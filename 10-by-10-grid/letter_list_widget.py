
from PyQt4 import (QtCore, QtGui)
from PyQt4.QtGui import (QWidget, QImage, QPainter, QCursor, QColor)
from PyQt4.QtCore import (QRectF, QPointF, QSizeF, QSize, QString)
import time
import random
from itertools import imap

BALL_SIZE = 40
MARGIN_SIZE = 40
STICK_SIZE = 40
STICK_WIDTH = 10

FONT_SIZE = 20

class SimpleHStickWidget(QWidget):
    def __init__(self):
        super(SimpleHStickWidget, self).__init__()

        self.setMinimumSize(STICK_SIZE, BALL_SIZE)

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()

    def drawWidget(self, qp):
        size = self.size()
        w = size.width()
        h = size.height()

        pen = QtGui.QPen(QtGui.QColor(20, 20, 20), 1, QtCore.Qt.SolidLine)
        qp.setPen(pen)
        qp.setBrush(QtCore.Qt.NoBrush)

        qp.drawRect(0, max((h - STICK_WIDTH)/2, 0), w-1, min(STICK_WIDTH, h))

class LetterCircleWidget(QWidget):
    def __init__(self, letter):
        super(LetterCircleWidget, self).__init__()
        self._letter = letter
        self.setMinimumSize(BALL_SIZE, BALL_SIZE)

        QtGui.QToolTip.setFont(QtGui.QFont('SansSerif', 10))
        self.setToolTip('Letter circle with letter "' + self._letter + '"')
        
    def paintEvent(self, e):

        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()
        
    def drawWidget(self, qp):
        size = self.size()
        w = size.width()
        h = size.height()

        self.draw_ellipse(qp, w, h)
        self.draw_letter(qp, w, h)

    def draw_ellipse(self, qp, w, h):
        pen = QtGui.QPen(QtGui.QColor(20, 20, 20), 1, QtCore.Qt.SolidLine)

        qp.setPen(pen)
        qp.setBrush(QtCore.Qt.NoBrush)
        
        qp.drawEllipse(0, 0, w-1, h-1)

    def draw_letter(self, qp, w, h):
        font = QtGui.QFont('Serif', FONT_SIZE, QtGui.QFont.Light)
        qp.setFont(font)

        metrics = qp.fontMetrics()
        fw = metrics.width(self._letter)
        fh = metrics.height()
        qp.drawText((w - fw)/2, (h + fh/2)/2, self._letter)
        
class LetterListWidget(QWidget):
    def __init__(self):
        super(LetterListWidget, self).__init__()
        self.setMinimumSize(2 * MARGIN_SIZE + BALL_SIZE,
                            2 * MARGIN_SIZE + BALL_SIZE)

        self._letters = ['A', 'B', 'C', 'D']

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(LetterCircleWidget(self._letters[0]))
        for lett_widget in imap(LetterCircleWidget, self._letters[1:]):
            hbox.addWidget(SimpleHStickWidget())
            hbox.addWidget(lett_widget)
        hbox.addStretch(1)

        vbox = QtGui.QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        
        self.setLayout(vbox)

    def paintEvent(self, e):

        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()
        
    def drawWidget(self, qp):
        size = self.size()
        w = size.width()
        h = size.height()

        pen = QtGui.QPen(QtGui.QColor(20, 20, 20), 1, QtCore.Qt.SolidLine)

        qp.setPen(pen)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawRect(0, 0, w-1, h-1)

