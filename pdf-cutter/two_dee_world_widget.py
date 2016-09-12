### 2dworld_widget.py
### The simple 2d world, where colored boxes (and later, more complicated objects) would live.

from __future__ import with_statement

from PyQt4 import (QtCore, QtGui)
from PyQt4.QtGui import (QWidget, QImage, QPainter, QCursor)
from PyQt4.QtCore import (QRectF, QPointF, QSizeF, QSize, QString, QObject, pyqtSignal, pyqtSlot)
import time
import random

# from linear_transform import linear_transform
from modal_dispatcher import (ModalDispatcher, DontWannaStart)
from utils import mysql_zooey_connection

THE_BLACK_BOX = QRectF(-50, -50, 100, 100)
FRAME_START_RATIO = 1.0

MOVE_SPEED = 10

FOCUS_LINE_WIDTH = 5

NEW_BOX_ONSCREEN_SIZE = 50.0
BOX_ZOOM_DELTA = 0.01
BOX_MOVE_DELTA = 1
CUTLINE_MOVE_DELTA = 0.01

ZOOEY_LOGIN='zooey'
ZOOEY_PASSWD='zooey-hey-zoomable'

class Action(object):
    def __init__(self, world, interval = 10):
        self.world = world
        self.init_timer(interval)

    def init_timer(self, interval):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.body)

    def on_start(self):
        self.timer.start()

    def on_stop(self):
        self.timer.stop()

    def body(self):
        pass

class OneshotAction(Action):
    '''For this action all the logic is supposed to go to init and on_stop'''
    def __init__(self, world):
        self.world = world
    def on_start(self):
        pass
    def on_stop(self):
        pass
    def body(self):
        pass
    
class ZoomCamera(Action):
    def __init__(self, world, direction):
        if direction == 'in':
            self.zoom_delta = 0.01
        elif direction == 'out':
            self.zoom_delta = -0.01
        else:
            raise Exception("Bad zoom direction" + str(direction))
        super(ZoomCamera, self).__init__(world)

    def body(self):
        self.world.camera.zoom(1.0 + self.zoom_delta)

def glue_selected_boxes(world):
    if not world.planar_world.have_narity_focus(2):
        raise DontWannaStart

    world.planar_world.try_glue_boxes(world.planar_world.get_focused(1),
                                      world.planar_world.get_focused(2))

class SelectIndex(OneshotAction):
    def __init__(self, world, index):
        world.the_index = index
        super(SelectIndex, self).__init__(world)

    def on_stop(self):
        self.world.the_index = 1

def cut_selected_box(world):
    if not world.planar_world.have_narity_focus(1):
        raise DontWannaStart

    world.planar_world.try_cut_box(world.planar_world.get_focused(1))

class MoveCutlineSelectedBox(Action):
    def __init__(self, world, direction):
        if not world.planar_world.have_narity_focus(1):
            raise DontWannaStart
        
        if direction == 'up':
            self.move_y = -CUTLINE_MOVE_DELTA
        elif direction == 'down':
            self.move_y = CUTLINE_MOVE_DELTA
        else:
            raise Exception("Bad move cutline direction" + str(direction))
        super(MoveCutlineSelectedBox, self).__init__(world)

    def body(self):
        self.world.planar_world.move_selected_box_cutline(self.move_y)

class MoveSelectedBox(Action):
    def __init__(self, world, direction):
        if not world.planar_world.have_narity_focus(1):
            raise DontWannaStart

        direction_map = { 'left' : (-BOX_MOVE_DELTA, 0),
                          'right' : (BOX_MOVE_DELTA, 0),
                          'up' : (0, -BOX_MOVE_DELTA),
                          'down' : (0, BOX_MOVE_DELTA) }
        (self.move_x, self.move_y) = direction_map[direction]
        super(MoveSelectedBox, self).__init__(world)

    def body(self):
        self.world.planar_world.try_move_selected_box(self.move_x, self.move_y)

def delete_selected_box(world):
    if not world.planar_world.have_narity_focus(1):
        raise DontWannaStart

    world.planar_world.delete_selected_box()
    
