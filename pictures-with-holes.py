#!/usr/bin/python3

from __future__ import with_statement

import sys
from PyQt4.QtGui import (QPalette, QWidget, QApplication, QPainter, QColor, QCursor, QImage)
from PyQt4 import QtCore
from PyQt4 import Qt
from PyQt4.QtCore import QRect, QRectF, QPointF

from os import walk
import os

import popplerqt4
import time
import random

PDF_BASE_RESOLUTION = 72.0
THE_X = 0
THE_Y = 0

MAX_HOLE_DISTANCE = 2.0
FULL_HOLE_DISTANCE = 1.1

# how much the image in the hole is smaller then the parent one
DEFAULT_HOLE_SCALE = 4

MOVE_SPEED = 10

NUM_HOLES = 3

def linear_transform(src, dst):
    zoom_x = float(dst.width())/src.width()
    zoom_y = float(dst.height())/src.height()
    
    return (lambda rect:
            QRectF(dst.x() + float(rect.x() - src.x()) * zoom_x,
                   dst.y() + float(rect.y() - src.y()) * zoom_y,
                   rect.width() * zoom_x,
                   rect.height() * zoom_y))



def child_opacity(distance):
    # return 1.0
    return min(float(MAX_HOLE_DISTANCE - distance)/(MAX_HOLE_DISTANCE - FULL_HOLE_DISTANCE),
               1.0)

def parent_opacity(distance):
    # return 1.0
    return max(1.0 - float(MAX_HOLE_DISTANCE - distance)/(MAX_HOLE_DISTANCE - FULL_HOLE_DISTANCE),
               0.0)

DRAFTS_SKETCHES_PATH = "/home/popolit/drafts/sketches"
ALL_SKETCHES = None
def populate_all_sketches():
    global ALL_SKETCHES
    ALL_SKETCHES = []
    for (dirpath, dirnames, filenames) in walk(DRAFTS_SKETCHES_PATH):
        ALL_SKETCHES.extend(map(lambda x: os.path.join(dirpath, x),
                                filter(lambda x: x[-4:] == ".pdf",
                                       filenames)))
    return True

def random_sketches_fname():
    if not ALL_SKETCHES:
        populate_all_sketches()

    return os.path.join(DRAFTS_SKETCHES_PATH, random.choice(ALL_SKETCHES))

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

    # def recursive_draw(self, image, frame=None, distance=None):
    #     if self.pic is None:
    #         return # we just do nothing
        
    #     if frame is None: # it means we are at the toplevel
    #         frame = self.parent_rectf
    #         distance = 1.0

    #     intersection = self.hole.intersected(frame)
    #     intersection_src = linear_transform(self.hole, self.child_rectf)(intersection)
            
    #     sub_image = self.pic.recursive_draw(intersection_src,
    #                                         distance = distance * self.hole_scale())
    #     painter = QPainter()
    #     painter.begin(image)

    #     # # we copy a hole region from image
    #     # hole_parent_image = image.copy(intersection.toAlignedRect())
    #     # we fill it white, with black border
    #     painter.setOpacity(1.0)
    #     painter.fillRect(intersection, QtCore.Qt.white)
    #     painter.setPen(QtCore.Qt.black)
    #     painter.drawRect(intersection)

    #     # # we redraw it parent-transparent
    #     # painter.setOpacity(parent_opacity(distance))
    #     # painter.drawImage(intersection, hole_parent_image)
        
    #     # # we draw child-transparent subimage on top of it
    #     # sub_image.setAlphaChannel(sub_image.createMaskFromColor(QtCore.Qt.white, 1))
    #     # painter.setOpacity(child_opacity(distance))
    #     # painter.drawImage(intersection, sub_image, intersection_src)

    #     painter.end()

    def draw_border(self, target_image, dest_rectf, src_rectf):
        painter = QPainter()
        painter.begin(target_image)
        painter.setPen(QtCore.Qt.black)
        painter.drawRect(linear_transform(src_rectf, dest_rectf)(self.hole).toAlignedRect())
        painter.end()
    
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
                
