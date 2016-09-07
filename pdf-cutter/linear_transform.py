
from PyQt4.QtCore import QRectF, QPointF

def linear_transform(src, dst):
    zoom_x = float(dst.width())/src.width()
    zoom_y = float(dst.height())/src.height()

    def foo(thing):
        if isinstance(thing, QRectF):
            return QRectF(dst.x() + float(thing.x() - src.x()) * zoom_x,
                          dst.y() + float(thing.y() - src.y()) * zoom_y,
                          thing.width() * zoom_x,
                          thing.height() * zoom_y)
        else:
            return QPointF(dst.x() + float(thing.x() - src.x()) * zoom_x,
                           dst.y() + float(thing.y() - src.y()) * zoom_y)
        
    return foo
