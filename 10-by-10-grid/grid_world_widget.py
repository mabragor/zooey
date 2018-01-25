from PyQt4 import (QtCore, QtGui)
from PyQt4.QtGui import (QWidget, QImage, QPainter, QCursor, QColor)
from PyQt4.QtCore import (QRectF, QPointF, QSizeF, QSize, QString)
import time
import random

THE_WIDTH = 10
THE_HEIGHT = 10
BOX_SIZE = 40
SKIP_SIZE = 5
FOCUS_LINE_WIDTH = 6

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

class ReversibleChange(object):
    def make(self):
        pass
    def inverse(self):
        pass

class ChangeBoxColorReversibleChange(ReversibleChange):
    def __init__(self, world=None, box_id=None, from_color=None, to_color=None):
        super(ChangeBoxColorReversibleChange, self).__init__()
        self._world = world
        self._box_id = box_id
        self._from_color = from_color
        self._to_color = to_color

    def inverse(self):
        return ChangeBoxColorReversibleChange(world=self._world,
                                              box_id=self._box_id,
                                              from_color=self._to_color,
                                              to_color=self._from_color)
    
    def make(self):
        it = self._world.find_box_by_id(self._box_id)
        if it is None:
            raise "Couldn't find a box on which to perform change color action"
        it.color = self._to_color
    

class Action(object):
    def __init__(self):
        self.change = None
        
    def guard(self):
        '''The predicate that should succeed for a command to be applicable (by the user).
        Always succeeds by default.'''
        return True
    
    def precalculate(self):
        ### The aim of this method is to set self.change to some reversible change object
        pass

    def __call__(self):
        ### Just for convenience we declare this calling interface
        return self.act()
    
    def act(self):
        '''Returns True if action was performed and False otherwise'''
        if self.guard():
            self.precalculate()
            self.change.make()
            return True
        return False
    
class ChangeSelectedBoxColorAction(Action):
    def __init__(self, grid_world):
        super(ChangeSelectedBoxColorAction, self).__init__()
        self._grid_world = grid_world
        self._my_box = None

    def guard(self):
        it = self._grid_world.selected_box()
        if it is not None:
            self._my_box = it
            return True
        return False

    def precalculate(self):
        self.change = ChangeBoxColorReversibleChange(world=self._grid_world,
                                                     box_id=self._my_box.ID,
                                                     from_color=self._my_box.color,
                                                     to_color=self._my_box.new_random_color())
                                                     
    
