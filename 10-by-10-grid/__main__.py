
from PyQt4.QtGui import QApplication
from grid_world_widget import GridWorldWidget
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GridWorldWidget()
    ex.start()
    sys.exit(app.exec_())