class ScaleSelectedBox(Action):
    def __init__(self, world, direction):
        if not world.planar_world.have_narity_focus(1):
            raise DontWannaStart
        
        if direction == 'enlarge':
            self.zoom_delta = BOX_ZOOM_DELTA
        elif direction == 'shrink':
            self.zoom_delta = -BOX_ZOOM_DELTA
        else:
            raise Exception("Bad scale direction" + str(direction))

        if world.the_index == 9:
            self.scaling_type = 'width'
        elif world.the_index == 0:
            self.scaling_type = 'height'
        else:
            self.scaling_type = 'zoom'
        
        super(ScaleSelectedBox, self).__init__(world)

    def body(self):
        self.world.planar_world.try_zoom_selected_box(1.0 + self.zoom_delta, scaling_type=self.scaling_type)

        
def unfocus_everything(world):
    world.planar_world.unfocus()
    
def focus_box_at_point(world):
    abs_pos = world.cursor_abs()
    box = world.planar_world.find_box_at_point(abs_pos.x(), abs_pos.y())
                                                   
    if box:
        world.planar_world.focus(box, world.the_index)

class MoveCursor(Action):
    def __init__(self, world, direction):
        direction_map = { 'left' : (-MOVE_SPEED, 0),
                          'right' : (MOVE_SPEED, 0),
                          'up' : (0, -MOVE_SPEED),
                          'down' : (0, MOVE_SPEED) }
        (self.move_x, self.move_y) = direction_map[direction]
        super(MoveCursor, self).__init__(world)

    def body(self):
        pos = QCursor().pos()
        QCursor().setPos(pos.x() + self.move_x,
                         pos.y() + self.move_y)

class MoveCamera(Action):
    def __init__(self, world, direction):
        direction_map = { 'left' : (-MOVE_SPEED, 0),
                          'right' : (MOVE_SPEED, 0),
                          'up' : (0, -MOVE_SPEED),
                          'down' : (0, MOVE_SPEED) }
        (self.move_x, self.move_y) = direction_map[direction]
        super(MoveCamera, self).__init__(world)
        
    def body(self):
        self.world.camera.move(self.move_x, self.move_y)

def create_box(world):
    abs_pos = world.cursor_abs()
    abs_size = world.camera.cam_to_abs(world.screen_to_cam(NEW_BOX_ONSCREEN_SIZE))
    box = world.planar_world.try_create_new_box(abs_pos.x(), abs_pos.y(), abs_size)
                                                   
    if box:
        world.planar_world.focus(box)

def save_everything(world):
    with mysql_zooey_connection(ZOOEY_LOGIN, ZOOEY_PASSWD) as conn:
        world.camera.mysql_save(conn)

def load_everything(world):
    world.mysql_load_camera()
        
def change_selected_box_color_to_next(world):
    if not world.planar_world.have_narity_focus(1):
        raise DontWannaStart

    world.planar_world.get_focused(1).change_color_to_the_next()
        
class ChangingObject(QObject):
    changed = pyqtSignal()

