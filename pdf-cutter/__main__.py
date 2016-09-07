
from PyQt4.QtGui import QApplication
# from picture_with_holes_widget import PicturesWithHolesWidget
from two_dee_world_widget import PlanarWorldWidget
import sys

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    # ex = PicturesWithHolesWidget()
    ex = PlanarWorldWidget()
    # ex.load("/home/popolit/code/python-qt5-tutorial/sample-pdf.pdf")
    ex.start()
    sys.exit(app.exec_())

    
