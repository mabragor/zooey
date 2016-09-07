### 2dworld_widget.py
### The simple 2d world, where colored boxes (and later, more complicated objects) would live.

from PyQt4 import (QtCore)
from PyQt4.QtGui import (QWidget, QImage, QPainter)
from PyQt4.QtCore import (QRectF)
import time

from linear_transform import linear_transform
from modal_dispatcher import ModalDispatcher

THE_BLACK_BOX = QRectF(-50, -50, 100, 100)
FRAME_START_RATIO = 1.0

MOVE_SPEED = 10

class PlanarWorldWidget(QWidget):
    def __init__(self):
        super(PlanarWorldWidget, self).__init__(None)
        self.ignore_events()
        # self.showMaximized()
        self.show()
        self.init_frame_and_qimage()
        self.init_modal_dispatcher()
        self.init_action_timer()
        self.receive_events()

    def init_frame_and_qimage(self):
        print "Initializing frame and qimage"
        width = float(self.frameSize().width()) * FRAME_START_RATIO
        height = float(self.frameSize().height()) * FRAME_START_RATIO
        self.frame = QRectF(- width / 2, - height / 2, width, height)
        print "In init frame", self.frame
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

        zoom = (1.0 + delta_zoom)
        center = self.frame.center()
        new_width = self.frame.width() / zoom
        new_height = self.frame.height() / zoom
        self.frame = QRectF(center.x() - new_width/2,
                            center.y() - new_height/2,
                            new_width,
                            new_height)
        print "Zoom to center", self.frame

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
        self.resize_frame(event.oldSize(), event.size())
        self.make_new_qimage(event.size())
        self.redraw()

    def resize_frame(self, old_size, size):
        print "Resizing frame", self.frameSize()
        center = self.frame.center()
        new_half_width = float(size.width())/old_size.width() * self.frame.width() / 2
        new_half_height = float(size.height())/old_size.height() * self.frame.height() / 2
        self.frame = QRectF(center.x() - new_half_width,
                            center.y() - new_half_height,
                            new_half_width * 2,
                            new_half_height * 2)

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
        transformed_rect = linear_transform(self.frame, QRectF(self.the_qimage.rect()))(THE_BLACK_BOX)
            
        print "The black rect in window coords", transformed_rect, self.frame
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
        ratio = self.frame.width() / self.the_qimage.width()
        self.frame.moveTo(self.frame.x() + (x or self.the_move_x) * ratio,
                          self.frame.y() + (y or self.the_move_y) * ratio)
        self.redraw_and_update()
