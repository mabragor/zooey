#!/usr/bin/python3

import sys
from PyQt4.QtGui import QPalette, QWidget, QApplication, QPainter
from PyQt4 import QtCore

import popplerqt4

class PdfViewer(QWidget):
    def __init__(self, rect):
        self.doc = None
        super(PdfViewer, self).__init__(None)

        self.setWindowTitle('PDF Viewer')
        self.isBlanked = False

        p = QPalette()
        p.setColor(QPalette.Background, QtCore.Qt.black);
        self.setPalette(p)

        self.setGeometry(rect)

        self.hide()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Down:
            self.nextPage()
        elif event.key() == QtCore.Qt.Key_Up:
            self.previousPage()
        elif event.key() == QtCore.Qt.Key_Escape:
            self.stop()

    def paintEvent(self, event):
        if self.isBlanked:
            return

        img = self.getImage(self.currentPage)
        if img is None:
            return

        x = (self.frameSize().width() - img.width())/2
        y = (self.frameSize().height() - img.height())/2

        painter = QPainter(self)
        painter.drawImage(x, y, img, 0, 0, 0, 0)

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

    def blank(self):
        self.isBlanked = True
        self.update()

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

    def cacheImage(self, idx):
        if idx >= self.doc.numPages():
            return

        if self.pdfImages[idx] is not None:
            return

        page = self.doc.page(idx)
        ratio = 1.0 * self.frameSize().width() / page.pageSize().width()
        yratio = 1.0 * self.frameSize().height() / page.pageSize().height()

        if yratio < ratio:
            ratio = yratio

        self.pdfImages[idx] = page.renderToImage(72 * ratio, 72 * ratio)

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
    ex = PdfViewer(QtCore.QRect(0,0, 300, 300))
    ex.load("/home/popolit/code/python-qt5-tutorial/sample-pdf.pdf")
    ex.start()
    sys.exit(app.exec_())
