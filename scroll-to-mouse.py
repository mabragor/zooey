#!/usr/bin/python3

import sys
from PyQt4.QtGui import QPalette, QWidget, QApplication, QPainter, QColor
from PyQt4 import QtCore
from PyQt4 import Qt

import popplerqt4

PDF_BASE_RESOLUTION = 72.0

class ScrollPdfToMouse(QWidget):
    def __init__(self):
        self.doc = None
        super(ScrollPdfToMouse, self).__init__(None)

        self.loadPDF()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Scroll PDF to mouse')

        p = QPalette()
        p.setColor(QPalette.Background, QtCore.Qt.black);
        self.setPalette(p)

        self.showMaximized()
        self.show()

    def loadPDF(self):
        self.showMaximized()
        self.hide()
        fname = "/home/popolit/drafts/sketches/knots/ammm-knots-c/13-doublet-tree-for-2.pdf"
        self.doc = popplerqt4.Poppler.Document.load(fname)
        self.doc.setRenderHint(popplerqt4.Poppler.Document.Antialiasing
                               and popplerqt4.Poppler.Document.TextAntialiasing)

        my_height = self.frameSize().height()
        my_width = self.frameSize().width()

        self.page = self.doc.page(0)
        self.ratio = max(float(self.page.pageSize().width())/my_width,
                         float(self.page.pageSize().height())/my_height)

        # set the original rendering parameters -- the whole page fits on screen
        self.w = float(self.page.pageSize().width()) / self.ratio
        self.h = float(self.page.pageSize().height()) / self.ratio
        self.x = 0
        self.y = 0
        
        self.pdf_image = self.page.renderToImage(PDF_BASE_RESOLUTION / self.ratio,
                                                 PDF_BASE_RESOLUTION / self.ratio,
                                                 self.x, self.y, self.w, self.h)
        
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.stop()

    def wheelEvent(self, event):
        step = float(event.delta())/8/15/20
        self.pdfImageRatios[self.currentPage] *= (1.0 + 0.1 * step)
        self.doubleCacheImage(self.currentPage, True)
        self.update()

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
    ex = ScrollPdfToMouse()
    # ex.load("/home/popolit/code/python-qt5-tutorial/sample-pdf.pdf")
    # ex.start()
    sys.exit(app.exec_())
