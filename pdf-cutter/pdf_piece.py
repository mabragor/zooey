### pdf_piece.py
### A piece of PDF that's been cut out


class PDFPiece(object):
    def __init__(self, fname,
                 start_page, start_ratio,
                 stop_page, stop_ratio):
        self.fname = fname
        self.start_page = start_page
        self.start_ratio = start_ratio
        self.stop_page = stop_page
        self.stop_ratio = stop_ratio


class PDFVisiblePiece(object):
    def __init__(self,
                 pdf_storage=None,
                 fname=None,
                 start_page=None, start_ratio=None,
                 stop_page=None, stop_ratio=None):
        self.pdf_renderer = pdf_storage[fname]
        self.piece = PDFPiece(fname, start_page, start_ratio, stop_page, stop_ratio)
        self.frame = QRect(0,0,0,0)
        self.init_slave_rect()

    def init_slave_rect(self):
        y_start = (self.pdf_renderer.boundaries[self.piece.start_page] * (1 - self.piece.start_ratio)
                   + self.pdf_renderer.boundaries[self.piece.start_page + 1] * self.piece.start_ratio)
        y_stop = (self.pdf_renderer.boundaries[self.piece.stop_page] * (1 - self.piece.stop_ratio)
                   + self.pdf_renderer.boundaries[self.piece.stop_page + 1] * self.piece.stop_ratio)
        self.slave_rect = QRect(0, y_start,
                                self.pdf_renderer.master_rect.width(),
                                y_stop - y_start)

    def move_by(self, dx, dy):
        test_rect = self.frame.copy()
        test_rect.moveTo(test_rect.x() + dx,
                         test_rect.y() + dy)
        if self.slave_rect.contains(test_rect):
            self.frame = test_rect
            return True
        return False

    def move_top_by(self, dy):
        test_rect = self.frame.copy()
        test_rect.setTop(test_rect.top() + dy)
        if self.slave_rect.contains(test_rect):
            self.frame = test_rect
            return True
        return False

    def move_bottom_by(self, dy):
        test_rect = self.frame.copy()
        test_rect.setBottom(test_rect.bottom() + dy)
        if self.slave_rect.contains(test_rect):
            self.frame = test_rect
            return True
        return False

    def move_left_by(self, dx):
        test_rect = self.frame.copy()
        test_rect.setLeft(test_rect.left() + dx)
        if self.slave_rect.contains(test_rect):
            self.frame = test_rect
            return True
        return False

    def move_right_by(self, dx):
        test_rect = self.frame.copy()
        test_rect.setLeft(test_rect.right() + dx)
        if self.slave_rect.contains(test_rect):
            self.frame = test_rect
            return True
        return False

                 
                 
