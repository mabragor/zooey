#!/usr/bin/python3

import sys
from PyQt4.QtGui import (QPalette, QWidget, QApplication, QPainter, QColor, QCursor, QImage)
from PyQt4 import QtCore
from PyQt4 import Qt
from PyQt4.QtCore import QRect

import popplerqt4
import time

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
            return QRect(dst.x() + float(rect.x() - src.x()) * zoom_x,
                         dst.y() + float(rect.y() - src.y()) * zoom_y,
                         rect.width() * zoom_x,
                         rect.height() * zoom_y))
            

def child_opacity(ratio):
    return min(float(ratio - MIN_HOLE_RATIO)/(FULL_HOLE_RATIO - MIN_HOLE_RATIO),
               1.0)

def parent_opacity(ratio):
    return max(1.0 - float(ratio - MIN_HOLE_RATIO)/(FULL_HOLE_RATIO - MIN_HOLE_RATIO),
               0.0)

class PictureWithHole(object):
    def __init__(self):
        self.child_pic = None
    
    def load(self, fname, index=0):
        self.doc = popplerqt4.Poppler.Document.load(fname)
        self.doc.setRenderHint(popplerqt4.Poppler.Document.Antialiasing
                               and popplerqt4.Poppler.Document.TextAntialiasing)
        self.pdf_image = self.doc.page(index).renderToImage(PDF_BASE_RESOLUTION,
                                                            PDF_BASE_RESOLUTION)
        
        # at first we assume we are rendering the whole of the page
        self.render_rect = (0, 0, self.pdf_image.width(), self.pdf_image.height())

        self.init_hole_coordinates()

    def init_hole_coordinates():
        w = self.pdf_image.width()
        h = self.pdf_image.height()
        self.hole = QRect(random.random() * 3/4 * w, random.random() * 3/4 * h, 1/4 * w, 1/4 * h)

    def hole_seen_p(self):
        if self.render_ratio > MIN_HOLE_RATIO:
            return self.hole.intersected(self.part)
        return None

    def sync_child_pic(self):
        if self.hole_seen_p():
            if self.child_pic is None:
                self.child_pic = PictureWithHole(random_sketches_fname())
        else:
            self.child_pic = None    

    def recursive_draw(self, image):
        painter = QPainter(image)
        painter.begin()
        self.draw(painter)
        painter.end()
        if self.child_pic is not None:
            self.child_pic.recursive_draw(image)

    def draw(self, painter):
        painter.setOpacity(child_opacity(self.render_ratio))
        painter.drawImage(self.dest, self.image, self.part)
        it = self.hole_seen_p()
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
        if ratio_x != ratio_y:
            raise "We don't support different ratios of PDFs right now"
        else:
            self.render_ratio = ratio_x

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
        if self.dest.right() > image.rect.right():
            self.part.setRight(self.part.right()
                               - float(self.dest.right()-image.rect.right())/self.render_ratio)
            self.dest.setRight(image.rect.right())
        if self.dest.bottom() > image.rect.bottom():
            self.part.setBottom(self.part.bottom()
                                - float(self.dest.bottom()-image.rect.bottom())/self.render_ratio)
            self.dest.setBottom(image.rect.bottom())
        
        # we sync and recurse on a child
        self.sync_child_pic()
        if self.child_pic:
            self.child_pic.recursive_rescale_and_sync(x_m, y_m, zoom=zoom, image=image)
        
