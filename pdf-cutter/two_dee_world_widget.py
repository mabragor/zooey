### 2dworld_widget.py
### The simple 2d world, where colored boxes (and later, more complicated objects) would live.

from PyQt4 import (QtCore)
from PyQt4.QtGui import (QWidget, QImage, QPainter)
from PyQt4.QtCore import (QRectF, QPointF, QSizeF)
import time

# from linear_transform import linear_transform
from modal_dispatcher import ModalDispatcher

THE_BLACK_BOX = QRectF(-50, -50, 100, 100)
FRAME_START_RATIO = 1.0

MOVE_SPEED = 10

class Camera(object):
    def __init__(self, x = 0.0, y = 0.0, distance = 1.0):
        self.x = x
        self.y = y
        # "absolute" sizes are distance * "camera" sizes -- the ones we see on screen
        self.distance = float(distance)

    def zoom(self, zoom):
        self.distance /= zoom

    def move(self, dx, dy):
        self.x += dx # * self.distance
        self.y += dy # * self.distance
        
    def to_screen(self, thing, screen_rect):
        if isinstance(thing, QPointF):
            return QPointF(self.x + (thing.x() - self.x)/self.distance + float(screen_rect.width())/2,
                           self.y + (thing.y() - self.y)/self.distance + float(screen_rect.height())/2)
        if isinstance(thing, float):
            return thing/self.distance
        if isinstance(thing, QRectF):
            return QRectF(self.to_screen(thing.topLeft(), screen_rect),
                          QSizeF(self.to_screen(thing.width(), screen_rect),
                                 self.to_screen(thing.height(), screen_rect)))
        raise Exception("Unknown type %s" % thing)
        
class PlanarWorldWidget(QWidget):
    def __init__(self):
        super(PlanarWorldWidget, self).__init__(None)
        self.ignore_events()
        # self.showMaximized()
        self.show()
        self.init_camera_and_qimage()
        
        self.init_modal_dispatcher()
        self.init_action_timer()
        self.receive_events()

    def init_camera_and_qimage(self):
        print "Initializing camera and qimage"
        scale = min(float(self.frameSize().width()),
                    float(self.frameSize().height()))
        self.camera = Camera(distance=float(THE_BLACK_BOX.width())/scale)
        self.make_new_qimage(self.frameSize())

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
                         "l" : ["move", "right"] },
              "actions" : self.expand_action_specs("zoom", "move")
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

    # def resize_frame(self, old_size, size):
    #     print "Resizing frame", self.frameSize()
    #     center = self.frame.center()
    #     new_half_width = float(size.width())/old_size.width() * self.frame.width() / 2
    #     new_half_height = float(size.height())/old_size.height() * self.frame.height() / 2
    #     self.frame = QRectF(center.x() - new_half_width,
    #                         center.y() - new_half_height,
    #                         new_half_width * 2,
    #                         new_half_height * 2)

    def redraw(self):
        self.draw_a_dummy_world()
        
    def redraw_and_update(self):
        # OK, for now just a simple redraw: we have white field with a black box in the middle
        self.redraw()
        self.update()

    def draw_a_dummy_world(self):
        self.the_qimage.fill(QtCore.Qt.white)
        p = QPainter()
        p.begin(self.the_qimage)
        transformed_rect = self.camera.to_screen(THE_BLACK_BOX,
                                                 self.the_qimage.rect())
            
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
        if event.key() == QtCore.Qt.Key_R:
            self.init_frame_and_qimage()
            self.redraw()
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
