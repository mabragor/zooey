### picture_with_holes_widget.py
### The frontend of "pictures with holes"

from PyQt4 import QtCore
from PyQt4.QtGui import (QWidget, QPalette, QPainter, QCursor)

import time

import hashlib

from modal_dispatcher import ModalDispatcher
from random_sketches import random_sketches_fname

MOVE_SPEED = 10

def md5sum(string):
    return int(hashlib.md5().update(my_string).hexdigest(), 16)

class DontWannaStart(Exception):
    pass

from picture_with_holes import Hole, PictureWithHoles

class PicturesWithHolesWidget(QWidget):
    def __init__(self):
        super(PicturesWithHolesWidget, self).__init__(None)

        self.loadFirstPDF()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Scroll PDFs and reveal random ones')

        p = QPalette()
        p.setColor(QPalette.Background, QtCore.Qt.black);
        self.setPalette(p)

        self.showMaximized()
        self.show()

        self.init_modal_dispatcher()
        self.init_action_timer()

    def init_modal_dispatcher(self):
        self.modal_dispatcher = ModalDispatcher(
            { "main" : { "a" : ["zoom", "in"],
                         "z" : ["zoom", "out"],
                         "i" : ["move", "up"],
                         "j" : ["move", "left"],
                         "k" : ["move", "down"],
                         "l" : ["move", "right"],
                         "shift" : ["mode", "shift"],
                         "e" : ["mode", "volder_edit"] },
              "shift" : { "options" : ["inherit"],
                          "i" : ["move_cursor", "up"],
                          "j" : ["move_cursor", "left"],
                          "k" : ["move_cursor", "down"],
                          "l" : ["move_cursor", "right"] },
              "volder_edit" : { "a" : ["zoom_volder_at_point", "enlarge"],
                                "z" : ["zoom_volder_at_point", "shrink"] },
                                # "i" : ["move_volder_at_point", "up"],
                                # "j" : ["move_volder_at_point", "left"],
                                # "k" : ["move_volder_at_point", "down"],
                                # "l" : ["move_volder_at_point", "right"] },
              "actions" : self.expand_action_specs("zoom", "move",
                                                   "move_cursor",
                                                   # "move_volder_at_point",
                                                   "zoom_volder_at_point")
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
        
    def make_curry(self, method):
        def frob(*args, **kwds):
            return method(self, *args, **kwds)
        return frob
        
    def init_action_timer(self):
        self.action_timer = QtCore.QTimer()
        self.action_timer.setInterval(10)

    def num_active_pics(self):
        return self.pics.recursive_active_pics()

    def loadFirstPDF(self):
        self.showMaximized()
        self.hide()
        self.pics = Hole(None, pic=PictureWithHoles(random_sketches_fname()))
        
        self.init_pdf_image_geometry()

        self.pics.recursive_sync()
        ## print self.pics.part, self.pics.dest, self.width(), self.height()
        self.redraw()
        
    def init_pdf_image_geometry(self):
        my_height = self.height()
        my_width = self.width()

        ratio = max(float(self.pics.pic.image.width())/my_width,
                    float(self.pics.pic.image.height())/my_height)

        self.the_qimage = self.pics.pic.get_ratioed_qimage(ratio)
        self.pics.init_geometry_from_qimage(self.the_qimage)
        
        self.pics.croak()
        
    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == QtCore.Qt.Key_Escape:
            self.stop()
            return

        self.modal_dispatcher.press(event.key())
        
    def zoom_starter(self, direction):
        if direction == 'in':
            self.the_zoom_delta = 0.1
        elif direction == 'out':
            self.the_zoom_delta = -0.1
        else:
            raise Exception("Bad zoom direction" + str(direction))
            
        self.action_timer.timeout.connect(self.zoom_to_cursor)
        self.action_timer.start()

    def zoom_stopper(self, direction):
        self.action_timer.timeout.disconnect(self.zoom_to_cursor)
        self.action_timer.stop()

    def find_volder_at_point(self):
        (x_m, y_m) = self.cursor_relative_position()
        self.the_volder_at_point = self.pics.find_volder_at_point(QPointF(x_m, y_m))
        if self.the_volder_at_point is not None:
            return True
        return False
        
    def zoom_volder_at_point_starter(self, direction):
        if not self.find_volder_at_point():
            raise DontWannaStart
        
        if direction == 'enlarge':
            self.the_zoom_delta = 0.1
        elif direction == 'shrink':
            self.the_zoom_delta = -0.1
        else:
            raise Exception("Bad zoom direction" + str(direction))
            
        self.action_timer.timeout.connect(self.zoom_volder_at_point)
        self.action_timer.start()

    def zoom_volder_at_point_stopper(self, direction):
        self.action_timer.timeout.disconnect(self.zoom_volder_at_point)
        self.action_timer.stop()
        
    def move_starter(self, direction):
        direction_map = { 'left' : (MOVE_SPEED, 0),
                          'right' : (-MOVE_SPEED, 0),
                          'up' : (0, MOVE_SPEED),
                          'down' : (0, -MOVE_SPEED) }
        (self.the_move_x, self.the_move_y) = direction_map[direction]
        self.action_timer.timeout.connect(self.move)
        self.action_timer.start()
    
    def move_stopper(self, direction):
        self.action_timer.timeout.disconnect(self.move)
        self.action_timer.stop()

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
            
    def move(self, x=None, y=None):
        print "I'm moving"
        self.pics.move(x or self.the_move_x,
                       y or self.the_move_y)
        self.sync_and_redraw()

    def move_cursor(self, x=None, y=None):
        print "I'm moving cursor!"
        pos = QCursor().pos()
        QCursor().setPos(pos.x() + (x or self.the_move_x),
                         pos.y() + (y or self.the_move_y))
            
    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

        self.modal_dispatcher.release(event.key())
            
    def wheelEvent(self, event):
        self.zoom_to_cursor(0.1 * float(event.delta())/8/15/20)

    def cursor_relative_position(self):
        pos = QCursor().pos()
        x_image = float(self.width() - self.the_qimage.width())/2
        y_image = float(self.height() - self.the_qimage.height())/2
        return (pos.x() - x_image, pos.y() - y_image)
        
    def zoom_to_cursor(self, delta_zoom=None):
        if not delta_zoom:
            delta_zoom = self.the_zoom_delta

        (x_m, y_m) = self.cursor_relative_position()
        zoom = (1.0 + delta_zoom)
        ## print "Zoom:", zoom

        self.pics.rescale(x_m, y_m, zoom=zoom)
        self.sync_and_redraw()

    def zoom_volder_at_point(self, delta_zoom=None):
        if not delta_zoom:
            delta_zoom = self.the_zoom_delta

        self.the_volder_at_point.central_rescale(1.0 + delta_zoom)

        self.sync_and_redraw()
        
    def sync_and_redraw(self):
        self.pics.recursive_sync()
        
        if not self.pics.takes_whole_frame():
            print "Creating new top pic"
            self.pics = self.pics.glue_on_top(PictureWithHoles(random_sketches_fname()))

        dominant_index = self.pics.some_last_hole_takes_whole_frame()
        if dominant_index is not None: # self.pics.hole_takes_whole_qimage():
            print "Switching to the child pic"
            self.pics = self.pics.switch_to_child_pic(dominant_index)

        self.redraw()

    def redraw(self):
        self.refresh_the_qimage()
        self.pics.recursive_draw(self.the_qimage)
        self.update()

    def refresh_the_qimage(self, color=QtCore.Qt.white):
        self.the_qimage.fill(color)

    def resizeEvent(self, event):
        self.redraw()
        
    def paintEvent(self, event):
        x = (self.frameSize().width() - self.the_qimage.width())/2
        y = (self.frameSize().height() - self.the_qimage.height())/2

        painter = QPainter(self)
        painter.drawImage(x, y, self.the_qimage, 0, 0, 0, 0)

    def start(self):
        self.showFullScreen()
        self.show()
        
    def stop(self):
        QtCore.QCoreApplication.instance().quit()

