### picture_with_holes
### the backend of pictures with holes for smaller pictures, which reveal as you scroll in

from PyQt4.QtGui import (QWidget, QApplication, QPainter, QColor, QImage)
from PyQt4 import QtCore
from PyQt4 import Qt
from PyQt4.QtCore import QRect, QRectF, QPointF

import popplerqt4
import random
from random_sketches import random_sketches_fname

PDF_BASE_RESOLUTION = 72.0
NUM_HOLES = 3

# how much the image in the hole is smaller then the parent one
DEFAULT_HOLE_SCALE = 4

MAX_HOLE_DISTANCE = 2.0
FULL_HOLE_DISTANCE = 1.1

def linear_transform(src, dst):
    zoom_x = float(dst.width())/src.width()
    zoom_y = float(dst.height())/src.height()

    def foo(thing):
        if isinstance(thing, QRectF):
            return QRectF(dst.x() + float(thing.x() - src.x()) * zoom_x,
                          dst.y() + float(thing.y() - src.y()) * zoom_y,
                          thing.width() * zoom_x,
                          thing.height() * zoom_y)
        else:
            return QPointF(dst.x() + float(thing.x() - src.x()) * zoom_x,
                           dst.y() + float(thing.y() - src.y()) * zoom_y)
        
    return foo

def child_opacity(distance):
    # return 1.0
    return min(float(MAX_HOLE_DISTANCE - distance)/(MAX_HOLE_DISTANCE - FULL_HOLE_DISTANCE),
               1.0)

def parent_opacity(distance):
    # return 1.0
    return max(1.0 - float(MAX_HOLE_DISTANCE - distance)/(MAX_HOLE_DISTANCE - FULL_HOLE_DISTANCE),
               0.0)

class Hole(object):
    def __init__(self, parent_rectf, pic=None, hole=None):
        self.parent_rectf = parent_rectf
        self.pic = pic
        self.hole = None
        self.child_rectf = None

        if self.parent_rectf is None:
            return
        
        if hole is None:
            w = self.parent_rectf.width()
            h = self.parent_rectf.height()
            hole_size = float(w + h) /DEFAULT_HOLE_SCALE /2
            self.hole = QRectF(random.random() * (w - hole_size),
                               random.random() * (h - hole_size),
                               hole_size,
                               hole_size)
        else:
            self.hole = hole

        if self.pic is not None:
            self.refine_coordinates()
        else:
            self.child_rectf = None

    def croak(self):
        print "parent_rectf:", self.parent_rectf, "hole:", self.hole, "child_rectf:", self.child_rectf
            
    def hole_scale(self):
        if self.hole is None:
            return DEFAULT_HOLE_SCALE
        else:
            return ((self.parent_rectf.width() + self.parent_rectf.height())
                    / (self.hole.width() + self.hole.height()))
            
    def refine_coordinates(self):
        c = self.hole.center()
        self.child_rectf = QRectF(self.pic.image.rect())
        scale = self.hole_scale()
        print "Hole scale:", scale
        w_half = float(self.parent_rectf.width()) / scale / 2
        h_half = float(self.parent_rectf.height()) / scale / 2

        self.hole = QRectF(c.x() - w_half, c.y() - h_half, w_half * 2, h_half * 2)
        
    def visible_p(self, frame, distance):
        # print "In visible: distance:", distance
        if distance < MAX_HOLE_DISTANCE:
            it = self.hole.intersected(frame)
            if it.width() * it.height() > 0:
                return it
        return None

    def rescale(self, x_m, y_m, zoom=1.0):
        self.hole = QRectF(float(self.hole.x() - x_m) * zoom + x_m,
                           float(self.hole.y() - y_m) * zoom + y_m,
                           self.hole.width() * zoom,
                           self.hole.height() * zoom)

    def central_rescale(self, zoom=1.0):
        center = self.hole.center()
        self.hole = QRectF(float(self.hole.x() - center.x()) * zoom + center.x(),
                           float(self.hole.y() - center.y()) * zoom + center.y(),
                           self.hole.width() * zoom,
                           self.hole.height() * zoom)
        
    def move(self, dx, dy):
        self.hole.moveTo(self.hole.topLeft() + QPointF(dx, dy))
        
    def sync(self, level, frame, ratio):
        it = self.visible_p(frame, ratio)
        if it is None:
            if self.pic is not None:
                print "Sync level", level, "Hole invisible -- removing pic:", ratio
                self.pic = None
            return None
        else:
            if self.pic is None:
                print "Sync level", level, "Hole visible -- adding pic:", ratio
                self.pic = PictureWithHoles(random_sketches_fname())
                self.refine_coordinates()
            return it
        
    def recursive_sync(self, level=0, frame=None, distance=None):
        if frame is None:
            frame = self.parent_rectf
            distance = 1.0 

        distance *= self.hole_scale()
            
        it = self.sync(level, frame, distance)
        
        if (it is not None) and (self.pic is not None):
            self.pic.recursive_sync(level,
                                    linear_transform(self.hole, self.child_rectf)(it),
                                    distance)

    def takes_whole_frame(self):
        image_rect = QRectF(self.parent_rectf) # we need our own copy here
        MARGIN = 5
        image_rect.setLeft(image_rect.left() + MARGIN)
        image_rect.setTop(image_rect.top() + MARGIN)
        image_rect.setRight(image_rect.right() - MARGIN)
        image_rect.setBottom(image_rect.bottom() - MARGIN)
        # print "In takes_whole_qimage:", self.dest, image_rect
        return self.hole.contains(image_rect)

    def glue_on_top(self, new_pic):
        index = random.randint(0, NUM_HOLES - 1)
        new_place = new_pic.children[index]

        new_place.pic = self.pic
        new_place.refine_coordinates()

        return Hole(self.parent_rectf,
                    pic = new_pic,
                    hole = linear_transform(new_place.hole, self.hole)(new_place.parent_rectf))

    def some_last_hole_takes_whole_frame(self):
        index = len(self.pic.children)
        for child in reversed(self.pic.children):
            index -= 1
            hole_in_abs_coords = linear_transform(child.parent_rectf, self.hole)(child.hole)

            if hole_in_abs_coords.contains(self.parent_rectf):
                return index
        return None

    def switch_to_child_pic(self, index):
        the_child = self.pic.children[index] # OK, I know, this isn't stricly OOP

        new_hole = Hole(self.parent_rectf, # frame stays the same
                        pic = the_child.pic,
                        hole = linear_transform(the_child.parent_rectf, self.hole)(the_child.hole))
        
        return new_hole

    def recursive_active_pics(self):
        if self.pic is None:
            return 0
        return self.pic.recursive_active_pics()

    def draw_border(self, target_image, dest_rectf, src_rectf):
        painter = QPainter()
        painter.begin(target_image)
        painter.setPen(QtCore.Qt.black)
        painter.drawRect(linear_transform(src_rectf, dest_rectf)(self.hole).toAlignedRect())
        painter.end()

    def init_geometry_from_qimage(self, qimage):
        the_qimage_rectf = QRectF(qimage.rect())
        self.parent_rectf = QRectF(the_qimage_rectf) # we need these two rects to be different (in memory)
        self.hole = QRectF(the_qimage_rectf)
        self.refine_coordinates()

        
    def recursive_draw(self, target_image, dest_rectf=None, src_rectf=None, distance=None):
        if dest_rectf is None:
            dest_rectf = self.parent_rectf
            src_rectf = self.parent_rectf
            distance = 1.0
            
        distance *= self.hole_scale()
            
        if self.pic is not None:
            # we need to calculate where to draw a hole,
            # and we are given, where to draw the whole thing
            intersection = src_rectf.intersected(self.hole)
            if intersection.width() * intersection.height() > 0:
                intersection_src = linear_transform(self.hole, self.child_rectf)(intersection)
                intersection_dst = linear_transform(src_rectf, dest_rectf)(intersection)
                self.pic.recursive_draw(target_image,
                                        dest_rectf = intersection_dst,
                                        src_rectf = intersection_src,
                                        distance = distance)

        # the reason we draw it here is that we want to draw it
        # even when there's no picture in the hole yet
        self.draw_border(target_image, dest_rectf, src_rectf)
        
    def find_volder_at_point(self, point_in_abs_refframe):
        point = linear_transform(self.hole, self.child_rectf)(point_in_abs_refframe)
        for child in self.pic.children:
            if child.hole.contains(point):
                return child
        return None
        

        