class ScrollAndReveal(QWidget):
    def __init__(self):
        self.doc = None
        super(ScrollAndReveal, self).__init__(None)

        self.loadPDF()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Scroll PDF and reveal another one')

        p = QPalette()
        p.setColor(QPalette.Background, QtCore.Qt.black);
        self.setPalette(p)

        self.showMaximized()
        self.show()

    def loadPDF(self):
        self.showMaximized()
        self.hide()
        fname1 = "/home/popolit/drafts/sketches/knots/ammm-knots-c/13-doublet-tree-for-2.pdf"
        fname2 = "/home/popolit/drafts/sketches/knots/ammm-knots-c/17-3-3-2-and-3-3-1-1-from-2.pdf"
        self.doc1 = popplerqt4.Poppler.Document.load(fname1)
        self.doc1.setRenderHint(popplerqt4.Poppler.Document.Antialiasing
                                and popplerqt4.Poppler.Document.TextAntialiasing)
        self.doc2 = popplerqt4.Poppler.Document.load(fname2)
        self.doc2.setRenderHint(popplerqt4.Poppler.Document.Antialiasing
                                and popplerqt4.Poppler.Document.TextAntialiasing)

        
        time.sleep(1)
        self.init_pdf_image_geometry()
        self.rerender_pdf_image()

    def init_pdf_image_geometry(self):
        my_height = self.height()
        my_width = self.width()

        self.page1 = self.doc1.page(0)
        self.page2 = self.doc2.page(0)
        self.ratio = max(float(self.page1.pageSize().width())/my_width,
                         float(self.page1.pageSize().height())/my_height)

        print "Page width:", self.page1.pageSize().width()
        
        # set the original rendering parameters -- the whole page fits on screen
        self.w = float(self.page1.pageSize().width()) / self.ratio
        self.h = float(self.page1.pageSize().height()) / self.ratio
        self.x = THE_X
        self.y = THE_Y

        print "In init pdf image:", self.h, my_height, self.frameSize().height()
        
    def rerender_pdf_image(self):
        if self.ratio > RATIO_MIN:
            self.pdf_image = self.page1.renderToImage(PDF_BASE_RESOLUTION / self.ratio,
                                                     PDF_BASE_RESOLUTION / self.ratio,
                                                     self.x, self.y, self.w, self.h)
        else:
            image1 = self.page1.renderToImage(PDF_BASE_RESOLUTION / self.ratio,
                                              PDF_BASE_RESOLUTION / self.ratio,
                                              self.x, self.y, self.w, self.h)
            image2 = self.page2.renderToImage(PDF_BASE_RESOLUTION, # / self.ratio,
                                              PDF_BASE_RESOLUTION # / self.ratio,
                                              )
                                              # self.x, self.y, self.w, self.h)
            self.pdf_image = image1.copy()

            x1 = MAGIC_RECT.x() / self.ratio - self.x
            y1 = MAGIC_RECT.y() / self.ratio - self.y
            h1 = MAGIC_RECT.height() / self.ratio
            w1 = MAGIC_RECT.width() / self.ratio
            
            # self.pdf_image.fill(QtCore.Qt.white)

            painter = QPainter()
            painter.begin(self.pdf_image)
            painter.setClipRect(x1, y1, w1, h1)

            # clear the magic region
            painter.setOpacity(1.0)
            painter.fillRect(x1, y1, w1, h1, QtCore.Qt.white)

            # draw semi-transparent version of image1 on top of it
            if self.ratio < RATIO_FULL:
                painter.setOpacity(0.0)
            else:
                painter.setOpacity(1.0 - float(self.ratio - RATIO_MIN)/(RATIO_FULL - RATIO_MIN))

            mask = image1.createMaskFromColor(QtCore.Qt.white, 1) # image1.pixel(0, 0), 1)
            image1.setAlphaChannel(mask)

            painter.drawImage(0, 0, image1)
            painter.end()

            # draw slowly revealing image2 in our magic rect
            painter = QPainter()
            painter.begin(self.pdf_image)
            painter.setClipRect(x1, y1, w1, h1)
            if self.ratio < RATIO_FULL:
                painter.setOpacity(1.0)
            else:
                painter.setOpacity(float(self.ratio - RATIO_MIN)/(RATIO_FULL - RATIO_MIN))

            mask = image2.createMaskFromColor(QtCore.Qt.white, 1) # image2.pixel(0, 0), 1)
            image2.setAlphaChannel(mask)

            painter.drawImage(QRect(x1, y1, w1, h1),
                              image2,
                              image2.rect())
            painter.end()
        
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

        if self.pics.hole_takes_whole_qimage(self.the_qimage):
            self.pics = self.pics.child_pic

        self.refresh_the_qimage()
        self.pics.recursive_draw(self.the_qimage)
        self.update()

    def refresh_the_qimage(self):
        self.the_qimage.fill(QtCore.Qt.white)
        
    def scale_pdf_image_geometry(self, x_m=0, y_m=0, dr=0.1):
        ratio2 = self.ratio + dr
        # print "In scale1:", self.x
        # self.x = float(self.x - x_m) * self.ratio/ratio2 + x_m
        # print "In scale2:", self.x
        # self.y = float(self.y - y_m) * self.ratio/ratio2 + y_m
        # self.x *= self.ratio/ratio2
        # self.y *= self.ratio/ratio2
        self.x = float(self.x + x_m) * self.ratio/ratio2 - x_m
        self.y = float(self.y + y_m) * self.ratio/ratio2 - y_m
        
        self.ratio = ratio2
        
    def paintEvent(self, event):
        x = (self.frameSize().width() - self.pdf_image.width())/2
        y = (self.frameSize().height() - self.pdf_image.height())/2

        painter = QPainter(self)
        painter.drawImage(x, y, self.pdf_image, 0, 0, 0, 0)

    def getCurrentPage(self):
        return self.currentPage + 1

    def getPageCount(self):
        if self.doc is None:
            return 0
        else:
            return self.doc.numPages()

    def load(self, filename):
        self.doc = popplerqt4.Poppler.Document.load(filename)
        self.doc.setRenderHint(popplerqt4.Poppler.Document.Antialiasing
                               and popplerqt4.Poppler.Document.TextAntialiasing)
        self.currentPage = 0
        self.pdfImages = [None for i in range(self.doc.numPages())]
        self.pdfImageRatios = [1.0 for i in range(self.doc.numPages())]
        self.cacheImage(self.currentPage)

    def display(self):
        self.update()
        self.cacheImage(self.currentPage + 1)

    def start(self):
        self.showFullScreen()
        self.show()

    def stop(self):
        self.hide()
        QtCore.QCoreApplication.instance().quit()

    def close(self):
        self.stop()
        self.pdfImages = None
        self.doc = None

    def nextPage(self):
        if self.currentPage + 1 < self.doc.numPages():
            self.currentPage += 1
            self.display()

    def previousPage(self):
        if self.currentPage > 0:
            self.currentPage -= 1
            self.display()

    def showPage(self, idx):
        if idx < self.doc.numPages():
            self.currentPages = idx
            self.display()

    def cacheImage(self, idx, force=None):
        if idx >= self.doc.numPages():
            return

        if (self.pdfImages[idx] is not None
            and force is None):
            return

        page = self.doc.page(idx)
        ratio = self.pdfImageRatios[idx]

        height = self.frameSize().height()
        width = float(height) * (float(page.pageSize().width()) / page.pageSize().height())

        self.pdfImages[idx] = page.renderToImage(72.0 * ratio, 72.0 * ratio,
                                                 0, 0, width, height)

    def doubleCacheImage(self, idx, force=None):
        self.cacheImage(idx, force)

        # now we want to add another image to the same layer
        self.cacheImage(idx+1, force)
        painter = QPainter()
        painter.begin(self.pdfImages[idx])
        painter.setOpacity(0.5)

        image2 = self.getImage(idx+1).copy()
        mask = image2.createMaskFromColor(image2.pixel(0, 0), 1)
        image2.setAlphaChannel(mask)

        painter.drawImage(0, 0, image2,
                          sw = self.pdfImages[idx].width()/2,
                          sh = self.pdfImages[idx].height()/2)
        painter.end()

    def getImage(self, idx):
        self.cacheImage(idx)
        return self.pdfImages[idx]

    def getThumbnail(self, idx):
        img = None
        if img is None:
            img = self.getImage(idx)
        return img
        
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = ScrollAndReveal()
    # ex.load("/home/popolit/code/python-qt5-tutorial/sample-pdf.pdf")
    # ex.start()
    sys.exit(app.exec_())
