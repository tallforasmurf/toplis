'''
Try to make a main window containing a central widget that
retains a square aspect ratio.

According to many posts in forum.qt.io, what is supposed to work is to
   * setHeightForWidth(True) in the size policy
   * set a size policy of Preferred
   * implement hasHeightForWidth() returning True
   * implement heightForWidth(w) returning w
and do this either in the widget, or perhaps in the BoxLayout that
contains the widget. Or the parent widget, or somewhere.

This is bullshit, frankly. As will be clear in the code below, the
hasHeightForWidth and heightForWidth methods are either never called, or only
called during creation of the widget. They are CERTAINLY never called during
a resize -- regardless of size policy settings.

Another approach is to override the sizeHint() method and return a "hint"
that has the desired aspect ratio. Also bullshit. That method is also only
called when the widget is created, and at that time the widget's width bears
no relation to its preferred or minimum size. Never used during a resize.

What does work is the method shown rather far down in this SO post:
   https://stackoverflow.com/questions/8211982/qt-resizing-a-qlabel-containing-a-qpixmap-while-keeping-its-aspect-ratio
In essence, on any resize event, set the object's content margins so as
to compensate for a disparity between height and width.

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
        policy = QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        policy.setControlType(QSizePolicy.ToolButton)
        self.setSizePolicy(policy)
    def hasHeightForWidth(self):
        #print('RedSquare hHFW')
        # ONLY called when setContentsMargins() called never otherwise
        return True
    def heightForWidth(self, width):
        #print('RedSquare hFW {}'.format(width))
        # NEVER EVER called EVER
        return width
    #def sizeHint(self):
        # if implemented, only effect is to start at 640 instead of 100
        #width = self.width()
        #print('RedSquare sH {}'.format(width))
        #return QSize(width, self.heightForWidth(width))
    def paintEvent(self, event):
        shape = self.contentsRect()
        painter = QPainter(self)
        color = QColor('red')
        painter.fillRect(shape,color)
    def resizeEvent(self, event):
        # setContentsMargins(left,top,right,bottom)
        d = self.width()-self.height()
        if d : # is not zero,
            mod1 = abs(d)//2
            mod2 = abs(d)-mod1
            if d > 0 : # width is greater, reduce it
                self.setContentsMargins(mod1,0,mod2,0)
            else : # height is greater, reduce it
                self.setContentsMargins(0,mod1,0,mod2)
        super().resizeEvent(event)

class SquareLayout(QHBoxLayout):
    def __init__(self, parent):
        super().__init__(parent)
    def hasHeightForWidth(self):
        #print('SquareLayout hHFW')
        # called TWICE during setup, never again
        return True
    def heightForWidth(self, width):
        #print('SquareLayout hFW {}'.format(width))
        # called twice with argument of 40 (why?) never again
        return width

class CustomMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(QSize(100,100))
        policy = QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        layout = SquareLayout(self)
        layout.addWidget( RedSquare(None) )
        self.setLayout(layout)
    def hasHeightForWidth(self):
        print('MainWindow hHFW')
        # NEVER called
        return True
    def heightForWidth(self, width):
        print('MainWindow hFW {}'.format(width))
        # ONLY called if MainWindow sizeHint is implemented
        return width
    #def sizeHint(self):
        # only effect is a call with width 640 at startup
        #width = self.width()
        #print('MainWindow sH {}'.format(width))
        #return QSize(width, self.heightForWidth(width))


if __name__ == "__main__" :
    the_app = QApplication([])
    the_main = CustomMainWindow()
    the_main.show()
    the_app.exec_()