class PictureWithHoles(object):
    def __init__(self, fname):
        self.load(fname)
    
    def load(self, fname, index=0):
        self.doc = popplerqt4.Poppler.Document.load(fname)
        self.doc.setRenderHint(popplerqt4.Poppler.Document.Antialiasing
                               and popplerqt4.Poppler.Document.TextAntialiasing)
        self.image = self.doc.page(index).renderToImage(PDF_BASE_RESOLUTION,
                                                        PDF_BASE_RESOLUTION)
        self.image.setAlphaChannel(self.image.createMaskFromColor(QtCore.Qt.white, 1))
        
        # at first we assume we are rendering the whole of the page
        self.part = QRectF(0, 0,
                           self.image.width(), self.image.height())
        self.whole_dest = None
        self.dest = None
        self.render_ratio = None
        
        self.init_children()
        ## print "Loaded:", fname, self.hole.x(), self.hole.y(), self.hole.width(), self.hole.height()

    def init_children(self):
        rectf = QRectF(self.image.rect())
        self.children = [Hole(rectf) for x in xrange(NUM_HOLES)]

    def get_ratioed_qimage(self, ratio):
        '''This is returned to the parent widget and this is where it will draw.
        Thanks to ratio provided, it now has correct size.'''
        return QImage(float(self.image.width()) / ratio,
                      float(self.image.height()) / ratio,
                      self.image.format())
        
    def draw(self, target_image, dest_rectf, src_rectf, distance):
        # draw oneself
        painter = QPainter()
        painter.begin(target_image)
        parent_image = target_image.copy(dest_rectf.toAlignedRect())
        # we fill it white, with black border
        painter.setOpacity(1.0)
        painter.fillRect(dest_rectf, QtCore.Qt.white)

        # we redraw it parent-transparent
        painter.setOpacity(parent_opacity(distance))
        painter.drawImage(dest_rectf, parent_image)
        
        # we draw our image child-transparent on top of it
        sub_image = self.image.copy(src_rectf.toAlignedRect())
        sub_image.setAlphaChannel(sub_image.createMaskFromColor(QtCore.Qt.white, 1))
        painter.setOpacity(child_opacity(distance))
        painter.drawImage(dest_rectf, sub_image)

        painter.end()
        
    def recursive_draw(self, target_image, dest_rectf, src_rectf, distance):
        self.draw(target_image, dest_rectf, src_rectf, distance)

        # draw all children (they know if they should draw themselves or not)
        for child in self.children:
            child.recursive_draw(target_image, dest_rectf, src_rectf, distance)

    def recursive_sync(self, level, frame, ratio):
        for child in self.children:
            child.recursive_sync(level + 1, frame, ratio)
        
    def recursive_active_pics(self):
        num_pics = 1
        for child in self.children:
            num_pics += child.recursive_active_pics()
        return num_pics