class ColoredBox(object):
    def __init__(self, id=None):
        self.color = RED
        self.ID = id

    def new_random_color(self):
        newcolor = ALLCOLORS[random.randint(0, len(ALLCOLORS)-1)]
        while self.color == newcolor:
            newcolor = ALLCOLORS[random.randint(0, len(ALLCOLORS)-1)]
        return newcolor
        
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
        self._select_i = None
        self._select_j = None

        self._boxes = {}

        self._free_id_counter = 0
    
    def draw(self, image):
        ### Obviously, for now we are pretty coupled to Qt
        self.draw_empty_board(image)
        self.draw_boxes(image)
        self.draw_selection(image)

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

    def draw_selection(self, image):
        if self._select_i is not None and self._select_j is not None:
            p = QPainter()
            p.begin(image)
            p.setPen(QtGui.QPen(QtCore.Qt.yellow, FOCUS_LINE_WIDTH/2, QtCore.Qt.SolidLine))
            p.drawRect(- FOCUS_LINE_WIDTH + self._select_i * (SKIP_SIZE + BOX_SIZE),
                       - FOCUS_LINE_WIDTH + self._select_j * (SKIP_SIZE + BOX_SIZE),
                       BOX_SIZE + 2 * FOCUS_LINE_WIDTH, BOX_SIZE + 2 * FOCUS_LINE_WIDTH)
            p.end()

    def draw_boxes(self, image):
        for i, row in enumerate(self._field):
            for j, box in enumerate(row):
                if box:
                    box.draw(image, i, j)

    def try_create_box_at_point(self, i, j):
        if self._field[i][j] is not None:
            return None
        it = ColoredBox(id=self._free_id_counter)
        self._boxes[self._free_id_counter] = it
        self._field[i][j] = it
        self._free_id_counter += 1

        return it

    def try_select_box_at_point(self, i, j):
        if self._field[i][j] is not None:
            self._select_i = i
            self._select_j = j
            return True
        return None

    def find_box_by_id(self, id):
        return self._boxes.get(id, None)

    ### The previous version of changing of box color,
    ### which we now try to convert to the Action-interface.
    # def try_change_selected_box_color(self):
    #     i = self._select_i
    #     j = self._select_j
    #     if i is not None and j is not None:
    #         it = self._field[i][j]
    #         if it is not None:
    #             it.randomly_change_color()
    #             return True
    #     return False

    def selected_box(self):
        i = self._select_i
        j = self._select_j
        if i is not None and j is not None:
            return self._field[i][j]
        return None
    
    def try_delete_selected_box(self):
        i = self._select_i
        j = self._select_j
        if i is not None and j is not None:
            it = self._field[i][j]
            if it is not None:
                id = it.ID
                self._field[i][j] = None
                del self._boxes[id]
                self._select_i = None
                self._select_j = None
                
                return True
        return False

    def try_move_selected_box_up(self):
        i = self._select_i
        j = self._select_j
        if i is not None and j is not None and j > 0:
            it = self._field[i][j]
            it_up = self._field[i][j-1]
            if it is not None and it_up is None:
                self._field[i][j-1] = it
                self._field[i][j] = None
                self._select_j -= 1
                return True
        return False

    def try_move_selected_box_down(self):
        i = self._select_i
        j = self._select_j
        if i is not None and j is not None and j < THE_HEIGHT - 1:
            it = self._field[i][j]
            it_down = self._field[i][j+1]
            if it is not None and it_down is None:
                self._field[i][j+1] = it
                self._field[i][j] = None
                self._select_j += 1
                return True
        return False

    def try_move_selected_box_left(self):
        i = self._select_i
        j = self._select_j
        if i is not None and j is not None and i > 0:
            it = self._field[i][j]
            it_left = self._field[i-1][j]
            if it is not None and it_left is None:
                self._field[i-1][j] = it
                self._field[i][j] = None
                self._select_i -= 1
                return True
        return False

    def try_move_selected_box_right(self):
        i = self._select_i
        j = self._select_j
        if i is not None and j is not None and i < THE_WIDTH - 1:
            it = self._field[i][j]
            it_right = self._field[i+1][j]
            if it is not None and it_right is None:
                self._field[i+1][j] = it
                self._field[i][j] = None
                self._select_i += 1
                return True
        return False
    
    
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

        ### Initialize keybindings : later we'll do this in the separate interface layer,
        ### so it can be kludgy for now.
        self.key_press_dict = { QtCore.Qt.Key_Up : self.world.try_move_selected_box_up,
                                QtCore.Qt.Key_Down : self.world.try_move_selected_box_down,
                                QtCore.Qt.Key_Left : self.world.try_move_selected_box_left,
                                QtCore.Qt.Key_Right : self.world.try_move_selected_box_right,
                                QtCore.Qt.Key_Space : ChangeSelectedBoxColorAction(self.world),
                                QtCore.Qt.Key_D : self.world.try_delete_selected_box }
        
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
        else:
            it = self.key_press_dict.get(event.key(), None)
            if it:
                if it():
                    self.redraw_and_update()
                    return
        super(GridWorldWidget, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            i = coerce_to_grid(event.x(), THE_WIDTH)
            j = coerce_to_grid(event.y(), THE_HEIGHT)
            if i is not None and j is not None:
                if self.world.try_create_box_at_point(i, j):
                    self.redraw_and_update()
        elif event.button() == QtCore.Qt.RightButton:
            i = coerce_to_grid(event.x(), THE_WIDTH)
            j = coerce_to_grid(event.y(), THE_HEIGHT)
            if i is not None and j is not None:
                if self.world.try_select_box_at_point(i, j):
                    self.redraw_and_update()
        else:
            return
        
        
