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

RATIO_MIN = 0.4
RATIO_FULL = 0.2

MAGIC_RECT = QRect(250,120,50,50)

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
        x_image = float(self.width() - self.w)/2
        y_image = float(self.height() - self.h)/2

        print "I'm in a wheel event1:", self.height(), self.h, self.ratio
        print "I'm in a wheel event:", pos.x(), pos.y(), x_image, y_image
        
        self.scale_pdf_image_geometry(dr=0.1 * float(event.delta())/8/15/20, # * self.ratio,
                                      x_m = pos.x() - x_image, y_m = pos.y() - y_image)
        self.rerender_pdf_image()
        self.update()

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