class PicturesWithHolesWidget(QWidget):
    def __init__(self):
        super(PicturesWithHolesWidget, self).__init__(None)

        self.loadFirstPDF()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Scroll PDFs and reveal random ones')

        p = QPalette()
        p.setColor(QPalette.Background, QtCore.Qt.black);
        self.setPalette(p)

        self.showMaximized()
        self.show()

        self.init_modal_dispatcher()
        # self.init_key_actions()

    def init_modal_dispatcher(self):
        self.modal_dispatcher = ModalDispatcher(
            { "main" : { "a" : ["zoom", "in"],
                         "z" : ["zoom", "out"],
                         "i" : ["move", "up"],
                         "j" : ["move", "left"],
                         "k" : ["move", "down"],
                         "l" : ["move", "right"],
                         "shift" : ["mode", "shift"],
                         "e" : ["mode", "volder_edit"] },
              "shift" : { "options" : ["inherit"],
                          "i" : ["move_cursor", "up"],
                          "j" : ["move_cursor", "left"],
                          "k" : ["move_cursor", "down"],
                          "l" : ["move_cursor", "right"] },
              "volder_edit" : { "a" : "enlarge_volder_at_point",
                                "z" : "shrink_volder_at_point",
                                "i" : ["move_volder_at_point", "up"],
                                "j" : ["move_volder_at_point", "left"],
                                "k" : ["move_volder_at_point", "down"],
                                "l" : ["move_volder_at_point", "right"] },
              "actions" : self.expand_action_specs("zoom", "move", "move_cursor",
                                                   "move_volder_at_point",
                                                   "enlarge_volder_at_point",
                                                   "shrink_volder_at_point") })

    def expand_action_specs(self, *specs):
        def foo(x):
            if isinstance(spec, basestring):
                return [spec,
                        self.make_curry(getattr(self, spec + "_starter")),
                        self.make_curry(getattr(self, spec + "_stopper"))]
            else:
                return x
                        
        return map(foo, specs)
        
    def make_curry(self, method):
        def frob(*args, **kwds):
            return method(self, *args, **kwds)
        return frob
        
    def init_key_actions(self):
        self.action_timer = QtCore.QTimer()
        self.action_timer.setInterval(10)

        self.action_lock = False
        self.action_type = None
        # self.the_zoom_delta = 0

    def num_active_pics(self):
        return self.pics.recursive_active_pics()

    def loadFirstPDF(self):
        self.showMaximized()
        self.hide()
        self.pics = Hole(None, pic=PictureWithHoles(random_sketches_fname()))
        
        self.init_pdf_image_geometry()

        self.pics.recursive_sync()
        ## print self.pics.part, self.pics.dest, self.width(), self.height()
        self.redraw()
        
    def init_pdf_image_geometry(self):
        my_height = self.height()
        my_width = self.width()

        ratio = max(float(self.pics.pic.image.width())/my_width,
                    float(self.pics.pic.image.height())/my_height)

        self.the_qimage = QImage(float(self.pics.pic.image.width()) / ratio,
                                 float(self.pics.pic.image.height()) / ratio,
                                 self.pics.pic.image.format())
        the_qimage_rectf = QRectF(self.the_qimage.rect())
        self.pics.parent_rectf = QRectF(the_qimage_rectf) # we need these two widgets to be different
        self.pics.hole = QRectF(the_qimage_rectf)
        self.pics.refine_coordinates()
        # self.pics.child_rectf = QRectF(self.pics.pic.image.rect())

        self.pics.croak()
        
    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == QtCore.Qt.Key_Escape:
            self.stop()
            return

        self.modal_dispatcher.press(event.key())
        
            
        # elif event.key() == QtCore.Qt.Key_A:
        #     print "Key A was pressed, # active pics:", self.num_active_pics()
        #     self.try_start_action("zoom_in")
        # elif event.key() == QtCore.Qt.Key_Z:
        #     print "Key Z was pressed, # active pics:", self.num_active_pics()
        #     self.try_start_action("zoom_out")
        # elif event.key() == QtCore.Qt.Key_J:
        #     print "Key J was pressed, # active pics:", self.num_active_pics()
        #     self.try_start_action("move_left")
        # elif event.key() == QtCore.Qt.Key_L:
        #     print "Key L was pressed, # active pics:", self.num_active_pics()
        #     self.try_start_action("move_right")
        # elif event.key() == QtCore.Qt.Key_I:
        #     print "Key I was pressed, # active pics:", self.num_active_pics()
        #     self.try_start_action("move_up")
        # elif event.key() == QtCore.Qt.Key_K:
        #     print "Key K was pressed, # active pics:", self.num_active_pics()
        #     self.try_start_action("move_down")
            
    def try_start_action(self, name):
        if self.action_type is not None:
            return

        self.action_type = name
        res = getattr(self, name + "_starter")()
        if res:
            self.action_timer.start()

    def zoom_in_starter(self):
        self.the_zoom_delta = 0.1
        self.action_timer.timeout.connect(self.zoom_to_cursor)
        return True

    def zoom_out_starter(self):
        self.the_zoom_delta = -0.1
        self.action_timer.timeout.connect(self.zoom_to_cursor)
        return True

    def try_stop_action(self, name):
        if not(self.action_type and self.action_type == name):
            return

        res = getattr(self, name + "_stopper")()
        if res:
            self.action_timer.stop()
        self.action_type = None

    def zoom_in_stopper(self):
        self.action_timer.timeout.disconnect(self.zoom_to_cursor)
        return True

    def zoom_out_stopper(self):
        self.action_timer.timeout.disconnect(self.zoom_to_cursor)
        return True

    def move_left_starter(self):
        self.the_move_x = MOVE_SPEED
        self.the_move_y = 0
        self.action_timer.timeout.connect(self.move)
        return True
    def move_right_starter(self):
        self.the_move_x = -MOVE_SPEED
        self.the_move_y = 0
        self.action_timer.timeout.connect(self.move)
        return True
    def move_up_starter(self):
        self.the_move_x = 0
        self.the_move_y = MOVE_SPEED
        self.action_timer.timeout.connect(self.move)
        return True
    def move_down_starter(self):
        self.the_move_x = 0
        self.the_move_y = -MOVE_SPEED
        self.action_timer.timeout.connect(self.move)
        return True
    
    def move_left_stopper(self):
        self.action_timer.timeout.disconnect(self.move)
        return True
    def move_right_stopper(self):
        self.action_timer.timeout.disconnect(self.move)
        return True
    def move_up_stopper(self):
        self.action_timer.timeout.disconnect(self.move)
        return True
    def move_down_stopper(self):
        self.action_timer.timeout.disconnect(self.move)
        return True
    
    def move(self, x=None, y=None):
        self.pics.move(x or self.the_move_x,
                       y or self.the_move_y)
        self.sync_and_redraw()
    
    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

        self.modal_dispatcher.release(event.key())
        
        # if event.key() == QtCore.Qt.Key_A:
        #     print "Key A was released, # active pics:", self.num_active_pics()
        #     self.try_stop_action("zoom_in")
        # elif event.key() == QtCore.Qt.Key_Z:
        #     print "Key Z was released, # active pics:", self.num_active_pics()
        #     self.try_stop_action("zoom_out")
        # elif event.key() == QtCore.Qt.Key_J:
        #     print "Key J was released, # active pics:", self.num_active_pics()
        #     self.try_stop_action("move_left")
        # elif event.key() == QtCore.Qt.Key_L:
        #     print "Key L was released, # active pics:", self.num_active_pics()
        #     self.try_stop_action("move_right")
        # elif event.key() == QtCore.Qt.Key_I:
        #     print "Key I was released, # active pics:", self.num_active_pics()
        #     self.try_stop_action("move_up")
        # elif event.key() == QtCore.Qt.Key_K:
        #     print "Key K was released, # active pics:", self.num_active_pics()
        #     self.try_stop_action("move_down")
            
    def wheelEvent(self, event):
        self.zoom_to_cursor(0.1 * float(event.delta())/8/15/20)
        
    def zoom_to_cursor(self, delta_zoom=None):
        if not delta_zoom:
            delta_zoom = self.the_zoom_delta
            
        pos = QCursor().pos()
        x_image = float(self.width() - self.the_qimage.width())/2
        y_image = float(self.height() - self.the_qimage.height())/2
        x_m = pos.x() - x_image
        y_m = pos.y() - y_image
        zoom = (1.0 + delta_zoom)
        ## print "Zoom:", zoom

        self.pics.rescale(x_m, y_m, zoom=zoom)
        self.sync_and_redraw()

    def sync_and_redraw(self):
        self.pics.recursive_sync()
        
        if not self.pics.takes_whole_frame():
            print "Creating new top pic"
            self.pics = self.pics.glue_on_top(PictureWithHoles(random_sketches_fname()))

        dominant_index = self.pics.some_last_hole_takes_whole_frame()
        if dominant_index is not None: # self.pics.hole_takes_whole_qimage():
            print "Switching to the child pic"
            self.pics = self.pics.switch_to_child_pic(dominant_index)

        self.redraw()

    def redraw(self):
        self.refresh_the_qimage()
        self.pics.recursive_draw(self.the_qimage)
        self.update()

    def refresh_the_qimage(self, color=QtCore.Qt.white):
        self.the_qimage.fill(color)
        
    def paintEvent(self, event):
        x = (self.frameSize().width() - self.the_qimage.width())/2
        y = (self.frameSize().height() - self.the_qimage.height())/2

        painter = QPainter(self)
        painter.drawImage(x, y, self.the_qimage, 0, 0, 0, 0)

    def start(self):
        self.showFullScreen()
        self.show()
        
    def stop(self):
        QtCore.QCoreApplication.instance().quit()

