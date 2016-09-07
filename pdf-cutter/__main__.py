
from PyQt4.QtGui import QApplication
from picture_with_holes_widget import PicturesWithHolesWidget
import sys

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = PicturesWithHolesWidget()
    # ex.load("/home/popolit/code/python-qt5-tutorial/sample-pdf.pdf")
    ex.start()
    sys.exit(app.exec_())

    
