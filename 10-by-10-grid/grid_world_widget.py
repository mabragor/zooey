from PyQt4 import (QtCore, QtGui)
from PyQt4.QtGui import (QWidget, QImage, QPainter, QCursor, QColor)
from PyQt4.QtCore import (QRectF, QPointF, QSizeF, QSize, QString)
import time
import random
from itertools import imap
from operator import add, sub

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

class DeleteBoxReversibleChange(ReversibleChange):
    def __init__(self, world=None, box_id=None):
        super(DeleteBoxReversibleChange, self).__init__()
        self._world = world
        self._box_id = box_id
        box = self._world.find_box_by_id(box_id)
        self._color = box.color
        (self._i, self._j) = self._world.box_position(box)

    def inverse(self):
        return CreateBoxReversibleChange(world=self._world,
                                         box_id=self._box_id,
                                         i=self._i,
                                         j=self._j,
                                         color=self._color)

    def make(self):
        self._world.delete_box(self._box_id, self._i, self._j)

        
class CreateBoxReversibleChange(ReversibleChange):
    def __init__(self, world=None, box_id=None, i=None, j=None, color=None):
        super(CreateBoxReversibleChange, self).__init__()
        self._world = world
        self._box_id = box_id
        self._i = i
        self._j = j
        self._color = color

    def inverse(self):
        return DeleteBoxReversibleChange(world=self._world,
                                         box_id=self._box_id)

    def make(self):
        self._world.create_box(self._box_id, self._i, self._j, self._color)

class MoveBoxReversibleChange(ReversibleChange):
    def __init__(self, world=None, box_id=None, position=None, delta=None):
        super(MoveBoxReversibleChange, self).__init__()
        self._world = world
        self._box_id = box_id
        self._position = position
        self._delta = delta

    def inverse(self):
        return MoveBoxReversibleChange(world=self._world,
                                       box_id=self._box_id,
                                       position=tuple(imap(add, self._position, self._delta)),
                                       delta=tuple(imap(sub, self._delta)))

    def make(self):
        self._world.move_box(self._box_id, self._position, self._delta)
        
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

    def finalize(self):
        ### The aim of this method is to perform various auxiliary actions, which do not need to be replayed later
        pass
    
    def __call__(self):
        ### Just for convenience we declare this calling interface
        return self.act()
    
    def act(self):
        '''Returns True if action was performed and False otherwise'''
        if self.guard():
            self.precalculate()
            self.change.make()
            self.finalize()
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


class DeleteSelectedBoxAction(Action):
    def __init__(self, grid_world):
        super(DeleteSelectedBoxAction, self).__init__()
        self._grid_world = grid_world
        self._my_box = None

    def guard(self):
        it = self._grid_world.selected_box()
        if it is not None:
            self._my_box = it
            return True
        return False

    def precalculate(self):
        self.change = DeleteBoxReversibleChange(world=self._grid_world,
                                                box_id=self._my_box.ID)

    def finalize(self):
        self._grid_world.deselect()

class CreateBoxAction(Action):
    def __init__(self, grid_world):
        super(CreateBoxAction, self).__init__()
        self._grid_world = grid_world
        self._my_box = None
        self._i = None
        self._j = None

    def __call__(self, i, j):
        return self.act(i, j)

    def act(self, i, j):
        self._i = i
        self._j = j
        return super(CreateBoxAction, self).act()

    def guard(self):
        return self._grid_world.cell_is_free(self._i, self._j)

    def precalculate(self):
        self.change = CreateBoxReversibleChange(world=self._grid_world,
                                                box_id=self._grid_world.new_object_id(),
                                                i=self._i,
                                                j=self._j,
                                                color=ColoredBox.default_color())

class MoveBoxAction(Action):
    def __init__(self, grid_world):
        super(MoveBoxAction, self).__init__()
        self._grid_world = grid_world
        self._my_box = None
        self._i = None
        self._j = None
        ### These two need to be redefined by the concrete subclasses:
        self._delta_i = None
        self._delta_j = None

    def guard(self):
        it = self._grid_world.selected_box()
        if it is not None:
            (self._i, self._j) = self._grid_world.box_position(it)
            if (self._grid_world.point_in_bounds_p(self._i + self._delta_i,
                                                   self._j + self._delta_j)
                and self._grid_world.cell_is_free(self._i + self._delta_i,
                                                  self._j + self._delta_j)):
                self._my_box = it
                return True
        return False

    def precalculate(self):
        self.change = MoveBoxReversibleChange(world=self._grid_world,
                                              box_id=self._my_box.ID,
                                              position=self._grid_world.selected_position(),
                                              delta=(self._delta_i, self._delta_j))

    def finalize(self):
        self._grid_world.move_selection((self._delta_i, self._delta_j))
        
        