class ModalDispatcher(object):
    def __init__(self, keymap_description):
        self.parse_keymap_description(keymap_description)

    def parse_keymap_description(self, keymap_description):
        pass

    def press(self, key):
        if self.mode_key_p(key):
            self.try_activate_mode(key)
        elif self.action_key_p(key):
            self.try_start_action(key)

    def mode_key_p(self, key):
        return self.current_mode.modes.has_key(key)

    def action_key_p(self, key):
        return self.current_mode.actions.has_key(key)

    def try_activate_mode(self, key):
        if self.action is not None:
            return

        with locking_attr(self):
            mode_name = self.current_mode.modes[key]
            self.mode_stack.append([mode_name, key, self.current_mode])
            self.current_mode = Mode(self.current_mode, mode_name)

    def try_start_action(self, key):
        if self.action is not None:
            return

        self.action = 'lock'
        action_name_and_args = self.current_mode.actions[key]
        try:
            apply(self.action_starter(action_name_and_args[0]),
                  action_name_and_args[1:])
        except:
            self.action = None
        else:
            self.action = action_name_and_args

    def release(self, key):
        if self.mode_in_stack_key_p(key):
            self.unwind_mode_stack(key)
        elif self.action_key_p(key):
            self.try_stop_action(key)

    def mode_in_stack_key_p(self, key):
        lst = filter(lambda x: x[1] == key,
                     self.mode_stack)
        return len(lst) == 1
            
    def unwind_mode_stack(self, key):
        self.stop_current_action()

        with locking_attr(self):
            while self.mode_stack[0, 1] != key:
                self.mode_stack.pop()
            (None, None, old_mode) = self.mode_stack.pop()
            self.current_mode = old_mode

    def stop_current_action(self):
        if self.action is None:
            return

        action = self.action
        with locking_attr(self):
            apply(self.action_stopper(action[0]), action[1:])

    def try_stop_action(self, key):
        if self.action is None:
            return

        if self.action == self.current_mode.actions(key):
            self.stop_current_action()
            
def locking_attr(x, attr_name="action", value_after=None):
    class Frob(object):
        def __enter__(self):
            it = getattr(x, attr_name)
            if it is not None:
                raise "Attempt to lock a not-None field", it

            setattr(x, attr_name, 'lock')
            return True
            
        def __exit__(self, type, value, traceback):
            setattr(x, attr_name, value_after)
            return True

    return Frob()
    
    
    
class Mode(object):
    pass
        
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = PicturesWithHolesWidget()
    # ex.load("/home/popolit/code/python-qt5-tutorial/sample-pdf.pdf")
    ex.start()
    sys.exit(app.exec_())

# if __name__ == '__main__':
#     print random_sketches_fname()
#     print random_sketches_fname()
#     print random_sketches_fname()
    
