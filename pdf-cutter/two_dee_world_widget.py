### 2dworld_widget.py
### The simple 2d world, where colored boxes (and later, more complicated objects) would live.

from PyQt4 import (QtCore, QtGui)
from PyQt4.QtGui import (QWidget, QImage, QPainter, QCursor)
from PyQt4.QtCore import (QRectF, QPointF, QSizeF, QSize)
import time
import random

# from linear_transform import linear_transform
from modal_dispatcher import (ModalDispatcher, DontWannaStart)

THE_BLACK_BOX = QRectF(-50, -50, 100, 100)
FRAME_START_RATIO = 1.0

MOVE_SPEED = 10

FOCUS_LINE_WIDTH = 5

NEW_BOX_ONSCREEN_SIZE = 50.0
BOX_ZOOM_DELTA = 0.01

class Camera(object):
    def __init__(self, x = 0.0, y = 0.0, distance = 1.0):
        self.x = x
        self.y = y
        # "absolute" sizes are distance * "camera" sizes -- the ones we see on screen
        self.d = float(distance)
        self.d0 = 1.0

    def zoom(self, zoom):
        self.d /= zoom

    def move(self, dx, dy):
        self.x += dx * self.d/self.d0
        self.y += dy * self.d/self.d0
        
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
        

COLORED_BOX_INIT_SIZE = 10

COLORS = ["white", "black", "red", "darkRed", "green", "darkGreen",
          "blue", "darkBlue", "cyan", "darkCyan", "magenta", "darkMagenta",
          "yellow", "darkYellow", "gray", "darkGray", "lightGray"]

class ColoredBox(object):
    def __init__(self, x=0, y=0, w=COLORED_BOX_INIT_SIZE, h=COLORED_BOX_INIT_SIZE, color=None):
        self.x = float(x) # x and y are coordinates of the CENTER of the box (center of mass if you will)
        self.y = float(y)
        self.w = float(w)
        self.h = float(h)
        if color is None:
            self._color = random.randint(0, len(COLORS) - 1)
        else:
            self._color = color

        self._image = None
        self._cache_valid = False

    def color(self):
        return getattr(QtCore.Qt, COLORS[self._color])
        
    def copy(self):
        return ColoredBox(x=self.x, y=self.y, w=self.w, h=self.h, color=self._color)
            
    def intersects(self, other_box):
        return ((abs(self.x - other_box.x) < (self.w + other_box.w)/2)
                and (abs(self.y - other_box.y) < (self.h + other_box.h)/2))

    def contains_point(self, x, y):
        return (abs(self.x - x) < self.w/2
                and abs(self.y - y) < self.h/2)
    
    def zoom(self, zoom):
        self.w *= zoom
        self.h *= zoom
        self._cache_valid = False
        return self

    def image(self):
        if (not self._cache_valid) or (self._image is None):
            self._cache_valid = True
            self._image = QImage(QSize(self.w, self.h), QImage.Format_ARGB32)
            self.draw()
        return self._image

    def draw(self):
        self._image.fill(self.color())
    
    def nd_zoom(self, zoom):
        '''ND stands for non-destructive -- creates a copy, and zooms it'''
        return self.copy().zoom(zoom)

    def rectf(self):
        return QRectF(self.x - self.w/2, self.y - self.h/2, self.w, self.h)
    