class Camera(ChangingObject):
    def __init__(self, x = 0.0, y = 0.0, distance = 1.0, id=None):
        super(Camera, self).__init__()
        self.x = x
        self.y = y
        # "absolute" sizes are distance * "camera" sizes -- the ones we see on screen
        self.d = float(distance)
        self.d0 = 1.0
        self.id = id

    def zoom(self, zoom):
        self.d /= zoom
        self.changed.emit()

    def move(self, dx, dy):
        self.x += dx * self.d/self.d0
        self.y += dy * self.d/self.d0
        self.changed.emit()
        
    def abs_to_cam(self, thing):
        if isinstance(thing, QPointF):
            pt = QPointF(self.x, self.y)
            return (thing - pt) * self.d0/self.d
        if isinstance(thing, float):
            return thing * self.d0/ self.d
        if isinstance(thing, QRectF):
            return QRectF(self.abs_to_cam(thing.topLeft()),
                          QSizeF(self.abs_to_cam(thing.width()),
                                 self.abs_to_cam(thing.height())))
        raise Exception("Unknown type %s" % thing)
    
    def cam_to_abs(self, thing):
        if isinstance(thing, QPointF):
            pt = QPointF(self.x, self.y)
            return pt + thing * self.d/self.d0
        if isinstance(thing, float):
            return thing /self.d0 * self.d
        if isinstance(thing, QRectF):
            return QRectF(self.cam_to_abs(thing.topLeft()),
                          QSizeF(self.cam_to_abs(thing.width()),
                                 self.cam_to_abs(thing.height())))

        raise Exception("Unknown type %s" % thing)

    @staticmethod
    def mysql_load(conn, camera_id):
        '''This will load a camera object from MySQL for us.'''
        cur = conn.cursor()
        cur.execute('select camera_id, world_id, x, y, d from cameras where camera_id = 1')
        res = cur.fetchone()
        if res is not None:
            (cam_id, world_id, x, y ,d) = res
            return Camera(x=x, y=y, distance=d, id=cam_id)
        return None
    
    def mysql_save(self, conn):
        # TODO : actually make multiple world IDs possible
        res = conn.cursor().execute('''
insert into cameras (camera_id, world_id, x, y, d)
    values (%(camera_id)s, %(world_id)s, %(x)s, %(y)s, %(d)s)
    on duplicate key update
        world_id = values(world_id),
        x = values(x),
        y = values(y),
        d = values(d)
        ''', { 'camera_id' : self.id, 'world_id' : 1, 'x' : self.x, 'y' : self.y, 'd' : self.d})
        print res
        
        
    
COLORED_BOX_INIT_SIZE = 10
CUT_SPLIT_MOVE = 1

COLORS = ["white", "black", "red", "darkRed", "green", "darkGreen",
          "blue", "darkBlue", "cyan", "darkCyan", "magenta", "darkMagenta",
          "yellow", "darkYellow", "gray", "darkGray", "lightGray"]

class Color(ChangingObject):
    def __init__(self, color=None):
        super(Color, self).__init__()
        self.change(color)

    def copy(self):
        return Color(self._color)
        
    def change(self, new_color=None):
        if new_color is None:
            self._color = random.randint(0, len(COLORS) - 1)
        elif new_color == 'next':
            self._color = (self._color + 1) % len(COLORS)
        else:
            self._color = new_color
        self.changed.emit()

    def color(self):
        return getattr(QtCore.Qt, COLORS[self._color])
        
    def draw(self, image):
        image.fill(self.color())

        

