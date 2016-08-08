#!/usr/bin/python3

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

MIN_HOLE_RATIO = 2
FULL_HOLE_RATIO = 3

# how much the image in the hole is smaller then the parent one
HOLE_SCALE = 4

MOVE_SPEED = 10

def linear_transform(src, dst):
    zoom_x = float(dst.width())/src.width()
    zoom_y = float(dst.height())/src.height()
    
    return (lambda rect:
            QRectF(dst.x() + float(rect.x() - src.x()) * zoom_x,
                   dst.y() + float(rect.y() - src.y()) * zoom_y,
                   rect.width() * zoom_x,
                   rect.height() * zoom_y))



def child_opacity(ratio):
    return min(float(HOLE_SCALE * ratio - MIN_HOLE_RATIO)/(FULL_HOLE_RATIO - MIN_HOLE_RATIO),
               1.0)

def parent_opacity(ratio):
    return max(1.0 - float(ratio - MIN_HOLE_RATIO)/(FULL_HOLE_RATIO - MIN_HOLE_RATIO),
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
    
class PictureWithHole(object):
    def __init__(self, fname):
        self.child_pic = None
        self.load(fname)
    
    def load(self, fname, index=0):
        self.doc = popplerqt4.Poppler.Document.load(fname)
        self.doc.setRenderHint(popplerqt4.Poppler.Document.Antialiasing
                               and popplerqt4.Poppler.Document.TextAntialiasing)
        self.image = self.doc.page(index).renderToImage(PDF_BASE_RESOLUTION,
                                                        PDF_BASE_RESOLUTION)
        
        # at first we assume we are rendering the whole of the page
        self.part = QRectF(0, 0,
                           self.image.width(), self.image.height())
        self.whole_dest = None
        self.dest = None
        self.render_ratio = None
        
        self.init_hole_coordinates()
        ## print "Loaded:", fname, self.hole.x(), self.hole.y(), self.hole.width(), self.hole.height()

    def init_hole_coordinates(self):
        w = self.image.width()
        h = self.image.height()
        # we don't yet know, what is the actual size of the picture at hole will be
        # so we first work with the mean values -- and later we update
        hole_size = float(w + h) /HOLE_SCALE /2
        self.hole = QRectF(random.random() * (w - hole_size),
                           random.random() * (h - hole_size),
                           hole_size,
                           hole_size)

    def refine_hole_coordinates(self):
        c = self.hole.center()
        w_half = float(self.child_pic.image.width()) / HOLE_SCALE / 2
        h_half = float(self.child_pic.image.height()) / HOLE_SCALE / 2

        self.hole = QRectF(c.x() - w_half, c.y() - h_half, w_half * 2, h_half * 2)

    def backpropagate_dest_and_part(self, image_rectf):
        self.dest = self.whole_dest.intersected(image_rectf)
        self.part = linear_transform(self.whole_dest, QRectF(self.image.rect()))(self.dest)
        
    def hole_visible_p(self):
        if self.render_ratio > MIN_HOLE_RATIO:
            return self.hole.intersected(self.part)
        return None

    def refine_childs_dest_and_part(self):
        parent_transform = linear_transform(self.part, self.dest)
        theor_dest = parent_transform(self.hole)
        expr_dest = parent_transform(self.hole.intersected(self.part))
        self.child_pic.whole_dest = theor_dest
        self.child_pic.dest = expr_dest
        reverse_child_transform = linear_transform(theor_dest, QRectF(self.child_pic.image.rect()))
        self.child_pic.part = reverse_child_transform(expr_dest)
    
    def sync_child_pic(self):
        if self.hole_visible_p():
            if self.child_pic is None:
                self.child_pic = PictureWithHole(random_sketches_fname())
                self.refine_hole_coordinates()
                self.refine_childs_dest_and_part()
                self.child_pic.determine_render_ratio()
        else:
            self.child_pic = None    

    def recursive_draw(self, image, toplevel=True):
        painter = QPainter()
        painter.begin(image)
        self.draw(painter, toplevel=toplevel)
        painter.end()
        if self.child_pic is not None:
            ## print "Drawing childpic"
            self.child_pic.recursive_draw(image, toplevel=False)

    def draw(self, painter, toplevel=True):
        if toplevel:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(child_opacity(self.render_ratio))
        ## print "Painter opacity:", painter.opacity(), self.render_ratio
        painter.drawImage(self.dest.toAlignedRect(), self.image, self.part.toAlignedRect())

        # mark, where the hole is
        ## print "Hole:", self.hole, linear_transform(self.part, self.dest)(self.hole)
        oldOpacity = painter.opacity()
        painter.setPen(QtCore.Qt.black)
        painter.drawRect(linear_transform(self.part, self.dest)(self.hole))
        painter.setOpacity(oldOpacity)
        
        it = self.hole_visible_p()
        if it:
            its_dst = linear_transform(self.part, self.dest)(it)
            painter.setOpacity(1.0)
            painter.fillRect(its_dst, QtCore.Qt.white)
            painter.setOpacity(parent_opacity(self.render_ratio))
            painter.drawImage(its_dst.toAlignedRect(), self.image, it.toAlignedRect())

    def hole_takes_whole_qimage(self):
        return self.hole.contains(self.part)
    def takes_whole_qimage(self, image):
        image_rect = QRectF(image.rect())
        MARGIN = 5
        image_rect.setLeft(image_rect.left() + MARGIN)
        image_rect.setTop(image_rect.top() + MARGIN)
        image_rect.setRight(image_rect.right() - MARGIN)
        image_rect.setBottom(image_rect.bottom() - MARGIN)
        # print "In takes_whole_qimage:", self.dest, image_rect
        return self.dest.contains(image_rect)

    def glue_on_top(self, new_pic, image):
        new_pic.child_pic = self
        new_pic.dest = QRectF(image.rect())

        # determine coordinates of the visible part of the hole in its parent coord system
        top = new_pic.hole.top() + 1.0/HOLE_SCALE * self.part.top()
        bottom = new_pic.hole.top() + 1.0/HOLE_SCALE * self.part.bottom()
        left = new_pic.hole.left() + 1.0/HOLE_SCALE * self.part.left()
        right = new_pic.hole.left() + 1.0/HOLE_SCALE * self.part.right()

        new_pic.part = linear_transform(self.dest, QRectF(left, top, right-left, bottom-top))(self.dest)
        
        new_pic.determine_render_ratio()
        return new_pic

    def determine_render_ratio(self):
        if self.part.width() != 0:
            ratio_x = float(self.dest.width())/self.part.width()
        else:
            ratio_x = 0
        if self.part.height() != 0:
            ratio_y = float(self.dest.height())/self.part.height()
        else:
            ratio_y = 0
        self.render_ratio = float(ratio_x + ratio_y)/2

    def recursive_rescale_and_sync(self, x_m, y_m, zoom=1.0, image=None):
        # we rescale destination
        self.whole_dest = QRectF(float(self.whole_dest.x() - x_m) * zoom + x_m,
                                 float(self.whole_dest.y() - y_m) * zoom + y_m,
                                 self.whole_dest.width() * zoom,
                                 self.whole_dest.height() * zoom)
        self.backpropagate_dest_and_part(QRectF(image.rect()))
        self.determine_render_ratio()

        if self.render_ratio == 0:
            return False

        # we sync and recurse on a child
        self.sync_child_pic()
        if self.child_pic:
            if not self.child_pic.recursive_rescale_and_sync(x_m, y_m, zoom=zoom, image=image):
                self.child_pic = None # if child scaled to zero, we delete it
        return True

    def recursive_move(self, dx, dy, image_rectf):
        self.whole_dest.moveTo(self.whole_dest.topLeft() + QPointF(dx, dy))
        self.backpropagate_dest_and_part(image_rectf)
        self.sync_child_pic()
        if self.child_pic:
            self.child_pic.recursive_move(dx, dy, image_rectf)
            
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
        
        self.init_key_actions()

    def init_key_actions(self):
        self.action_timer = QtCore.QTimer()
        self.action_timer.setInterval(10)

        self.action_lock = False
        self.action_type = None
        # self.the_zoom_delta = 0

    def loadFirstPDF(self):
        self.showMaximized()
        self.hide()
        self.pics = PictureWithHole(random_sketches_fname())
        
        self.init_pdf_image_geometry()

        ## print self.pics.part, self.pics.dest, self.width(), self.height()
        
        self.refresh_the_qimage() # color=QtCore.Qt.transparent)
        self.pics.recursive_draw(self.the_qimage)
        self.update()
        
    def init_pdf_image_geometry(self):
        my_height = self.height()
        my_width = self.width()

        ratio = max(float(self.pics.image.width())/my_width,
                    float(self.pics.image.height())/my_height)

        self.the_qimage = QImage(float(self.pics.image.width()) / ratio,
                                 float(self.pics.image.height()) / ratio,
                                 self.pics.image.format())
        the_qimage_rectf = QRectF(self.the_qimage.rect())
        self.pics.whole_dest = the_qimage_rectf
        self.pics.backpropagate_dest_and_part(the_qimage_rectf)
        self.pics.determine_render_ratio()
        
    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == QtCore.Qt.Key_Escape:
            self.stop()
        elif event.key() == QtCore.Qt.Key_A:
            print "Key A was pressed"
            self.try_start_action("zoom_in")
        elif event.key() == QtCore.Qt.Key_Z:
            print "Key Z was pressed"
            self.try_start_action("zoom_out")
        elif event.key() == QtCore.Qt.Key_J:
            print "Key J was pressed"
            self.try_start_action("move_left")
        elif event.key() == QtCore.Qt.Key_L:
            print "Key L was pressed"
            self.try_start_action("move_right")
        elif event.key() == QtCore.Qt.Key_I:
            print "Key I was pressed"
            self.try_start_action("move_up")
        elif event.key() == QtCore.Qt.Key_K:
            print "Key K was pressed"
            self.try_start_action("move_down")
            
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
        self.pics.recursive_move(x or self.the_move_x,
                                 y or self.the_move_y,
                                 QRectF(self.the_qimage.rect()))
        self.redraw()
    
    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == QtCore.Qt.Key_A:
            print "Key A was released"
            self.try_stop_action("zoom_in")
        elif event.key() == QtCore.Qt.Key_Z:
            print "Key Z was released"
            self.try_stop_action("zoom_out")
        elif event.key() == QtCore.Qt.Key_J:
            print "Key J was released"
            self.try_stop_action("move_left")
        elif event.key() == QtCore.Qt.Key_L:
            print "Key L was released"
            self.try_stop_action("move_right")
        elif event.key() == QtCore.Qt.Key_I:
            print "Key I was released"
            self.try_stop_action("move_up")
        elif event.key() == QtCore.Qt.Key_K:
            print "Key K was released"
            self.try_stop_action("move_down")
            
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
        self.pics.recursive_rescale_and_sync(x_m, y_m,
                                             zoom = zoom,
                                             image = self.the_qimage)
        if not self.pics.takes_whole_qimage(self.the_qimage):
            print "Creating new top pic"
            self.pics = self.pics.glue_on_top(PictureWithHole(random_sketches_fname()),
                                              self.the_qimage)

        if self.pics.hole_takes_whole_qimage():
            print "Switching to the child pic"
            self.pics = self.pics.child_pic

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
    