class PlanarWorld(object):
    '''The backend of the planar world
    It knows about objects in it, it can move them around, create and so on.'''
    def __init__(self):
        self.objects = []
        self._focus = None

    def intersects_with_something(self, box, except_box=None):
        '''True if we intersect with anything except ourself and some 'exceptional' box'''
        for other in self.objects:
            if ((not box == other)
                and (not except_box == other)
                and box.intersects(other)):
                # print "INTERSECTS WITH SOMETHING:", box, except_box, other
                return True
        return False
        
    def try_create_new_box(self, x, y, size):
        new_box = ColoredBox(x = x, y = y, w=size, h=size)
        if self.intersects_with_something(new_box):
            return None
        self.objects.append(new_box)
        return new_box

    def find_box_at_point(self, x, y):
        for box in self.objects:
            if box.contains_point(x, y):
                return box
        return None

    def focus(self, box):
        self._focus = box
    def unfocus(self):
        self._focus = None
        
    def try_zoom_box(self, box, zoom):
        print "TRY ZOOM BOX: we enter"
        if not self.intersects_with_something(box.nd_zoom(zoom), box):
            # after we've checked non-destructively everything is OK, we do destructively in-place
            print "TRY ZOOM BOX: we do not intersect with anything"
            return box.zoom(zoom)
        print "TRY ZOOM BOX: we intersect with something"
        # Otherwise we don't change anything
        return None
    