class ColoredBox(ChangingObject):
    def __init__(self, x=0, y=0, w=COLORED_BOX_INIT_SIZE, h=COLORED_BOX_INIT_SIZE, color=None):
        super(ColoredBox, self).__init__()
        self.x = float(x) # x and y are coordinates of the CENTER of the box (center of mass if you will)
        self.y = float(y)
        self.w = float(w)
        self.h = float(h)

        self.init_color(color)

        self.cut_line = 0.5
            
        self._image = None
        self._cache_valid = False

    def init_color(self, color):
        # the value True means we do shallow copy (and don't have an underlying color object)
        if color == True:
            self.color = None
        else:
            if isinstance(color, Color):
                self.color = color
            else:
                self.color = Color(color)
                
            self.color.changed.connect(self.on_change)

    def on_change(self):
        self._cache_valid = False
        self.changed.emit()
        
    def copy(self):
        return ColoredBox(x=self.x, y=self.y, w=self.w, h=self.h, color=self.color.copy())

    def shallow_copy(self):
        # we don't copy a color object
        return ColoredBox(x=self.x, y=self.y, w=self.w, h=self.h, color=True)
    
    def intersects(self, other_box):
        return ((abs(self.x - other_box.x) < (self.w + other_box.w)/2)
                and (abs(self.y - other_box.y) < (self.h + other_box.h)/2))

    def contains_point(self, x, y):
        return (abs(self.x - x) < self.w/2
                and abs(self.y - y) < self.h/2)
    
    def zoom(self, zoom, scaling_type='zoom'):
        if scaling_type == 'height':
            self.h *= zoom
        elif scaling_type == 'width':
            self.w *= zoom
        elif scaling_type == 'zoom':
            self.w *= zoom
            self.h *= zoom
        else:
            raise Exception("Unexpected scaling type: %s" % scaling_type)

        self.on_change()
        return self

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        # here the trick is that cached image is still valid -- that's why we don't call on_change
        self.changed.emit()
        return self
    
    def image(self):
        if (not self._cache_valid) or (self._image is None):
            self._cache_valid = True
            self._image = QImage(QSize(self.w, self.h), QImage.Format_ARGB32)
            self.color.draw(self._image)
        return self._image

    def change_color(self, new_color=None):
        self.color.change(new_color)

    def change_color_to_the_next(self):
        self.change_color('next')
            
    def nd_zoom(self, zoom, scaling_type='zoom', shallow=True):
        '''ND stands for non-destructive -- creates a copy, and zooms it'''
        if shallow:
            return self.shallow_copy().zoom(zoom, scaling_type=scaling_type)
        else:
            return self.copy().zoom(zoom, scaling_type=scaling_type)

    def nd_move(self, dx, dy, shallow=True):
        '''ND stands for non-destructive -- creates a copy, and zooms it'''
        if shallow:
            return self.shallow_copy().move(dx, dy)
        else:
            return self.copy().move(dx, dy)
    
    def rectf(self):
        return QRectF(self.x - self.w/2, self.y - self.h/2, self.w, self.h)

    def cut(self):
        y1 = self.y - self.h/2 + self.cut_line * self.h / 2
        y2 = self.y + self.h/2 - (1.0 - self.cut_line) * self.h / 2

        # the point is that color object of the cut boxes will be shared
        # -- then, when we color-change one, we automatically also change another
        box1 = ColoredBox(x=self.x, y=y1, w=self.w, h=self.cut_line * self.h, color=self.color)
        box2 = ColoredBox(x=self.x, y=y2, w=self.w, h=(1.0 - self.cut_line) * self.h, color=self.color)
        box1.move(0, -CUT_SPLIT_MOVE)
        box2.move(0, CUT_SPLIT_MOVE)

        return (box1, box2)

    def glue(self, other_box):
        '''New box center is at the center of mass. Width is an average. Height is so that mass is preserved'''
        mean_width = (self.w + other_box.w)/2
        area1 = self.w * self.h
        area2 = other_box.w * other_box.h
        new_height1 = area1 / mean_width
        new_height2 = area2 / mean_width
        return ColoredBox(x = (area1 * self.x + area2 * other_box.x)/(area1+area2),
                          y = (area1 * self.y + area2 * other_box.y)/(area1+area2),
                          w = mean_width,
                          h = new_height1 + new_height2,
                          color = (self.color._color + other_box.color._color)/2)
    
