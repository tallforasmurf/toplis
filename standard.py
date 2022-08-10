'''
        Basic Tetris

This is a Tetris game implemented using PyQt6.

It is basically a line-by-line rewrite of Jan Bodnar's "Tetris in PyQt"
tutorial found at: http://zetcode.com/gui/pyqt5/tetris/

The game is made to conform to the Tetris Guideline for play as described at
http://tetris.wikia.com/wiki/Random_Generator

In particular it uses the standard colors and a "7-bag randomizer".

'''


from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow
    )
from PyQt6.QtCore import (
    Qt,
    QBasicTimer,
    QEvent,
    pyqtSignal
    )
from PyQt6.QtGui import (
    QColor,
    QPainter
    )
import typing
import random
import enum

'''
    Defining the standard Tetronimo shapes and colors.

Name the seven Tetronimoes via an IntEnum. 'O', 'I', 'T' and so forth are the
standarized names for the shapes.

The 'N' Tetronimo is the non-shape that appears in any empty cell of the
board. Only one 'N' is ever instantiated, as the global NO_T_mo.
'''

class T_ShapeNames(enum.IntEnum):
    N = 0 # the non-shape in an empty cell
    O = 1 # square
    I = 2 # line of 4
    T = 3
    L = 4
    J = 5
    S = 6
    Z = 7

'''

Assigning standardized colors for the Tetronimoes, as specified in the Tetris
guidelines.

The color names are given as strings, chosen from the list of available
predefined colors that is returned by QColor.colorNames(). (FYI: there are
148 names in that list, alphabetically from "aliceblue" to "yellowgreen".)

The special color defined for the 'N' tetronimo is the color of an empty
board cell.

'''

T_Colors = {
    T_ShapeNames.N : QColor(204,204,204,32),
    T_ShapeNames.O : QColor('yellow'),
    T_ShapeNames.I : QColor('cyan'),
    T_ShapeNames.T : QColor('purple'),
    T_ShapeNames.L : QColor('orange'),
    T_ShapeNames.J : QColor('blue'),
    T_ShapeNames.S : QColor('green'),
    T_ShapeNames.Z : QColor('red')
    }
'''
Assigning each Tetronimoe its shape and initial orientation.

Per the guidelines, quote,
    "The playfield is ... 10 by 20 ..."
    "The tetriminoes spawn horizontally with J, L and T spawning flat-side first."
    "The I and O spawn in the middle columns
     The rest spawn in the left-middle columns"

As I interpret that, if the columns are numbered 0-9, the O spawns in columns
4, 5, and the I in columns 3, 4, 5, 6. The others (which are all 3 squares
wide when horizontal) spawn in columns 3, 4, 5.

As designed by Jan Bodnar, each Tetronimo is described by a list of four
(x,y) tuples that specify four cells centered in an x-y coordinate plane. The
initial values specify the initial (spawn) rotation of a Tetronimo, where
(x=0,y=0) corresponds to column 4 row 20.

For example the Z is:
                (-1,1)(0,1)
                      (0,0) (1,0)
while the L is:
                            (1,1)
                (-1,0)(0,0) (1,0)

This design has the very nice property that rotation is easy. (Bodnar does
not explain this in his tutorial; one must infer it from the code.)

To rotate a shape left, replace the tuples of the original shape with
the tuple comprehension,

    ( (-y,x) for (x,y) in original_shape )

To rotate a shape right, use ( (y,-x) for (x,y) in original_shape )

For example if L is ((1,1), (-1,0),(0,0),(1,0))
L rotated left is   ((-1,1),(0,-1),(0,0),(0,1))
L rotated right is  ((1,-1),(0,-1),(0,0),(0,1))

'''