class MoveBoxUpAction(MoveBoxAction):
    def __init__(self, grid_world):
        super(MoveBoxUpAction, self).__init__(grid_world)
        self._delta_i = 0
        self._delta_j = -1

class MoveBoxDownAction(MoveBoxAction):
    def __init__(self, grid_world):
        super(MoveBoxDownAction, self).__init__(grid_world)
        self._delta_i = 0
        self._delta_j = 1

class MoveBoxLeftAction(MoveBoxAction):
    def __init__(self, grid_world):
        super(MoveBoxLeftAction, self).__init__(grid_world)
        self._delta_i = -1
        self._delta_j = 0

class MoveBoxRightAction(MoveBoxAction):
    def __init__(self, grid_world):
        super(MoveBoxRightAction, self).__init__(grid_world)
        self._delta_i = 1
        self._delta_j = 0
        
        
class ColoredBox(object):
    def __init__(self, id=None, color=None):
        if color is None:
            self.color = self.default_color()
        else:
            self.color = color
        self.ID = id

    @staticmethod
    def default_color():
        return RED
        
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

    def cell_is_free(self, i, j):
        return ((i is not None)
                and (j is not None)
                and self._field[i][j] is None)

    def new_object_id(self):
        return self._free_id_counter
    
    def try_select_box_at_point(self, i, j):
        if self._field[i][j] is not None:
            self._select_i = i
            self._select_j = j
            return True
        return None

    def find_box_by_id(self, id):
        return self._boxes.get(id, None)

    def box_position(self, box):
        for i, row in enumerate(self._field):
            for j, elt_box in enumerate(row):
                if box == elt_box:
                    return (i, j)
        raise "Box position was not found, which is unacceptable for internal function"

    def selected_box(self):
        i = self._select_i
        j = self._select_j
        if i is not None and j is not None:
            return self._field[i][j]
        return None

    def deselect(self):
        self._select_i = None
        self._select_j = None
    
    def selected_position(self):
        i = self._select_i
        j = self._select_j
        if i is None or j is None:
            raise "Selection position should be definite when calling this utility function."
        return (i, j)

    def point_in_bounds_p(self, i, j):
        return ((i >= 0)
                and (i < THE_WIDTH)
                and (j >= 0)
                and (j < THE_HEIGHT))
    
    def delete_box(self, box_id, i, j):
        self._field[i][j] = None
        del self._boxes[box_id]
        if self._free_id_counter == 1 + box_id:
            self._free_id_counter -= 1

    def create_box(self, box_id, i, j, color):
        box = ColoredBox(id=box_id, color=color)
        self._field[i][j] = box
        self._boxes[box_id] = box
        if self._free_id_counter == box_id:
            self._free_id_counter += 1

    def move_box(self, box_id, position, delta):
        it = self._field[position[0]][position[1]]
        self._field[position[0]][position[1]] = None
        self._field[position[0] + delta[0]][position[1] + delta[1]] = it

    def move_selection(self, delta):
        if (self._select_i is None
            or self._select_j is None):
            raise "Selection should be definite when calling this utility function"
        self._select_i += delta[0]
        self._select_j += delta[1]
        
    
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
        self.key_press_dict = { QtCore.Qt.Key_Up : MoveBoxUpAction(self.world),
                                QtCore.Qt.Key_Down : MoveBoxDownAction(self.world),
                                QtCore.Qt.Key_Left : MoveBoxLeftAction(self.world),
                                QtCore.Qt.Key_Right : MoveBoxRightAction(self.world),
                                QtCore.Qt.Key_Space : ChangeSelectedBoxColorAction(self.world),
                                QtCore.Qt.Key_D : DeleteSelectedBoxAction(self.world) }
        self.mouse_click_dict = { QtCore.Qt.LeftButton : CreateBoxAction(self.world),
                                  QtCore.Qt.RightButton : self.world.try_select_box_at_point }
        
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
        cmd = self.mouse_click_dict.get(event.button(), None)
        if cmd is not None:
            i = coerce_to_grid(event.x(), THE_WIDTH)
            j = coerce_to_grid(event.y(), THE_HEIGHT)
            if cmd(i,j):
                self.redraw_and_update()
        super(GridWorldWidget, self).mousePressEvent(event)
        
