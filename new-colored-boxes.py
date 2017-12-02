#!/usr/bin/python2

import sys
from PyQt4.QtGui import QPalette, QWidget, QApplication, QPainter
from PyQt4 import QtCore
from PyQt4 import Qt

# import popplerqt4


class NewColoredBoxes(QWidget):
    def __init__(self):
        # ### Standard initialization of a superclass
        super(NewColoredBoxes, self).__init__(None)

        # ### Set the background color
        p = QPalette()
        p.setColor(QPalette.Background, QtCore.Qt.white)
        self.setPalette(p)

        self.hide()

    def start(self):
        self.showFullScreen()
        self.show()


if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = NewColoredBoxes()
    ex.start()
    sys.exit(app.exec_())