T_Shapes = {
    T_ShapeNames.N : ((0,0),(0,0),(0,0),(0,0)),
    T_ShapeNames.O : ((0,1),(1,1),(0,0),(1,0)),
    T_ShapeNames.I : ((-2,0),(-1,0),(0,0),(1,0)),
    T_ShapeNames.T : ((0,1),(-1,0),(0,0),(1,0)),
    T_ShapeNames.L : ((1,1),(-1,0),(0,0),(1,0)),
    T_ShapeNames.J : ((-1,1),(-1,0),(0,0),(1,0)),
    T_ShapeNames.S : ((-1,0),(0,0),(0,1),(1,1)),
    T_ShapeNames.Z : ((-1,1),(0,1),(0,0),(1,0))
    }

'''
Create a "bag" of seven Tetronimo names in random order. The bag will be
consumed before another is requested. This prevents the frustrations of a
naive randomizer (like in Bodnar's tutorial) where you can easily get four or
five I- or Z-tetronimoes close together then go without them for 50 turns.
'''

def make_bag() -> typing.List[T_ShapeNames] :
    bag = [ T_ShapeNames(v) for v in range(1,8) ]
    random.shuffle(bag)
    return bag

'''
Define the class of Tetronimo game pieces, T_mo. (Bodnar calls this class
Shape.)

A game piece knows its shape name and color, and its shape in terms of a
tuple of the four (x,y) values of each of its cells, as defined in T_Shapes
above.

When drawing the active T_mo, the Board adds the actual row and column index
to the relative values of the T_mo shape.

A T_mo can rotate, but note that the rotate_left() and rotate_right() methods
do NOT modify shape of the called T_mo. They return a NEW T_mo intended to
replace this one. This is done so that the Board can test a rotation. If the
new, rotated T_mo is legal, it replaces the old; but if it is not permitted,
the original T_mo is left unchanged.

'''

class T_mo(object):
    def __init__(self, t_name: T_ShapeNames) :
        self.t_name = t_name
        self.t_color = T_Colors[t_name]
        self.coords = tuple( ((x,y) for (x,y) in T_Shapes[t_name]) )

    def color(self) -> QColor :
        return self.t_color

    '''
    Return the x and y values of one of the four cells of this T_mo
    '''
    def x(self, cell:int ) -> int :
        return self.coords[cell][0]
    def y(self, cell:int ) -> int :
        return self.coords[cell][1]

    '''
    Return the minimum and maximum x and y values of this T_mo. These are
    used to compute collisions.
    '''
    def x_max(self) -> int :
        return max( (x for (x,y) in self.coords) )
    def x_min(self) -> int :
        return min( (x for (x,y) in self.coords) )
    def y_max(self) -> int :
        return max( (y for (x,y) in self.coords) )
    def y_min(self) -> int :
        return min( (y for (x,y) in self.coords) )

    '''
    Return a new T_mo with its shape rotated either left or right. Note that
    we cannot type-declare these methods as "-> T_mo", because when these
    lines are executed, the name T_mo has not been defined yet! Little flaw
    in the Python typing system.
    '''
    def rotateLeft(self) :
        new_tmo = T_mo( self.t_name )
        new_tmo.coords = tuple( ((-y,x) for (x,y) in self.coords ) )
        return new_tmo
    def rotateRight(self) :
        new_tmo = T_mo( self.t_name )
        new_tmo.coords = tuple( ( (y,-x) for (x,y) in self.coords ) )
        return new_tmo

'''
This global instance of T_mo is the only one of type N. It is
referenced from any unoccupied board cell.
'''

NO_T_mo = T_mo( T_ShapeNames.N )