class PlanarWorld(ChangingObject):
    '''The backend of the planar world
    It knows about objects in it, it can move them around, create and so on.'''
    def __init__(self, id=None):
        super(PlanarWorld, self).__init__()
        self.objects = []
        self.init_focus_registers()
        self._display_cutline = False
        self.id = id

    def intersects_with_something(self, box, *except_boxes):
        '''True if we intersect with anything except ourself and some 'exceptional' box'''
        for other in self.objects:
            if ((not box == other)
                and (other not in except_boxes)
                and box.intersects(other)):
                # print "INTERSECTS WITH SOMETHING:", box, except_box, other
                return True
        return False
        
    def try_create_new_box(self, x, y, size):
        new_box = ColoredBox(x = x, y = y, w=size, h=size)
        if self.intersects_with_something(new_box):
            return None
        self.add_box(new_box)
        self.changed.emit()
        return new_box

    def add_box(self, new_box):
        self.objects.append(new_box)
        new_box.changed.connect(self.changed)

    def remove_box(self, box):
        self.objects.remove(box)
        box.changed.disconnect(self.changed)
        
    def find_box_at_point(self, x, y):
        for box in self.objects:
            if box.contains_point(x, y):
                return box
        return None

    def init_focus_registers(self):
        self._focus = [None for i in xrange(0,10)]
    
    def focus(self, box, index=1):
        # first we unfocus the box if it's already focused
        try:
            i = self._focus.index(box)
            self._focus[i] = None
        except ValueError:
            pass

        # and then we focus it under a new register
        self._focus[(index + 10 - 1) % 10] = box
        self.changed.emit()

    def unfocus(self):
        '''Returns True if we've actually unfocused something'''
        flag = False
        for (i, item) in enumerate(self._focus):
            if item is not None:
                flag = True
                self._focus[i] = None
        if flag:
            self.changed.emit()
        return flag

    def have_narity_focus(self, arity):
        '''True, when we have enough or more registers populated to apply the function'''
        j = 0
        for item in self._focus:
            if item is None:
                break
            j += 1
            
        return j >= arity

    def get_focused(self, index):
        # This wrapping is done for convenience of keyboard mapping
        print "GET FOCUSED", self._focus
        return self._focus[(index + 10 - 1) % 10]
    
    def try_zoom_box(self, box, zoom, scaling_type='zoom'):
        # print "TRY ZOOM BOX: we enter"
        if not self.intersects_with_something(box.nd_zoom(zoom, scaling_type=scaling_type), box):
            # after we've checked non-destructively everything is OK, we do destructively in-place
            # print "TRY ZOOM BOX: we do not intersect with anything"
            return box.zoom(zoom, scaling_type=scaling_type)
        # print "TRY ZOOM BOX: we intersect with something"
        # Otherwise we don't change anything
        return None

    def try_zoom_selected_box(self, zoom, scaling_type='zoom'):
        return self.try_zoom_box(self.get_focused(1), zoom, scaling_type)
    
    def try_move_box(self, box, dx, dy):
        if not self.intersects_with_something(box.nd_move(dx, dy), box):
            # after we've checked non-destructively everything is OK, we do destructively in-place
            res = box.move(dx, dy)
            self.changed.emit()
            return res
        # Otherwise we don't change anything
        return None

    def try_move_selected_box(self, dx, dy):
        return self.try_move_box(self.get_focused(1), dx, dy)
    
    def try_cut_box(self, box):
        (box1, box2) = box.cut()
        if (not self.intersects_with_something(box1, box)
            and not self.intersects_with_something(box2, box)):
            self.remove_box(box)
            self.add_box(box1)
            self.add_box(box2)
            self.unfocus()
            self.focus(box1, 1)
            self.focus(box2, 2)
            self.changed.emit()
            return True
        return False

    def delete_selected_box(self):
        self.remove_box(self.get_focused(1))
        self.unfocus()
        self.changed.emit()
    
    def try_glue_boxes(self, box1, box2):
        new_box = box1.glue(box2)
        if not self.intersects_with_something(new_box, box1, box2):
            self.remove_box(box1)
            self.remove_box(box2)
            self.add_box(new_box)
            self.unfocus()
            self.focus(new_box, 1)
            self.changed.emit()
            return True
        return False

    def display_cutline(self):
        self._display_cutline = True
        self.changed.emit()

    def hide_cutline(self):
        self._display_cutline = False
        self.changed.emit()
        
    def move_selected_box_cutline(self, dy):
        focused_box = self.get_focused(1)
        focused_box.cut_line += dy
        if focused_box.cut_line < 0.0:
            focused_box.cut_line = 0.0
        if focused_box.cut_line > 1.0:
            focused_box.cut_line = 1.0
            
        self.changed.emit()

        
