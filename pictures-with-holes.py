#!/usr/bin/python3

import sys
from PyQt4.QtGui import (QPalette, QWidget, QApplication, QPainter, QColor, QCursor, QImage)
from PyQt4 import QtCore
from PyQt4 import Qt
from PyQt4.QtCore import QRect

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

MAGIC_RECT = QRect(250,120,50,50)

def linear_transform(src, dst):
    zoom_x = float(dst.width())/src.width()
    zoom_y = float(dst.height())/src.height()
    
    return (lambda rect:
            QRect(dst.x() + float(rect.x() - src.x()) * zoom_x,
                  dst.y() + float(rect.y() - src.y()) * zoom_y,
                  rect.width() * zoom_x,
                  rect.height() * zoom_y))



def child_opacity(ratio):
    return min(float(ratio - MIN_HOLE_RATIO)/(FULL_HOLE_RATIO - MIN_HOLE_RATIO),
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
        self.part = QRect(0, 0,
                          self.image.width(), self.image.height())
        self.dest = None
        self.render_ratio = None
        
        self.init_hole_coordinates()

    def init_hole_coordinates(self):
        w = self.image.width()
        h = self.image.height()
        self.hole = QRect(random.random() * 3/4 * w, random.random() * 3/4 * h, 1/4 * w, 1/4 * h)

    def hole_visible_p(self):
        if self.render_ratio > MIN_HOLE_RATIO:
            return self.hole.intersected(self.part)
        return None

    def sync_child_pic(self):
        if self.hole_visible_p():
            if self.child_pic is None:
                self.child_pic = PictureWithHole(random_sketches_fname())
                self.child_pic.dest = linear_transform(self.part, self.dest)(self.hole.intersected(self.part))
                self.child_pic.determine_render_ratio()
        else:
            self.child_pic = None    

    def recursive_draw(self, image):
        painter = QPainter()
        painter.begin(image)
        self.draw(painter)
        painter.end()
        if self.child_pic is not None:
            self.child_pic.recursive_draw(image)

    def draw(self, painter):
        painter.setOpacity(child_opacity(self.render_ratio))
        painter.drawImage(self.dest, self.image, self.part)
        it = self.hole_visible_p()
        if it:
            its_dst = linear_transform(self.part, self.dest)(it)
            painter.setOpacity(1.0)
            painter.fillRect(its_dst, QtCore.Qt.white)
            painter.setOpacity(parent_opacity(self.render_ratio))
            painter.drawImage(self.dst_it, self.image, it)

    def hole_takes_whole_qimage(self):
        return self.hole.contains(self.part)
    def takes_whole_qimage(self, image):
        return self.dest.contains(image.rect())

    def glue_on_top(self, new_pic, image):
        new_pic.child_pic = self
        new_pic.dest = image.rect()

        # determine coordinates of the visible part of the hole in its parent coord system
        top = new_pic.hole.top() + 1.0/4 * self.part.top()
        bottom = new_pic.hole.top() + 1.0/4 * self.part.bottom()
        left = new_pic.hole.left() + 1.0/4 * self.part.left()
        right = new_pic.hole.left() + 1.0/4 * self.part.right()

        new_pic.part = linear_transform(self.dest, QRect(left, top, right-left, bottom-top))(self.dest)
        
        new_pic.determine_render_ratio()
        return new_pic

    def determine_render_ratio(self):
        ratio_x = float(self.dest.width())/self.part.width()
        ratio_y = float(self.dest.height())/self.part.height()
        self.render_ratio = float(ratio_x + ratio_y)/2
        # if abs(ratio_x - ratio_y) > 1:
        #     print ratio_x, ratio_y
        #     raise Exception("We don't support different ratios of PDFs right now")
        # else:
        #     self.render_ratio = ratio_x

    def recursive_rescale_and_sync(self, x_m, y_m, zoom=1.0, image=None):
        # we rescale destination
        self.dest = QRect((self.dest.x() - x_m) * zoom + x_m,
                          (self.dest.y() - y_m) * zoom + y_m,
                          self.dest.width() * zoom,
                          self.dest.height() * zoom)

        self.determine_render_ratio()

        # we crop part and destination if they take more than qimage
        if self.dest.x() < 0:
            self.part.setLeft(self.part.x() - float(self.dest.x()) / self.render_ratio)
            self.dest.setLeft(0)
        if self.dest.y() < 0:
            self.part.setTop(self.part.y() - float(self.dest.y()) / self.render_ratio)
            self.dest.setTop(0)
        if self.dest.right() > image.rect().right():
            self.part.setRight(self.part.right()
                               - float(self.dest.right()-image.rect().right())/self.render_ratio)
            self.dest.setRight(image.rect().right())
        if self.dest.bottom() > image.rect().bottom():
            self.part.setBottom(self.part.bottom()
                                - float(self.dest.bottom()-image.rect().bottom())/self.render_ratio)
            self.dest.setBottom(image.rect().bottom())
        
        # we sync and recurse on a child
        self.sync_child_pic()
        if self.child_pic:
            self.child_pic.recursive_rescale_and_sync(x_m, y_m, zoom=zoom, image=image)
        
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

    def loadFirstPDF(self):
        self.showMaximized()
        self.hide()
        self.pics = PictureWithHole(random_sketches_fname())
        
        self.init_pdf_image_geometry()

        self.refresh_the_qimage()
        self.pics.recursive_draw(self.the_qimage)

    def init_pdf_image_geometry(self):
        my_height = self.height()
        my_width = self.width()

        ratio = max(float(self.pics.image.width())/my_width,
                    float(self.pics.image.height())/my_height)

        self.the_qimage = QImage(self.pics.image.width() * ratio,
                                 self.pics.image.height() * ratio,
                                 self.pics.image.format())
        self.pics.dest = self.the_qimage.rect()
        self.pics.determine_render_ratio()
        
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.stop()

    def wheelEvent(self, event):
        pos = QCursor().pos()
        x_image = float(self.width() - self.the_qimage.width())/2
        y_image = float(self.height() - self.the_qimage.height())/2
        x_m = pos.x() - x_image
        y_m = pos.y() - y_image
        self.pics.recursive_rescale_and_sync(x_m, y_m,
                                             zoom = (1.0 + 0.1 * float(event.delta())/8/15/20),
                                             image = self.the_qimage)
        if not self.pics.takes_whole_qimage(self.the_qimage):
            self.pics = self.pics.glue_on_top(PictureWithHole(random_sketches_fname()),
                                              self.the_qimage)

        if self.pics.hole_takes_whole_qimage():
            self.pics = self.pics.child_pic

        self.refresh_the_qimage()
        self.pics.recursive_draw(self.the_qimage)
        self.update()

    def refresh_the_qimage(self):
        self.the_qimage.fill(QtCore.Qt.white)
        
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
    