'''
Define the game board. This is where the game is implemented.

The board object is set as the central widget of the main window. It takes
"strong" focus so it will receive all keystroke events.

It defines a string-valued Qsignal that is connected to the main window's
status line. At various times it emits a signal that updates the status line.

The board is logically an array of square cells, Board.Columns wide and
Board.Rows high. The relationship between cells and pixels is set in the
paintEvent() and drawSquare() methods.

The logical board is implemented as a list of length Rows*Columns. Each item
in the list is a reference to a T_mo object.

Initially the board is full of NO_T_mo, representing empty cells. Only when
the current T_mo, the one the user is controlling with keys, comes to rest
and cannot move any further, is it copied into the four board cells where it
stopped, so that resting location takes on the color of that T_mo.

While it is moving, the current T_mo is not "in" the board cell list. To draw
the board, we draw the fixed contents (finalized cells and empty cells), then
draw the current T_mo over the top of it. (This saves having to erase the
active T_mo before redrawing it when it moves or rotates.)

The board creates a QBasicTimer with the timer interval Board.StartingSpeed
(milliseconds). Each time the interval expires, the timer creates a
timerEvent that is used to drop the current T_mo. The timer is stopped during
a pause and restarted.

'''
class Board(QFrame):

    '''
    Define a Qt signal with a string value. The main window will
    connect this signal to the ShowMessage method of the status bar.
    '''
    NewStatus = pyqtSignal(str)

    '''
    Define the dimensions of the board in cells.
    '''
    Columns = 10
    Rows = 22

    '''
    Initial millisecond delay value for the game timer.
    '''
    StartingSpeed = 500

    def __init__(self, parent):
        super().__init__(parent)
        '''
        Set Qt properties of this widget.
        TODO: constrain dimensions so cells stay square on stretch
        '''
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        '''
        Create the timer that sets the pace of the game.
        '''
        self.timer = QBasicTimer()
        '''
        Create the flag that is set True after clearing any complete lines,
        so that the next piece is not created until the timer expires.
        '''
        self.waitForNextTimer = False
        '''
        Create state flags. self.start() is called by the main window.
        isPaused flag is toggled in self.pause() by a P keystroke.
        '''
        self.isStarted = False
        self.isPaused = False
        '''
        Create a list of accepted keys, for quick reference during a
        keyPressEvent.
        '''
        self.validKeys = [ Qt.Key.Key_Left, Qt.Key.Key_Right,
                           Qt.Key.Key_D, Qt.Key.Key_Down, Qt.Key.Key_Up,
                           Qt.Key.Key_Space, Qt.Key.Key_P ]
        '''
        Create a reference to the active T_mo and the index of its center cell.
        '''
        self.curPiece = NO_T_mo
        self.curX = 0
        self.curY = 0
        '''
        Initialize the count of completed lines.
        '''
        self.completedLines = 0
        '''
        Create the "board" where all cells are documented. It will be
        initialized when self.start() is called.
        '''
        self.board = [] # type: List[T_mo]
        '''
        Create the "bag" holder, where we keep the bag of up to 7
        pieces to be generated. When it is empty, self.newPiece
        refills it.
        '''
        self.bag = [] # type List[T_ShapeNames]

    def start(self):
        '''
        Called from the parent widget to begin a new game.
        '''
        self.isStarted = True
        self.waitForNextTimer = False
        self.completedLines = 0
        self.clearBoard()
        self.NewStatus.emit(str(self.completedLines))
        self.timer.start(Board.StartingSpeed, self)
        self.newPiece()

    def clearBoard(self):
        '''
        Clear the board to empty. An empty cell is one that contains a
        reference to NO_T_mo.
        '''
        self.board = [NO_T_mo] * (Board.Rows * Board.Columns)

    def newPiece(self):
        '''
        Get a new T_mo from the current bag, refilling the bag if
        necessary. Try to place the new piece on the board. Normally
        that works, but if the board is full, this is where we find
        out the game is over.
        '''
        if 0 == len(self.bag) :
            self.bag = make_bag()
        self.curPiece = T_mo( self.bag.pop() )

        self.curX = Board.Columns // 2 + 1
        self.curY = Board.Rows - 2 + self.curPiece.y_min()

        if not self.tryMove(self.curPiece, self.curX, self.curY):
            '''
            The game is over. Clear the current piece so update will not
            attempt to display it. Turn off the isStarted flag, potentially a
            new game could be started now (not implemented in this version).
            Stop the timer.
            '''
            self.curPiece = NO_T_mo
            self.isStarted = False
            self.timer.stop()
            '''
            Update the status with the final result and cause a repaint.
            '''
            self.NewStatus.emit(
                "Game over, {} lines".format(self.completedLines)
                )
            self.update()

    def tryMove(self, newPiece, newX, newY) ->bool :
        '''
        Try to place the active tetronimo in a new position. This method is
        called when a new piece is first created, and when the active piece
        is rotated or translated.

        If there exists another tetronimo already in a cell that the new
        position would occupy, the change is not allowed and we return false.
        It is up to the caller what to do then.

        If the changed tetronimo covers only empty cells, the move is
        completed by saving the proposed coordinates, and by assigning the
        piece to curPiece. In the case of a translation (left, right or down)
        the newPiece is already the curPiece. In the case of a rotation, the
        newPiece is a rotated version and replaces the curPiece.

        After accepting a change we call the inherited QWidget.update() method
        which schedules a paint event, resulting in a call to paintEvent().
        '''
        for i in range(4):

            x = newX + newPiece.x(i)
            y = newY + newPiece.y(i)
            if x < 0 or x >= Board.Columns:
                return False
            if y < 0 or y >= Board.Rows:
                return False

            if self.shapeAt(x, y) is not NO_T_mo:
                return False

        self.curPiece = newPiece
        self.curX = newX
        self.curY = newY
        self.update()

        return True

    def keyPressEvent(self, event:QEvent):
        '''
        Process a key press. Any key press (not release) while the
        focus is in the board comes here. The key code is event.key()
        and the names of keys are defined in the Qt namespace, see
        http://doc.qt.io/qt-5/qt.html#Key-enum

        If we can handle the event we do; else pass it to our parent.

        Note that in left, right and rotate keys, we could look at the return
        from tryMove() and if it is False, we could maybe implement the "wall
        kick" feature.
        '''

        if self.isStarted and self.curPiece is not NO_T_mo :
            key = event.key()
            if key in self.validKeys :
                event.accept() # Tell Qt, we got this one
                if key == Qt.Key.Key_P:
                    self.togglePause()
                elif key == Qt.Key.Key_Left:
                    self.tryMove(self.curPiece, self.curX - 1, self.curY)
                elif key == Qt.Key.Key_Right:
                    self.tryMove(self.curPiece, self.curX + 1, self.curY)
                elif key == Qt.Key.Key_Down:
                    self.tryMove(self.curPiece.rotateRight(), self.curX, self.curY)
                elif key == Qt.Key.Key_Up:
                    self.tryMove(self.curPiece.rotateLeft(), self.curX, self.curY)
                elif key == Qt.Key.Key_Space:
                    self.dropDown()
                elif key == Qt.Key.Key_D:
                    self.oneLineDown()
        if not event.isAccepted():
            '''either we are paused or not one of our keys'''
            super().keyPressEvent(event)

    def togglePause(self):
        '''
        On the pause key (or click of a Pause button not implemented) change
        the game paused state. Update the status line, and suggest to Qt that
        we be repainted.
        '''

        if not self.isStarted:
            return # ignore when not running

        self.isPaused = not self.isPaused

        if self.isPaused:
            self.timer.stop()
            self.NewStatus.emit("paused")

        else:
            '''
            Restart the timer. Note that when the timer becomes variable,
            this has to pick up the current interval.
            '''
            self.timer.start(Board.StartingSpeed, self)
            self.NewStatus.emit(str(self.completedLines))

        self.update()

    def timerEvent(self, event:QEvent):
        '''
        A timer has expired. If we are waiting after clearing whole lines,
        the wait is over and it is time to start a new tetronimo.

        Otherwise, it is time to move the active tetronimo down one.

        (note: Bodnar's code tests that the timer in the event is actually
        the timer we started. This seems odd, what other timer's event would
        be delivered to this widget? So, not doing that.)

        TODO: if timer interval is to change with #lines, this is
        the place to stop the timer and restart it with a new interval.
        '''
        event.accept()
        if self.waitForNextTimer:
            self.waitForNextTimer = False
            self.newPiece()
        else:
            self.oneLineDown()

    def oneLineDown(self):
        '''
        Move the active T_mo down one line, either because the timer
        expired or the D key was pressed. If it can't be moved down,
        place it into the board.
        '''
        if not self.tryMove(self.curPiece, self.curX, self.curY - 1):
            self.pieceDropped()

    def dropDown(self):
        '''
        The user wants to slam the current piece to the bottom. Note that
        tryMove, when the move is allowed, calls .update(), so the piece
        should be drawn in each row as it goes down, creating an animation.
        However this is not happening -- TODO: investigate.
        '''
        newY = self.curY
        while newY > 0:
            if not self.tryMove(self.curPiece, self.curX, newY - 1):
                break
            newY -= 1

        self.pieceDropped()

    def pieceDropped(self):
        '''
        The active T_mo has reached its final resting place.
        Install it into the board. Then remove any full lines that result.
        '''

        for (x,y) in self.curPiece.coords:
            self.setShapeAt(x+self.curX, y+self.curY, self.curPiece)

        self.removeFullLines()

        '''
        During line-removal we set waitForNextTimer. So there is nothing
        further to do here. If the timer has not expired, there's nothing to
        do, and if it has expired while removeFullLines was returning, the
        timerEvent has called newPiece().
        '''

    def setShapeAt(self, x:int, y:int, shape:T_mo):
        '''
        Install a T_mo into a cell of the board. That marks the cell
        as one the active piece cannot enter, and gives it a color.
        '''
        self.board[(y * Board.Columns) + x] = shape
        #print('shape {} at x {} y {}'.format(shape.t_name,x,y))

    def shapeAt(self, x, y) -> T_mo :
        '''
        Return the T_mo in the board cell at x, y. This just factors
        out some index arithmetic.
        '''
        return self.board[(y * Board.Columns) + x]

    def removeFullLines(self):
        '''
        The active T_mo has stopped moving and been installed into the board
        cells. This might have made one or more lines full. If so, remove
        those lines from the board. Increment the count of lines completed
        and update the status line.
        '''

        '''
        Make a list of the row indexes of full rows. A full row is one that
        contains no empty cells, i.e. no references to NO_T_mo.

        TODO: do this smarter by taking a row-length slice of the board
        and using "NO_T_mo not in..." the slice.
        '''
        rowsToRemove = []
        for i in range(Board.Rows):
            n = 0
            for j in range(Board.Columns):
                if self.shapeAt(j, i) is not NO_T_mo:
                    n = n + 1

            if n == Board.Columns:
                rowsToRemove.append(i)
        '''
        We built the list of filled rows from low indexes (visual bottom of
        the board) to high. But we want to remove them in the opposite
        sequence, from the visually upper, down. This is because if two
        filled rows are not contiguous we need to remove the visually higher
        one first.
        '''
        rowsToRemove.reverse()

        '''
        For each filled row from the visually highest (highest index) down,
        copy all rows above it down one row, replacing that filled row.

        In trying to think of a faster or different way to do this, keep in
        mind that (a) one filled row is the most common case and (b) when
        there is more than one, they need not be contiguous. It might be that
        rows 21 (bottom) and 19 are filled, but 20 is not.
        '''
        for m in rowsToRemove:
            for k in range(m, Board.Rows-1):
                for l in range(Board.Columns):
                    self.setShapeAt(l, k, self.shapeAt(l, k + 1))

        '''
        Update the status line to show zero or more rows removed.
        Set the flag to wait for the next timer interval before starting
        a new piece.
        '''
        self.completedLines += len(rowsToRemove)
        self.NewStatus.emit(str(self.completedLines))
        self.waitForNextTimer = True
        '''
        Make the current piece NO_T_mo so the paint routine will
        not try to draw it, and start a repaint.
        '''
        self.curPiece = NO_T_mo
        self.update()

    def paintEvent(self, event):
        '''
        Called by the Qt app when it thinks this QFrame should be updated,
        the paintEvent() method is responsible for drawing all shapes of the game.
        '''
        painter = QPainter(self)
        rect = self.contentsRect()
        boardTop = rect.bottom() - Board.Rows * self.cellHeight()

        for i in range(Board.Rows):
            for j in range(Board.Columns):
                self.drawSquare(painter,
                                rect.left() + j * self.cellWidth(),
                                boardTop + i * self.cellHeight(),
                                self.shapeAt(j, Board.Rows - i - 1))

        if self.curPiece is not NO_T_mo:
            '''
            Draw the active tetronimo around the current cell.
            '''
            for i in range(4):
                x = self.curX + self.curPiece.x(i)
                y = self.curY + self.curPiece.y(i)
                self.drawSquare(painter,
                                rect.left() + x * self.cellWidth(),
                                boardTop + (Board.Rows - y - 1) * self.cellHeight(),
                                self.curPiece)

    def cellWidth(self) -> int :
        '''
        Return the width of one board cell in pixels.
        Note that cell width and cell height should be the same,
        but we are not assuming that. (In Jan Bodnar's original it
        is possible to drag the board to any width with the result
        that cells become rectangular.)
        '''
        return self.contentsRect().width() // Board.Columns

    def cellHeight(self) -> int :
        '''
        Return the height of one board cell in pixels. See note above.
        '''
        return self.contentsRect().height() // Board.Rows

    def drawSquare(self, painter:QPainter, x:int, y:int, shape:T_mo):
        '''
        Draw one cell of the board with the color of the tetronimo
        that is in that cell. The T_mo knows its own QColor.

        First, paint a rectangle inset 1 pixel from the cell boundary in
        the T_mo's color.
        '''
        color = shape.color()
        painter.fillRect(x + 1, y + 1, self.cellWidth() - 2,
            self.cellHeight() - 2, color)

        '''
        Then, give the rectangle a "drop shadow" outline, lighter on two
        sides and darker on two, using the very convenient lighter/darker
        methods of the QColor class.
        '''
        painter.setPen(color.lighter())
        painter.drawLine(x, y + self.cellHeight() - 1, x, y)
        painter.drawLine(x, y, x + self.cellWidth() - 1, y)

        painter.setPen(color.darker())
        painter.drawLine(x + 1, y + self.cellHeight() - 1,
            x + self.cellWidth() - 1, y + self.cellHeight() - 1)
        painter.drawLine(x + self.cellWidth() - 1,
            y + self.cellHeight() - 1, x + self.cellWidth() - 1, y + 1)

'''
        Define the main window.
'''

class Tetris(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Tetris')
        '''
        Create the board and make it the central widget.
        TODO: add Start and Pause buttons, arrange them below the
        board with a QVboxLayout.
        '''
        self.tboard = Board(self)
        self.setCentralWidget(self.tboard)
        '''
        Connect the board's status update signal to the status bar's
        showMessage method.
        '''
        self.tboard.NewStatus[str].connect(self.statusBar().showMessage)
        '''
        Set the main window geometry.
        TODO: get the geometry from a QSettings, and save the geometry
        at shutdown.
        '''
        self.resize(180, 380)
        #self.center()
        '''
        Start the game.
        '''
        self.tboard.start()
        self.show()

    def center(self):
        '''centers the window on the screen'''

        #screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width()-size.width())/2,
            (screen.height()-size.height())/2)

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# Command line execution


if __name__ == '__main__':

    import sys
    '''
    Initialize the random seed from the command line if there is an
    argument and it is convertable to int. Otherwise don't.
    '''
    try :
        random.seed( int( sys.argv[1] ) )
    except : # whatever...
        random.seed()

    app = QApplication([])
    tetris = Tetris()
    tetris.show
    sys.exit(app.exec())