class PlanarWorldWidget(QWidget):
    def __init__(self):
        super(PlanarWorldWidget, self).__init__(None)
        self.ignore_events()
        # self.showMaximized()
        self.show()
        self.init_camera_and_qimage()

        self.planar_world = PlanarWorld()
        
        self.init_modal_dispatcher()
        self.init_action_timer()
        self.receive_events()

    def init_camera_and_qimage(self):
        print "Initializing camera and qimage"
        scale = min(float(self.frameSize().width()),
                    float(self.frameSize().height()))
        self.camera = Camera()
        self._cam_to_screen_zoom = scale / 2 / float(THE_BLACK_BOX.width())
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


    def init_action_timer(self):
        self.action_timer = QtCore.QTimer()
        self.action_timer.setInterval(10)

    def init_modal_dispatcher(self):
        self.modal_dispatcher = ModalDispatcher(
            { "main" : { "a" : ["zoom", "in"],
                         "z" : ["zoom", "out"],
                         "i" : ["move", "up"],
                         "j" : ["move", "left"],
                         "k" : ["move", "down"],
                         "l" : ["move", "right"],
                         "q" : ["mode", "cursor_mode"],
                         "b" : ["mode", "box_mode"],
                         "f" : "focus_box_at_point",
                         "u" : "unfocus" },
              "cursor_mode" : { "options" : ["inherit"],
                                "i" : ["move_cursor", "up"],
                                "j" : ["move_cursor", "left"],
                                "k" : ["move_cursor", "down"],
                                "l" : ["move_cursor", "right"] },
              "box_mode" : { "c" : "create_box",
                             "d" : ["mode", "box_destructive_mode"],
                             "a" : ["scale_selected_box", "enlarge"],
                             "z" : ["scale_selected_box", "shrink"] },
              "box_destructive_mode" : { "r" : "delete_selected_box" },
              "actions" : self.expand_action_specs("zoom", "move", "move_cursor",
                                                   "create_box", "focus_box_at_point",
                                                   "unfocus", "scale_selected_box",
                                                   "delete_selected_box")
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

    def zoom_starter(self, direction):
        if direction == 'in':
            self.the_zoom_delta = 0.01
        elif direction == 'out':
            self.the_zoom_delta = -0.01
        else:
            raise Exception("Bad zoom direction" + str(direction))
            
        self.action_timer.timeout.connect(self.zoom_to_center)
        self.action_timer.start()

    def zoom_stopper(self, direction):
        self.action_timer.timeout.disconnect(self.zoom_to_center)
        self.action_timer.stop()

    def zoom_to_center(self, delta_zoom=None):
        if not delta_zoom:
            delta_zoom = self.the_zoom_delta

        self.camera.zoom(1.0 + delta_zoom)
        self.redraw_and_update()

    def create_box_starter(self):
        abs_pos = self.cursor_abs()
        abs_size = self.camera.cam_to_abs(self.screen_to_cam(NEW_BOX_ONSCREEN_SIZE))
        box = self.planar_world.try_create_new_box(abs_pos.x(), abs_pos.y(), abs_size)
                                                   
        if box:
            self.planar_world.focus(box)
            # we only redraw if we've successfully created the box
            self.redraw_and_update()

    def create_box_stopper(self):
        pass
        
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

        self.modal_dispatcher.press(event.key())

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

        self.modal_dispatcher.release(event.key())

    def move_starter(self, direction):
        direction_map = { 'left' : (-MOVE_SPEED, 0),
                          'right' : (MOVE_SPEED, 0),
                          'up' : (0, -MOVE_SPEED),
                          'down' : (0, MOVE_SPEED) }
        (self.the_move_x, self.the_move_y) = direction_map[direction]
        self.action_timer.timeout.connect(self.move)
        self.action_timer.start()
    
    def move_stopper(self, direction):
        self.action_timer.timeout.disconnect(self.move)
        self.action_timer.stop()
        
    def move(self, x=None, y=None):
        self.camera.move((x or self.the_move_x),
                         (y or self.the_move_y))
        self.redraw_and_update()

    def move_cursor_starter(self, direction):
        direction_map = { 'left' : (-MOVE_SPEED, 0),
                          'right' : (MOVE_SPEED, 0),
                          'up' : (0, -MOVE_SPEED),
                          'down' : (0, MOVE_SPEED) }
        (self.the_move_x, self.the_move_y) = direction_map[direction]
        self.action_timer.timeout.connect(self.move_cursor)
        self.action_timer.start()
    
    def move_cursor_stopper(self, direction):
        self.action_timer.timeout.disconnect(self.move_cursor)
        self.action_timer.stop()

    def move_cursor(self, x=None, y=None):
        print "I'm moving cursor!"
        pos = QCursor().pos()
        QCursor().setPos(pos.x() + (x or self.the_move_x),
                         pos.y() + (y or self.the_move_y))
    
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
        if not self.planar_world._focus:
            return
        p = QPainter()
        p.begin(self.the_qimage)
        rect = self.cam_to_screen(self.camera.abs_to_cam(self.planar_world._focus.rectf()))
        pen = QtGui.QPen(QtCore.Qt.yellow, FOCUS_LINE_WIDTH, QtCore.Qt.SolidLine)
        p.setPen(pen)
        p.drawRect(rect)
        p.end()

    def cursor_abs(self):
        pos = QCursor().pos()
        # print "CURSOR ABS:", self.frameSize(), self.the_qimage.rect(), pos
        return self.camera.cam_to_abs(self.screen_to_cam(QPointF(self.mapFromGlobal(pos))))
        
    def focus_box_at_point_starter(self):
        abs_pos = self.cursor_abs()
        box = self.planar_world.find_box_at_point(abs_pos.x(), abs_pos.y())
                                                   
        if box:
            self.planar_world.focus(box)
            self.redraw_and_update()

    def focus_box_at_point_stopper(self):
        pass

    def unfocus_starter(self):
        if self.planar_world._focus:
            self.planar_world._focus = None
            self.redraw_and_update()

    def unfocus_stopper(self):
        pass

    def scale_selected_box_starter(self, direction):
        if not self.planar_world._focus:
            raise DontWannaStart
        
        if direction == 'enlarge':
            self.the_zoom_delta = BOX_ZOOM_DELTA
        elif direction == 'shrink':
            self.the_zoom_delta = -BOX_ZOOM_DELTA
        else:
            raise Exception("Bad zoom direction" + str(direction))
            
        self.action_timer.timeout.connect(self.scale_selected_box)
        self.action_timer.start()

    def scale_selected_box_stopper(self, direction):
        self.action_timer.timeout.disconnect(self.scale_selected_box)
        self.action_timer.stop()

    def scale_selected_box(self):
        delta_zoom = self.the_zoom_delta

        if self.planar_world.try_zoom_box(self.planar_world._focus, 1.0 + self.the_zoom_delta):
            self.redraw_and_update()

    def delete_selected_box_starter(self):
        if not self.planar_world._focus:
            raise DontWannaStart

        self.planar_world.objects.remove(self.planar_world._focus)
        self.planar_world.unfocus()
        self.redraw_and_update()

    def delete_selected_box_stopper(self):
        pass
