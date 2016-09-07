### pdf_caching_renderer.py
### This simple class loads a PDF file and gives us QImages of pages, internally caching the results.

import popplerqt4
from __future__ import with_statement

PDF_BASE_RESOLUTION = 72.0

def progn():
    class Frob(object):
        def __enter__(self):
            return True
            
        def __exit__(self, type, value, traceback):
            return False

    return Frob()

class PDFCachingRenderer(object):
    def __init__(self, fname):
        self.load(fname)
        self.init_cache()
        self.init_master_rect_and_boundaries()
    
    def load(self, fname, index=0):
        self.doc = popplerqt4.Poppler.Document.load(fname)
        self.doc.setRenderHint(popplerqt4.Poppler.Document.Antialiasing
                               and popplerqt4.Poppler.Document.TextAntialiasing)

    def init_cache(self):
        self.cache = {}

    def __getitem__(self, num):
        it = self.cache.get(num, None)
        if it is not None:
            return it
        
        self.cache[num] = self.doc.page(index).renderToImage(PDF_BASE_RESOLUTION, PDF_BASE_RESOLUTION)
        return self.cache[num]

    def has_constant_width(self):
        width = None
        for i in xrange(self.doc.numPages()):
            if width is None:
                width = self.page(i).pageSize().width()
            else:
                if width != self.page(i).pageSize.width():
                    return False
        return True

    def init_master_rect_and_boundaries(self):
        self.boundaries = [0]
        width = None
        height = 0
        for i in xrange(self.doc.numPages()):
            if width is None:
                width = self.page(i).pageSize().width()
            height += self.page(i).pageSize().height()
            self.boundaries.append(height)
        self.master_rect = QRect(width, height)
    
        
            

