'''
Try to make a main window containing a central widget that
retains a square aspect ratio.
'''
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QHBoxLayout,
    QSizePolicy,
    QWidget
    )
from PyQt5.QtGui import (
    QColor,
    QPainter
    )
from PyQt5.QtCore import ( QSize )


class RedSquare(QWidget):
    ''' square widget that paints itself red'''
    def __init__(self,parent):
        super().__init__(parent)
        policy = self.sizePolicy()
        policy.setHeightForWidth(True)
        policy.setControlType(QSizePolicy.ToolButton)
        self.setSizePolicy(policy)
    def hasHeightForWidth(self):
        print('RedSquare hHFW')
        return True
    def heightForWidth(self, width):
        print('RedSquare hFW {}'.format(width))
        return width
    def paintEvent(self, event):
        #print('RedSquare paint')
        shape = self.contentsRect()
        painter = QPainter(self)
        color = QColor('red')
        painter.fillRect(shape,color)

class SquareLayout(QHBoxLayout):
    def __init__(self, parent):
        super().__init__(parent)
    def hasHeightForWidth(self):
        print('SquareLayout hHFW')
        return True
    def heightForWidth(self, width):
        print('SquareLayout hFW {}'.format(width))
        return width

class CustomMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(QSize(100,100))
        policy = self.sizePolicy()
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        layout = SquareLayout(self)
        layout.addWidget( RedSquare(None) )
        self.setLayout(layout)
    def hasHeightForWidth(self):
        print('MainWindow hHFW')
        return True
    def heightForWidth(self, width):
        print('MainWindow hFW {}'.format(width))
        return width


if __name__ == "__main__" :
    the_app = QApplication([])
    the_main = CustomMainWindow()
    the_main.show()
    the_app.exec_()