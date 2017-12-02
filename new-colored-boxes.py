#!/usr/bin/python2

import sys
from PyQt4.QtGui import QPalette, QWidget, QApplication, QPainter
from PyQt4 import QtCore
from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4.QtCore import QPoint

from random import randint

# import popplerqt4


class ColoredCircle(object):
    def __init__(self, x, y, r=10):
        self.center = QPoint(x, y)
        self.radius = r
        self.color = QtGui.QColor(randint(0, 255),
                                  randint(0, 255),
                                  randint(0, 255))

    def draw(self, widget):
        p = QPainter(widget)
        p.setBrush(QtGui.QBrush(self.color))
        p.drawEllipse(self.center, self.radius, self.radius)

        
class ColoredSquare(object):
    def __init__(self, x, y, half_width=10):
        self.center = QPoint(x, y)
        self.half_width = half_width
        self.color = QtGui.QColor(randint(0, 255),
                                  randint(0, 255),
                                  randint(0, 255))

    def draw(self, widget):
        p = QPainter(widget)
        p.setBrush(QtGui.QBrush(self.color))
        p.drawRect(self.center.x() - self.half_width,
                   self.center.y() - self.half_width,
                   self.half_width * 2,
                   self.half_width * 2)
        

class NewColoredBoxes(QWidget):
    def __init__(self):
        # ### Standard initialization of a superclass
        super(NewColoredBoxes, self).__init__(None)

        # ### Set the background color
        p = QPalette()
        p.setColor(QPalette.Background, QtCore.Qt.white)
        self.setPalette(p)

        # ### The objects (contained) in the current widget
        self.objects = []
        
        self.hide()

    def start(self):
        self.showFullScreen()
        self.show()

    def stop(self):
        self.hide()
        QtCore.QCoreApplication.instance().quit()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.stop()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.add_circle_at_point(event.x(), event.y())
        elif event.button() == QtCore.Qt.RightButton:
            self.add_square_at_point(event.x(), event.y())
        self.update()

    def add_circle_at_point(self, x, y):
        self.objects.append(ColoredCircle(x, y))

    def add_square_at_point(self, x, y):
        self.objects.append(ColoredSquare(x, y))

    def paintEvent(self, event):
        for obj in self.objects:
            obj.draw(self)
        
        
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = NewColoredBoxes()
    ex.start()
    sys.exit(app.exec_())
