
from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QApplication, QWidget
from grid_world_widget import GridWorldWidget
from letter_list_widget import LetterListWidget
import sys

class Example(QWidget):
    def __init__(self):
        super(Example, self).__init__()

        self.initUI()
    
    def initUI(self):
        gw = GridWorldWidget()

        llw = LetterListWidget()
        scroll_area = QtGui.QScrollArea()
        llw.sizePolicy().setVerticalPolicy(QtGui.QSizePolicy.Fixed)
        scroll_area.setWidget(llw)
        scroll_area.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)
        scroll_area.setLineWidth(2)
        
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(gw)
        hbox.addStretch(1)
        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        vbox.addWidget(scroll_area)
        self.setLayout(vbox)

        ### TODO : we'll change this once we do more fancy input handling
        self.setFocusProxy(gw)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFocus()

        self.setGeometry(300, 300, 390, 210)
        self.setWindowTitle('Simple grid game')
        self.show()
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())
