from PyQt4 import (QtCore, QtGui)
from PyQt4.QtGui import (QWidget, QImage, QPainter, QCursor, QColor)
from PyQt4.QtCore import (QRectF, QPointF, QSizeF, QSize, QString)
import time
import random

THE_WIDTH = 10
THE_HEIGHT = 10
BOX_SIZE = 40
SKIP_SIZE = 5

GRAY = (100, 100, 100)
NAVYBLUE = (60, 60, 100)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 128, 0)
PURPLE = (255, 0, 255)
CYAN = (0, 255, 255)

ALLCOLORS = (RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, CYAN)

class ColoredBox(object):
    def __init__(self):
        self.color = RED

    def randomly_change_color(self):
        newcolor = ALLCOLORS[random.randint(0, len(ALLCOLORS)-1)]
        while self.color == newcolor:
            newcolor = ALLCOLORS[random.randint(0, len(ALLCOLORS)-1)]
        self.color = newcolor
        
    def draw(self, image, i, j):
        p = QPainter()
        p.begin(image)
        p.fillRect(i * (SKIP_SIZE + BOX_SIZE),
                   j * (SKIP_SIZE + BOX_SIZE),
                   BOX_SIZE,
                   BOX_SIZE,
                   apply(QColor, self.color))

        p.end()

class GridWorld(object):
    def __init__(self):
        self._field = [[None for x in xrange(THE_WIDTH)] for y in xrange(THE_HEIGHT)]
    
    def draw(self, image):
        ### Obviously, for now we are pretty coupled to Qt
        self.draw_empty_board(image)
        self.draw_boxes(image)

    def draw_empty_board(self, image):
        image.fill(QtCore.Qt.white)
        p = QPainter()
        p.begin(image)
        for i in xrange(THE_WIDTH):
            for j in xrange(THE_HEIGHT):
                p.drawRect(i * (SKIP_SIZE + BOX_SIZE),
                           j * (SKIP_SIZE + BOX_SIZE),
                           BOX_SIZE, BOX_SIZE)
        p.end()

    def draw_boxes(self, image):
        for i, row in enumerate(self._field):
            for j, box in enumerate(row):
                if box:
                    box.draw(image, i, j)

    def try_create_box_at_point(self, i, j):
        if self._field[i][j]:
            return None
        it = ColoredBox()
        self._field[i][j] = it
        return it
                    
def coerce_to_grid(coord, size):
    i = coord / (BOX_SIZE + SKIP_SIZE)
    if (i < size) and (coord % (BOX_SIZE + SKIP_SIZE) < BOX_SIZE):
        return i
    return None
                    
class GridWorldWidget(QWidget):
    def __init__(self):
        super(GridWorldWidget, self).__init__(None)
        self.world = GridWorld()
        self.make_new_qimage(self.frameSize())
        self.show()

    def start(self):
        # self.showFullScreen()
        self.show()
        self.redraw_and_update()
        
    def stop(self):
        QtCore.QCoreApplication.instance().quit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.the_qimage, 0, 0, 0, 0)

    def make_new_qimage(self, size):
        self.the_qimage = QImage(size, QImage.Format_ARGB32)
        
    def redraw(self):
        self.world.draw(self.the_qimage)
        
    def redraw_and_update(self):
        ### OK, for now just a simple redraw: we have white field with a black box in the middle
        self.redraw()
        self.update()

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == QtCore.Qt.Key_Escape:
            self.stop()
            return

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            i = coerce_to_grid(event.x(), THE_WIDTH)
            j = coerce_to_grid(event.y(), THE_HEIGHT)
            if i and j:
                if self.world.try_create_box_at_point(i, j):
                    self.redraw_and_update()
        elif event.button() == QtCore.Qt.RightButton:
            i = coerce_to_grid(event.x(), THE_WIDTH)
            j = coerce_to_grid(event.y(), THE_HEIGHT)
            if i and j:
                if self.world.try_select_box_at_point(i, j):
                    self.redraw_and_update()
        else:
            return
        
        