class PlanarWorldWidget(QWidget):
    def __init__(self):
        super(PlanarWorldWidget, self).__init__(None)
        self.ignore_events()
        # self.showMaximized()
        self.show()
        self.init_camera_and_qimage()

        self.planar_world = PlanarWorld()
        self.planar_world.changed.connect(self.redraw_and_update)

        # the optional index used by some commands
        self.the_index = 1
        
        self.init_modal_dispatcher()
        self.receive_events()

    def init_camera_and_qimage(self):
        print "Initializing camera and qimage"
        scale = min(float(self.frameSize().width()),
                    float(self.frameSize().height()))
        
        self.camera = Camera(id=1)
        self._cam_to_screen_zoom = scale / 2 / float(THE_BLACK_BOX.width())
        print "INIT_CAMERA_AND_QIMAGE", self.camera.changed, dir(self.camera.changed)
        self.camera.changed.connect(self.redraw_and_update)
        
        self.make_new_qimage(self.frameSize())

    def cam_to_screen(self, thing):
        if isinstance(thing, QPointF):
            return QPointF(float(self.the_qimage.width())/2,
                           float(self.the_qimage.height())/2) + thing * self._cam_to_screen_zoom
        if isinstance(thing, float):
            return thing * self._cam_to_screen_zoom
        if isinstance(thing, QRectF):
            return QRectF(self.cam_to_screen(thing.topLeft()),
                          QSizeF(self.cam_to_screen(thing.width()),
                                 self.cam_to_screen(thing.height())))
        raise Exception("Unknown type %s" % thing)

    def screen_to_cam(self, thing):
        if isinstance(thing, QPointF):
            return (thing - QPointF(float(self.the_qimage.width())/2,
                                    float(self.the_qimage.height())/2)) / self._cam_to_screen_zoom
        if isinstance(thing, float):
            return thing / self._cam_to_screen_zoom
        if isinstance(thing, QRectF):
            return QRectF(self.screen_to_cam(thing.topLeft()),
                          QSizeF(self.screen_to_cam(thing.width()),
                                 self.screen_to_cam(thing.height())))
        raise Exception("Unknown type %s" % thing)


    def init_modal_dispatcher(self):
        self.pre_modal_dispatcher = ModalDispatcher(
            self,
            { "main" : { "1" : [SelectIndex, 1],
                         "2" : [SelectIndex, 2],
                         "3" : [SelectIndex, 3],
                         "4" : [SelectIndex, 4],
                         "5" : [SelectIndex, 5],
                         "6" : [SelectIndex, 6],
                         "7" : [SelectIndex, 7],
                         "8" : [SelectIndex, 8],
                         "9" : [SelectIndex, 9],
                         "0" : [SelectIndex, 0] },
            })
        self.modal_dispatcher = ModalDispatcher(
            self,
            { "main" : { "a" : [ZoomCamera, "in"],
                         "z" : [ZoomCamera, "out"],
                         "i" : [MoveCamera, "up"],
                         "j" : [MoveCamera, "left"],
                         "k" : [MoveCamera, "down"],
                         "l" : [MoveCamera, "right"],
                         "q" : ["mode", "cursor_mode"],
                         "b" : ["mode", "box_mode"],
                         "control" : ["mode", "ctrl_mode"],
                         "f" : focus_box_at_point,
                         "u" : unfocus_everything },
              "ctrl_mode" : { "s" : save_everything,
                              "l" : load_everything },
              "cursor_mode" : { "options" : {"inherit" : True },
                                "i" : [MoveCursor, "up"],
                                "j" : [MoveCursor, "left"],
                                "k" : [MoveCursor, "down"],
                                "l" : [MoveCursor, "right"] },
              "box_mode" : { "c" : create_box,
                             "d" : ["mode", "box_destructive_mode"],
                             "a" : [ScaleSelectedBox, "enlarge"],
                             "z" : [ScaleSelectedBox, "shrink"],
                             "i" : [MoveSelectedBox, "up"],
                             "j" : [MoveSelectedBox, "left"],
                             "k" : [MoveSelectedBox, "down"],
                             "l" : [MoveSelectedBox, "right"] },
              "box_destructive_mode" : { "options" : { 'on_start' : self.planar_world.display_cutline,
                                                       'on_stop' : self.planar_world.hide_cutline },
                                         "r" : delete_selected_box,
                                         "i" : [MoveCutlineSelectedBox, "up"],
                                         "k" : [MoveCutlineSelectedBox, "down"],
                                         "c" : cut_selected_box,
                                         "g" : glue_selected_boxes,
                                         "h" : change_selected_box_color_to_next
                                     },
            })

    def expand_action_specs(self, *specs):
        def expand_one_spec(spec):
            if isinstance(spec, basestring):
                return [spec,
                        getattr(self, spec + "_starter"),
                        getattr(self, spec + "_stopper")]
            else:
                return spec
                        
        return map(expand_one_spec, specs)

    def receive_events(self):
        self.events_are_accepted = True
    def ignore_events(self):
        self.events_are_accepted = False

    def resizeEvent(self, event):
        if not self.events_are_accepted:
            print "Ignoring frame resize", self.frameSize()
            event.ignore()
            return None
        self._properResizeEvent(event)
        
    def _properResizeEvent(self, event):
        # self.resize_frame(event.oldSize(), event.size())
        self.make_new_qimage(event.size())
        self.redraw()

    def redraw(self):
        self.draw_a_dummy_world()
        self.draw_boxes()
        self.draw_focus()
        
    def redraw_and_update(self):
        # OK, for now just a simple redraw: we have white field with a black box in the middle
        self.redraw()
        self.update()

    def draw_a_dummy_world(self):
        self.the_qimage.fill(QtCore.Qt.white)
        p = QPainter()
        p.begin(self.the_qimage)
        transformed_rect = self.cam_to_screen(self.camera.abs_to_cam(THE_BLACK_BOX))
            
        # print "The black rect in window coords", transformed_rect, self.frame
        p.fillRect(transformed_rect, QtCore.Qt.black)
        p.end()

        
    def make_new_qimage(self, size):
        self.the_qimage = QImage(size, QImage.Format_ARGB32)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.the_qimage, 0, 0, 0, 0)

    def start(self):
        # self.showFullScreen()
        self.show()
        self.redraw_and_update()
    def stop(self):
        QtCore.QCoreApplication.instance().quit()

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == QtCore.Qt.Key_Escape:
            self.stop()
            return

        if self.pre_modal_dispatcher.press(event.key()):
            return
        if self.modal_dispatcher.press(event.key()):
            return

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

        if self.pre_modal_dispatcher.release(event.key()):
            return 

        if self.modal_dispatcher.release(event.key()):
            return 

    def draw_boxes(self):
        p = QPainter()
        p.begin(self.the_qimage)
        for box in self.planar_world.objects:
            rect = self.cam_to_screen(self.camera.abs_to_cam(box.rectf()))
            p.drawImage(rect,
                        box.image())
            p.drawRect(rect)
        p.end()
        
    def draw_focus(self):
        p = QPainter()
        p.begin(self.the_qimage)

        for i, focused_box in enumerate(self.planar_world._focus):
            if focused_box is None:
                continue
            self.draw_focus_rect(p, focused_box.rectf(), index=(i + 1)%10)

            # we only draw a cutline on a box in the first register
            if i == 0 and self.planar_world._display_cutline:
                self.draw_cutline(p, focused_box)
        p.end()

    def draw_focus_rect(self, painter, rectf, color=QtCore.Qt.yellow, index=0):
        rect = self.cam_to_screen(self.camera.abs_to_cam(rectf))
        painter.setPen(QtGui.QPen(color, FOCUS_LINE_WIDTH, QtCore.Qt.SolidLine))
        painter.drawRect(rect)
        
        painter.setPen(QtGui.QPen(QtCore.Qt.black, FOCUS_LINE_WIDTH, QtCore.Qt.SolidLine))
        painter.drawText(rect.bottomRight(), QString(str(index)))

    def draw_cutline(self, painter, box, color=QtCore.Qt.black):
        cut_line = box.cut_line
        rect = self.cam_to_screen(self.camera.abs_to_cam(box.rectf()))
        painter.setPen(QtGui.QPen(color, 2, QtCore.Qt.DashLine))
        painter.drawLine(rect.left(), (1.0 - cut_line) * rect.top() + cut_line * rect.bottom(),
                         rect.right(), (1.0 - cut_line) * rect.top() + cut_line * rect.bottom())

        
    def cursor_abs(self):
        pos = QCursor().pos()
        # print "CURSOR ABS:", self.frameSize(), self.the_qimage.rect(), pos
        return self.camera.cam_to_abs(self.screen_to_cam(QPointF(self.mapFromGlobal(pos))))
        
    def mysql_load_camera(self):
        new_camera = None
        with mysql_zooey_connection(ZOOEY_LOGIN, ZOOEY_PASSWD) as conn:
            new_camera = Camera.mysql_load(conn, 1)
        if new_camera is not None:
            self.camera.changed.disconnect(self.redraw_and_update)
            self.camera = new_camera
            self.camera.changed.connect(self.redraw_and_update)
            self.redraw_and_update()
        


        
