'''
        Tetris implemented in PyQt

This is an expansion of the simple game (see standard.py) using the same
techniques, but adding full game features such as wall-kick, next-piece
preview, score records, and sound. In general game play conforms to the
Tetris Guideline for play as described at
    http://tetris.wikia.com/wiki/Tetris_Wiki

The GUI structure is based on a QMainWindow. The provided Tool Bar offers
buttons for Pause, Restart, Sound, Music, and for a display of high scores.

The status line shows the game state, either paused, or a count of completed
lines.

The central widget is a QFrame which implements the game; it is in effect the
"controller" in an MVC design. The Game contains a Board object (comprising
both "model" and "view") composed of cells in 22 rows and 10 columns. To its
right is a small Board showing the next pieces to come. On the left is a
small Board showing the currently "held" piece if any.

'''

from PyQt5.QtWidgets import (
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSlider,
    QToolBar,
    QVBoxLayout
    )
from PyQt5.QtCore import (
    Qt,
    QBasicTimer,
    QEvent,
    QPoint,
    QRect,
    QSettings,
    QSize,
    pyqtSignal
    )
from PyQt5.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPixmap
    )
from PyQt5.QtMultimedia import (
    QMediaContent,
    QMediaPlayer,
    QSoundEffect
)
from PyQt5.QtCore import QUrl
from PyQt5.QtTest import QTest # for qWait
import typing
import random
import enum

'''

Tetronimo Object
================

We begin by defining the Tetronimo, the basic game piece.

Names of Shapes
---------------

Name the seven Tetronimoes via an IntEnum. Note that 'O', 'I', 'T' and so
forth are the standardized names for the shapes, per the tetris wiki.

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

Colors of Tetronimos
--------------------

Assign standardized colors for the Tetronimoes, as specified in the Tetris
guidelines.

The colors are chosen from the list of available predefined colors that is
returned by QColor.colorNames(). (FYI: there are 148 names in that list,
alphabetically from "aliceblue" to "yellowgreen".)

The special color defined for the 'N' tetronimo is the color that will appear
in every empty board cell.

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

Tetronimo Shape and Initial Orientation
----------------------------------------

Per the guidelines, quote,

    "The playfield is ... 10 by 20 ..."
    "The tetriminoes spawn horizontally with J, L and T spawning flat-side first."
    "The I and O spawn in the middle columns
     The rest spawn in the left-middle columns"

As I interpret that, if the columns are numbered 0-9, the O spawns in columns
4, 5, and the I in columns 3, 4, 5, 6. The others (which are all 3 squares
wide when horizontal) spawn in columns 3, 4, 5.

The following design is due to Jan Bodnar (see URL to his game in
standard.py). Each Tetronimo is described by a tuple holding four (col,row)
tuples that specify four cells at the center of a coordinate plane.

The initial values when a tetronimo is created specify the initial (spawn)
rotation of a Tetronimo, where (col:0,row:0) will be spawned into row 1,
column 4 of the board.

For example the Z is:

                (-1,-1)(0,-1)
                       (0,0) (1,0)

while the L is:

                           (1,-1)
                (-1,0)(0,0)(1,0)

Tetronimo Rotation
------------------

This design has the very nice property that rotation is easy. To rotate a
shape left, replace the tuples of the original shape with the tuple
comprehension,

    ( (r,-c) for (c,r) in current_shape )

That is, reverse the meaning of the row and column values, negating the
column number. For example if L is currently

                           (1,-1)
                (-1,0)(0,0)(1,0)

then the new values given by `((r,-c) for (c,r) in current_shape)` is

             (-1,-1) (0,-1)
                     (0,0)
                     (0,1)

To rotate a shape right, use `((-r,c) for (c,r) in current_shape)`,
which applied to original L gives

              (0,-1)
              (0,0)
              (0,1) (1,1)

'''
T_Shapes = {
    T_ShapeNames.N : ((0,0),(0,0),(0,0),(0,0)),
    T_ShapeNames.O : ((0,0),(1,0),(0,1),(1,1)),
    T_ShapeNames.I : ((-2,0),(-1,0),(0,0),(1,0)),
    T_ShapeNames.T : ((0,-1),(-1,0),(0,0),(1,0)),
    T_ShapeNames.L : ((1,-1),(-1,0),(0,0),(1,0)),
    T_ShapeNames.J : ((-1,-1),(-1,0),(0,0),(1,0)),
    T_ShapeNames.S : ((1,-1),(0,-1),(0,0),(-1,0)),
    T_ShapeNames.Z : ((-1,-1),(0,-1),(0,0),(1,0))
    }

'''

Tetronimo Class Definition (T_mo)
---------------------------------

A Tetronimo knows its shape name and color, and its current shape in terms of
a tuple of the four (c,r) values of each of its cells, initialized from
T_Shapes above.

A T_mo can rotate, but note that the `rotate_left()` and `rotate_right()`
methods do _not_ modify the shape of the "self" T_mo! They return a _new_
T_mo intended to replace this one. This is done so that the game can test a
rotation. If the new, rotated T_mo is legal, it will replace the old; but if
it it collides with something, the original T_mo can be left unchanged.

'''
class T_mo(object):
    def __init__(self, t_name: T_ShapeNames) :
        self.t_name = t_name
        self.t_color = T_Colors[t_name]
        self.coords = tuple( ((c,r) for (c,r) in T_Shapes[t_name]) )

    def color(self) -> QColor :
        return self.t_color

    '''
    Return the r and c values of one of the four cells of this T_mo
    '''
    def c(self, cell:int ) -> int :
        return self.coords[cell][0]
    def r(self, cell:int ) -> int :
        return self.coords[cell][1]

    '''
    Return the minimum and maximum r and c values of this T_mo. These are
    used to compute collisions.
    TODO: NOT USED ELIMINATE?
    '''
    #def r_max(self) -> int :
        #return max( (r for (c,r) in self.coords) )
    #def r_min(self) -> int :
        #return min( (r for (c,r) in self.coords) )
    #def c_max(self) -> int :
        #return max( (c for (c,r) in self.coords) )
    #def c_min(self) -> int :
        #return min( (c for (c,r) in self.coords) )

    '''
    Return a new T_mo with its shape rotated either left or right.

    Just in case at some point we need to sub-class the T_mo, we create the
    new object using type(self)() instead of naming the class explicitly.
    '''
    def rotateLeft(self) :
        new_tmo = type(self)( self.t_name )
        new_tmo.coords = tuple( ((r,-c) for (c,r) in self.coords ) )
        return new_tmo
    def rotateRight(self) :
        new_tmo = type(self)( self.t_name )
        new_tmo.coords = tuple( ((-r,c) for (c,r) in self.coords ) )
        return new_tmo

'''

Global "N" T_mo
---------------

This global instance of T_mo is the only one of an 'N' tetronimo. It is
referenced from any unoccupied board cell, giving empty cells their color.
Thus `x is NO_T_mo` is the test for an empty cell.

'''
NO_T_mo = T_mo( T_ShapeNames.N )
'''

The Board
=========

The Board object displays as an array of square cells. The number of rows and
columns are initialization parameters. The main board of course is 10x20, but
the Board for the preview is smaller.

The cells are drawn during a paint event, and the `paintEvent()` method and
its subroutines are the bulk of the Board logic. Each cell of a Board
contains only a reference to a T_mo. The color of that T_mo is the color of
the cell. Empty cells all refer to the global `NO_T_mo` and so are drawn with
a light gray color.

The Board keeps a reference to a "current" T_mo. On the main board this is
the T_mo that the user is controlling. During a paintEvent, this T_mo is
drawn separately, after the other cells and on top of them.

Board Geometry
--------------

Board location is by row and column. Columns are numbered from 0 to
self.cols, increasing from left to right. Rows are numbered from 0 to
self.rows, increasing from 0 at the top toward the bottom.

Some confusion arises (in me!) from trying to use "x" and "y" when referring
to cells. So in the code all access to coordinates is in terms of "row" and
"col" (or r/c).

The location of the center cell of the current T_mo is returned by
currentColumn() and currentRow(). (The center cell is the one with value
(0,0) in the T_Shapes table, and this remains true under rotation.)

Testing a Move
--------------

The Board provides the `testAndPlace()` method, which tests the four cells
of a proposed T_mo against the Board margins and the existing cells. It
returns one of three values,

  * Board.OK when the cells of the T_mo do not overlap a colored cell and do
    not extend outside the board. The given T_mo will be assigned as the
    current piece, replacing it.

  * Board.TOUCH when a cell of the T_mo overlaps a cell that is not
    empty. (This is tested before the following tests.)

  * Board.LEFT when a cell of the current T_mo would fall outside the left
    board margin.

  * Board.RIGHT when it would fall outside the right margin.

Completing a Move
-----------------

The Board provides the `place()` method, which merges the current T_mo
into the cells of the board.

Next to be called is the `winnow()` method that looks for and removes
completed lines. The number of removed lines is returned.

Retaining Cell Aspect Ratio
---------------------------

In order to ensure that all board cells are drawn as squares, the aspect
ratio of the board must be preserved during a resize event. Supposedly this
can be done by implementing the QWidget methods `hasHeightForWidth` and
`heightForWidth` but in fact those are never called during a resize (yes,
the Qt docs lie).

What does work is the method described here:

https://stackoverflow.com/questions/8211982/qt-resizing-a-qlabel-containing-a-qpixmap-while-keeping-its-aspect-ratio

which is, during a resizeEvent, to call `setContentsMargins()` to set new
margins which will force the resized height and width into the proper ratio.
In this case, rather than setting contents margins directly, we use the Widget
CSS styling to set the padding of the board. Same idea.

'''
class Board(QFrame):
    '''
    Values returned by testAndPlace()
    '''
    OK = 0
    TOUCH = 1
    LEFT = 2
    RIGHT = 3
    '''
    CSS style applied during a resize. format() is used to install numbers.
    '''
    board_style = '''
    Board{{
        border: 2px solid gray;
        padding-top: {}px ;
        padding-right: {}px ;
        padding-bottom: {}px ;
        padding-left: {}px ;
        }}
    '''
    def __init__(self, parent, rows:int, columns:int):
        super().__init__(parent)
        self.rows = rows
        self.cols = columns
        self.aspect = rows/columns
        self.setStyleSheet( Board.board_style.format(0,0,0,0) )
        '''
        Set the size policy so we cannot shrink below 10px per cell, but can
        grow. Any change will be preceded by a resize event; see
        `resizeEvent()` below for how that is handled to maintain square cells.
        '''
        self.setMinimumHeight(int(10*rows))
        self.setMinimumWidth(int(10*columns))
        sp = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setSizePolicy(sp)
        '''
        The board contents is rows*columns cells, each referring to a T_mo.
        '''
        self.size = rows*columns
        self.cells = [] # type: List[T_mo]
        self.clear() # populate the board with empty cells
        '''
        These slots hold info about the current piece, if any.
        '''
        self._current = NO_T_mo # type: T_mo
        self._col = 0
        self._row = 0

    '''
    Clear the board to empty cells, at initialization and when the game is
    reset. Force a paint event so the board is re-drawn.
    '''
    def clear(self):
        self._current = NO_T_mo
        self._col = 0
        self._row = 0
        self.cells = [NO_T_mo]*self.size
        self.update( self.contentsRect() ) # forces a paint event
    '''
    Return the current piece or its location
    '''
    def currentPiece(self) -> T_mo:
        return self._current
    def currentColumn(self) -> int:
        return self._col
    def currentRow(self) -> int:
        return self._row
    '''
    Return the T_mo in our array at a given row and column.
    '''
    def shapeInCell(self,row:int,col:int) -> T_mo:
        return self.cells[row*self.cols + col]
    '''
    Set the cell at a given row and column to contain the given T_mo.
    '''
    def setCell(self, row:int, col:int, shape:T_mo) :
        self.cells[row*self.cols + col] = shape

    '''
    Test a tetronimo in a new position or orientation. This method is
    called when a new piece is first created, and when the active piece
    is rotated or translated.

    If there exists another tetronimo already in a cell that the new position
    would occupy, the change is not allowed and we return Board.TOUCH. If the
    T_mo would go outside a wall, we return Board.LEFT or Board.RIGHT. In
    these cases, no change is made to the board. The caller has to decide
    what to do next.

    If the proposed tetronimo covers only empty cells, the move is completed
    by saving the T_mo and its coordinates as the current piece, replacing
    the previous current piece.

    After accepting a change we call QWidget.repaint(), to force a call to
    paintEvent() so that the piece is seen to descend.
    '''

    def testAndPlace(self, new_piece:T_mo, new_row:int, new_col:int) ->int :
        #print('t&p at r{} c{} ->'.format(new_row,new_col), end=' ')
        for i in range(4):
            r = new_row + new_piece.r(i)
            c = new_col + new_piece.c(i)
            if c < 0 :
                #print('left')
                return Board.LEFT
            elif c >= self.cols:
                #print('right')
                return Board.RIGHT
            elif r < 0 \
            or r >= self.rows \
            or self.shapeInCell(row=r,col=c) is not NO_T_mo:
                #print('touch')
                return Board.TOUCH

        # It fits, place it
        #print('ok')
        self._current = new_piece
        self._row = new_row
        self._col = new_col
        self.repaint()
        return Board.OK

    def place(self):
        '''
        The current T_mo has reached its final resting place. Install it into the
        board cells so they will show its color and no longer appear empty to
        testAndPlace().
        '''
        for (c,r) in self._current.coords:
            self.setCell(row=r+self._row, col=c+self._col, shape=self._current)
    '''
    After place() has been called, winnow can be called to find out if any
    rows have been completely filled, and eliminate them. As many as four
    rows might have been filled (by a well-placed I piece). Filled rows need
    not be contiguous.

    Note that making sounds, updating scores, etc. are up to the caller.
    '''
    def winnow(self) -> int :
        '''
        Step through the rows of the board and make a list of the row indices
        of rows that are full, i.e. do not contain any NO_T_mo cells.
        '''
        full_rows = []
        for row in range(0, len(self.cells), self.cols) :
            if NO_T_mo in self.cells[row:row+self.cols] :
                continue
            full_rows.append(row)

        if full_rows:
            '''
            Full rows are deleted from the cells list. Do this from last
            (higher index) to first (lower index) so as not to invalidate the
            index of undeleted rows.
            '''
            for row in reversed(full_rows):
                del self.cells[row:row+self.cols]
            '''
            Install an equal number of blank rows at the top, pushing existing
            non-full rows down.

            Note this means the "falling" of rows happens all at once. Some
            tetris games let the rows fall separately like bricks, and that
            would be nice.
            '''
            new_rows = [NO_T_mo]*(len(full_rows)*self.cols)
            self.cells = new_rows + self.cells
            #self.update( self.contentsRect() ) # force a paint event
            #self.repaint()

        return len(full_rows)
    '''
    A paint event occurs when the Qt app thinks this QFrame should be
    updated. The event handler is responsible for drawing all the shapes in
    the contents rectangle of this widget.

    Note that the contents margins that may be set during a resize event to
    maintain the aspect ratio, are not painted here. Margins are painted by the
    containing widget.
    '''
    def paintEvent(self, event):
        rect = self.contentsRect()
        # Note the pixel dimensions of one cell, for use in the drawCell method.
        # cell_width SHOULD equal cell_height always, but don't assume it.
        self.cell_width = rect.width() // self.cols
        self.cell_height = rect.height() // self.rows

        painter = QPainter(self)

        for v in range(self.rows):
            for h in range(self.cols):
                self.drawCell(painter,
                                rect.left() + h * self.cell_width,
                                rect.top() + v * self.cell_height,
                                self.shapeInCell(row=v, col=h)
                                )

        if self._current is not NO_T_mo:
            '''
            Draw the current tetronimo at its given location.
            '''
            for i in range(4):
                c = self._col + self._current.c(i)
                r = self._row + self._current.r(i)
                self.drawCell(painter,
                                rect.left() + c * self.cell_width,
                                rect.top() + r * self.cell_height,
                                self._current
                                )

    '''
    During a paint event (above) draw one cell of the board with the color of
    the tetronimo that is in that cell. The T_mo knows its own QColor.
    '''
    def drawCell(self, painter:QPainter, x:int, y:int, shape:T_mo):
        '''
        First, paint a rectangle, inset 1 pixel from the cell boundary, in
        the T_mo's color.
        '''
        color = shape.color()
        painter.fillRect(x + 1,
                         y + 1,
                         self.cell_width - 2,
                         self.cell_height - 2,
                         color)

        '''
        Then, give the rectangle a "drop shadow" outline, lighter on top and
        left sides and darker on bottom and right, using the very convenient
        lighter/darker methods of the QColor class.
        '''
        painter.setPen(color.lighter())
        painter.drawLine(x, y + self.cell_height - 1, x, y)
        painter.drawLine(x, y, x + self.cell_width - 1, y)

        painter.setPen(color.darker())
        painter.drawLine(x + 1, y + self.cell_height - 1,
                         x + self.cell_width - 1, y + self.cell_height - 1)
        painter.drawLine(x + self.cell_width - 1, y + self.cell_height - 1,
                         x + self.cell_width - 1, y + 1)
    '''
    A resize event occurs once, before this widget is made visible (promised
    in the doc page for QWidget), and again whenever the user drags our
    parent widget to a new shape.

    The Board wants to maintain its aspect ratio A=self.rows/self.columns.
    Upon a resize event, look at the new height H and width W. If H/W is not
    equal to A, adjust the style padding to restore the aspect ratio.

    Let A=rows/cols be the desired aspect ratio (A=2.2 for the main board).
    Let B=H/W, the resized ratio.

    Suppose B<A, indicating that the width is greater than desired. (Actually
    the height has been reduced.) We want to effectively reduce the width by
    padding, to force the cell array back to about the A aspect ratio (at the
    cost of shrinking the array in the frame).

        A = H/W-S
        A/H = 1/W-S
        H/A = W-S
        H/A-W = S

    Set the left and right padding to S pixels, equally divided.

    Suppose B>A, indicating the width is too narrow, or the height is too much.
    Reduce the height by padding with T pixels:

        A = H-T/W
        WA = H-T
        WA-H = T

    Set the top and bottom padding to T pixels, equally divided.
    '''
    def resizeEvent(self, event):
        H = float(self.height())
        W = float(self.width())
        new_aspect = H/W
        #print('resize, new aspect {} desired {}'.format(new_aspect,self.aspect))
        if new_aspect < self.aspect:
            '''
            Resized dimensions are too narrow, need to pad the sides.
            H/A-W = S
            '''
            adjust = abs(int( H/self.aspect - W ))
            if adjust > 1:
                # split S into approximately equal parts and add to
                # side margins
                add_left = adjust//2
                add_right = adjust - add_left
                #print('new left/right {}/{}'.format(add_left,add_right))
                self.setStyleSheet(
                    Board.board_style.format(0,add_right,0,add_left)
                    )
        else :
            '''
            Resized dimensions are ok or too tall. Pad the top and bottom
            margins as necessary. A*W-H = T
            '''
            adjust = abs(int( self.aspect*W - H ))
            if adjust > 1:
                # split T into approximately equal parts and add to
                # top and bottom margins
                add_top = adjust//2
                add_bottom = adjust-add_top
                #print('new top/bottom {}/{}'.format(add_top,add_bottom))
                self.setStyleSheet(
                    Board.board_style.format(add_top,0,add_bottom,0)
                    )
        super().resizeEvent(event)

'''

The Game Class
==============

The Game is a frame that contains the playing field (a Board), and shows a
preview of the upcoming T_mo (also a Board), a display of the current count
of lines and current score.

The Game implements the rules of the game by responding appropriately to
keystrokes and timer events to move the current piece and update the board
when the current piece stops moving.

TODO:
    initialize the UI
    implement the timer
    implement keystrokes
    implement piece movement
    implement signal to parent on game over
    implement signals to parent for SFX

'''

class Game(QFrame):
    '''
    Initial game-step-time in milliseconds.
    '''
    StartingSpeed = 750
    '''
    Lines to a level change
    '''
    LinesPerLevel = 10
    '''
    Time reduction factor: game step time is multipled by this
    after every LinesPerLevel lines have been cleared.
    '''
    TimeFactor = 0.75

    def __init__(self, parent, high_score, sfx_dict):
        super().__init__()
        '''
        Save the previous high score and a reference to the
        dict of QSoundEffects provided by the main window.
        '''
        self.high_score = high_score
        self.sfx = sfx_dict
        '''
        Direct all keystrokes seen by a contained widget, to this widget.
        '''
        self.setFocusPolicy(Qt.StrongFocus)
        '''
        Create the timer that sets the pace of the game.
        Create the timer interval, initially StartingSpeed.
        Create the count of lines cleared.
        '''
        self.timer = QBasicTimer()
        self.timeStep = Game.StartingSpeed
        self.lines_cleared = 0
        '''
        Create the flag that is set True after clearing any complete lines,
        so that the next piece is not created until the timer expires.
        '''
        self.waitForNextTimer = False
        '''
        Create state flags. self.start() is called by the main window.
        isPaused flag is toggled in self.pause() by a P keystroke.
        isOver means, need to clear the board of previous game.
        '''
        self.isStarted = False
        self.isPaused = False
        self.isOver = False
        '''
        Create the "bag" of upcoming T-mos.
        '''
        self.bag_of_pieces = [] # Type: typing.List[T_mo]
        '''
        Create sets of accepted keys, for quick reference during a
        keyPressEvent. The keys to be recognized are those listed in "4.1
        Table of Basic Controls" in the Tetris guidelines. The frozenset

        The names of keys and modifier codes are defined in the Qt namespace,
        see http://doc.qt.io/qt-5/qt.html#Key-enum. For simple recognition we
        take the modifier value and OR it with the key code.

        We create a set of the key values that command each operation. For
        speed we use frozenset. The frozenset constructor requires an
        iterator as its argument; we give it a tuple, hence lots of parens.

        Note: on the macbook (at least) the arrow keys have the keypad bit
        set. Don't know about other platforms.
        '''
        self.Keys_left = frozenset((
            int(Qt.Key_Left),
            int(Qt.KeypadModifier)|int(Qt.Key_Left),
            int(Qt.KeypadModifier)|int(Qt.Key_4)
            ))
        self.Keys_right = frozenset((
            int(Qt.Key_Right),
            int(Qt.KeypadModifier)|int(Qt.Key_Right),
            int(Qt.KeypadModifier)|int(Qt.Key_6)
            ))
        self.Keys_hard_drop = frozenset((
            int(Qt.Key_Space),
            int(Qt.KeypadModifier)|int(Qt.Key_8)
            ))
        self.Keys_soft_drop = frozenset((
            int(Qt.Key_D),
            int(Qt.KeypadModifier)|int(Qt.Key_2)
            ))
        self.Keys_clockwise = frozenset((
            int(Qt.Key_Up),
            int(Qt.KeypadModifier)|int(Qt.Key_Up),
            int(Qt.Key_X),
            int(Qt.KeypadModifier)|int(Qt.Key_1),
            int(Qt.KeypadModifier)|int(Qt.Key_5),
            int(Qt.KeypadModifier)|int(Qt.Key_9)
            ))
        self.Keys_widdershins = frozenset((
            int(Qt.Key_Down),
            int(Qt.KeypadModifier)|int(Qt.Key_Down),
            int(Qt.Key_Z),
            int(Qt.KeypadModifier)|int(Qt.Key_3),
            int(Qt.KeypadModifier)|int(Qt.Key_7)
            ))
        self.Keys_hold = frozenset((
            int(Qt.Key_Shift),
            int(Qt.Key_C),
            int(Qt.KeypadModifier)|int(Qt.Key_0)
            ))
        self.Keys_pause = frozenset((
            int(Qt.Key_P),
            int(Qt.Key_Escape),
            int(Qt.Key_F1)
            ))
        '''
        Merge the sets of accepted keys into one set so we can make a very
        fast "Do we handle this key?" test.
        '''
        self.validKeys = frozenset(
            self.Keys_left | self.Keys_right | self.Keys_hard_drop | \
            self.Keys_soft_drop | self.Keys_clockwise | \
            self.Keys_widdershins | self.Keys_hold | self.Keys_pause
            )
        '''
        Create the playing board and lay it out.
        There are three blocks to the board:
            Left:    Held piece (TODO)
                     Lines cleared
                     Level
                     Score
            Center:  The game board
            Right:   The Next piece preview

        Create the game board.
        '''
        self.board = Board(self,22,10)
        '''
        Create the layout as an HBox. Give it left and right sublayouts
        and the game board in the center.
        '''
        layout = QHBoxLayout()
        left_vb = QVBoxLayout()
        right_vb = QVBoxLayout()
        layout.addLayout(left_vb,1)
        layout.addWidget(self.board,2)
        layout.addLayout(right_vb,1)
        '''
        Create the T_mo last held, and a tiny Board in which to display it.
        '''
        self.held_piece = NO_T_mo
        self.held_display = Board(None,5,5)
        '''
        Create the numerical variables that hold the lines cleared and the
        current score. (self.high_score already exists).
        '''
        self.current_score = 0
        self.lines_cleared = 0
        self.current_level = 0
        '''
        The left VBox has the held-piece display at the top, then space.
        '''
        left_vb.addWidget(self.held_display,1)
        left_vb.addStretch(2)
        '''
        Create a grid layout for the four score numbers. Each row has a
        QLabel for a caption, and QLabel to display the value. We keep a reference
        to the latter so its text can be updated as needed.
        '''
        score_grid = QGridLayout()

        lines_caption = self.make_label('Lines Cleared')
        score_grid.addWidget(lines_caption, 0, 0, 1, 1)
        self.lines_display = self.make_label()
        score_grid.addWidget(self.lines_display, 0, 1, 1, 1)

        level_caption = self.make_label('Level')
        score_grid.addWidget(level_caption, 1, 0, 1, 1)
        self.level_display = self.make_label()
        score_grid.addWidget(self.level_display, 1, 1, 1, 1)

        score_caption = self.make_label('Score')
        score_grid.addWidget(score_caption, 2, 0, 1, 1)
        self.score_display = self.make_label()
        score_grid.addWidget(self.score_display, 2, 1, 1, 1)

        high_caption = self.make_label('High Score')
        score_grid.addWidget(high_caption, 3, 0, 1, 1)
        self.high_display = self.make_label()
        score_grid.addWidget(self.high_display, 3, 1, 1, 1)

        left_vb.addLayout(score_grid)
        '''
        Populate the right VBox with the preview board.
        '''
        #right_vb = QVBoxLayout()
        #right_vb.addWidget( QLabel("Nonce"))
        #layout.addChildLayout(right_vb)
        right_vb.addWidget(QLabel('Preview!'))

        self.setLayout(layout)
        '''
        Initialize all the above.
        '''
        self.clear()
    '''
    Take the job of creating a QLabel for caption or score out of line.
    Caption label has a text, and is a raised panel. Score label has no
    text and is a sunken panel. Code from a .uic file.
    '''
    def make_label(self,text:str = None):
        label = QLabel(self)
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        font.setWeight(75)
        label.setFont(font)
        if text: # caption
            #label.setFrameShadow(QFrame.Raised)
            label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
            label.setText(text)
        else:
            label.setFrameShape(QFrame.Panel)
            label.setLineWidth(2)
            label.setFrameShadow(QFrame.Sunken)
            label.setAlignment(Qt.AlignCenter)
            label.setText('0')
            label.setMinimumWidth(80)
        return label

    '''
    Reset the game clearing everything.
    '''
    def clear(self):
        self.timer.stop()
        self.board.clear()
        self.isStarted = False
        self.isPaused = False
        self.isOver = False
        self.timeStep = Game.StartingSpeed
        self.current_level = 0
        self.level_display.setText('0')
        self.current_score = 0
        self.score_display.setText('0')
        self.high_display.setText(str(self.high_score))
        self.lines_cleared = 0
        self.lines_display.setText('0')
        self.held_piece = NO_T_mo
        self.held_display.clear()
        self.bag_of_pieces = self.make_bag()
        self.update( self.contentsRect() ) # force a paint event

    def make_bag(self) -> typing.List[T_mo] :
        '''
        Create a "bag" of seven Tetronimos in random order. They will be
        consumed before another bag is requested. This prevents the
        frustrations of a naive randomizer, where you can get many quick
        repeats or many long droughts. With the bag system you never get more
        than two identical pieces in a row, or go longer than 12 before
        getting another of the same type.
        '''
        bag = [ T_mo(T_ShapeNames(v)) for v in range(1,8) ]
        random.shuffle(bag)
        return bag
    '''
    Begin or resume play. If the board has a current piece, we are
    resuming after a pause. Otherwise we need to start a piece.
    '''
    def start(self):
        if self.isOver :
            self.clear()
        self.isStarted = True
        self.timer.start( self.timeStep, self )
        if self.board.currentPiece() is NO_T_mo :
            self.newPiece()
    '''
    The Pause icon has been clicked (in which case isPaused must be False,
    because the icon is grayed out while paused), or the P key has been
    pressed to toggle pausing (in which case isPaused could be true).
    '''
    def pause(self):
        self.isPaused = not self.isPaused
        if self.isPaused :
            # stop the timer
            self.timer.stop()
        else :
            # P key wants to restart the game
            self.start()

    def game_over(self):
        #print('game over')
        self.timer.stop()
        self.isStarted = False
        self.isOver = True
        if self.high_score < self.current_score :
            #TODO: can we make the new high score flash a few times?
            #TODO: make different end of game sound for new high score
            self.high_score = self.current_score
            self.high_display.setText(str(self.high_score))
        # TODO: make appropriate sound
    '''
    Take the next piece from the bag, refilling the bag if necessary, and
    put it on the board at the middle column and row 1 (second from top).
    If it won't fit, the game is over.

    TODO: preview
    '''
    def newPiece(self):
        #print('new piece')
        if 0 == len(self.bag_of_pieces):
            self.bag_of_pieces = self.make_bag()
        if self.board.testAndPlace(
            new_piece=self.bag_of_pieces.pop(),
            new_row=1,
            new_col=self.board.cols//2) == Board.OK :
            return
        self.game_over()
    '''
    A timer has expired. Normally this means it is time to move the
    current piece down one line.

    If we are waiting after clearing whole lines, the wait is over and it
    is time to start a new tetronimo. In that case, we need to re-set the
    timer interval, as it may have been changed while clearing lines.
    '''
    def timerEvent(self, event:QEvent):
        event.accept()
        #print('timer')
        if self.isStarted:
            self.score_display.setText(str(self.current_score))
            if not self.waitForNextTimer:
                self.oneLineDown()
            else:
                self.waitForNextTimer = False
                self.timer.stop()
                self.timer.start( self.timeStep, self )
                self.newPiece()
        else: # ignore possible timer while processing game_over
            pass
    '''
    Process a key press. Any key press (not release) while the focus is
    in the board comes here. The key code is event.key() If the key is in
    self.validKeys, we can handle the event. Otherwise pass it to our
    parent.
    '''
    def keyPressEvent(self, event:QEvent):
        if self.isStarted and self.board.currentPiece() is not NO_T_mo :
            key = int(event.key()) | int(event.modifiers())
            if key in self.validKeys :
                event.accept() # Tell Qt, we got this one
                if key in self.Keys_left:
                    self.moveSideways(toleft=True)
                elif key in self.Keys_right:
                    self.moveSideways(toleft=False)
                elif key in self.Keys_hard_drop:
                    self.dropDown()
                elif key in self.Keys_soft_drop:
                    self.oneLineDown()
                    self.current_score += 1
                elif key in self.Keys_clockwise:
                    self.rotatePiece(toleft=False)
                elif key in self.Keys_widdershins:
                    self.rotatePiece(toleft=True)
                elif key in self.Keys_hold:
                    pass # TODO WHAT IS HOLD AND HOW TO DO IT
                elif key in self.Keys_pause:
                    self.pause()
        if not event.isAccepted():
            '''either we are paused or not one of our keys'''
            super().keyPressEvent(event)
    '''
    Move the active T_mo down one line, either because the timer expired
    or a soft-drop key was pressed. If successful, return True.

    If it can't be moved down, place it into the board and return False.

    Note we don't expect to get Board.LEFT/RIGHT returns when
    moving down.
    '''
    def oneLineDown(self):
        if self.board.testAndPlace(
            new_piece=self.board.currentPiece(),
            new_row=self.board.currentRow() + 1,
            new_col=self.board.currentColumn()) == Board.OK:
            # translated T_mo is happy where it is, current piece
            # has been updated to new position.
            # TODO: make move noise
            return True
        '''
        Cannot move this piece down, so it has reached its final position,
        so make it a permanent part of the board.
        '''
        self.board.place()
        self.waitForNextTimer = True
        '''
        That may have filled one or more rows. Count the lines cleared
        and adjust the timer interval based on how many lines have been cleared.
        '''
        n = self.board.winnow()
        if n :
            # TODO make clearing noise
            self.lines_cleared += n
            self.current_level = self.lines_cleared // Game.LinesPerLevel
            self.current_score += (1+self.current_level)*(100,300,500,800)[n-1]
            self.lines_display.setText( str(self.lines_cleared) )
            self.level_display.setText( str(self.current_level) )
            self.timeStep = max(20,
                int(Game.StartingSpeed * ( Game.TimeFactor ** self.current_level))
                               )
        return False
    '''
    The user wants to slam the current piece to the bottom. Move it
    down repeatedly until it hits bottom.
    '''
    def dropDown(self):
        while self.oneLineDown() :
            self.current_score += 2
    '''
    The user has hit a key to move the current piece left or right
    '''
    def moveSideways(self, toleft:bool) :
        X = self.board.currentColumn()-1 if toleft else self.board.currentColumn()+1
        if self.board.testAndPlace(
            new_piece=self.board.currentPiece(),
            new_row=self.board.currentRow(),
            new_col=X) == Board.OK :
            # TODO: make move noise
            return True
        # TODO: make bonk noise
        return False
    '''
    The user has hit a key to rotate the current piece.
    '''
    def rotatePiece(self, toleft:bool ) :
        new_piece = self.board.currentPiece().rotateLeft() if toleft else \
                    self.board.currentPiece().rotateRight()
        result = self.board.testAndPlace(
            new_piece=new_piece,
            new_row=self.board.currentRow(),
            new_col=self.board.currentColumn())
        if result == Board.LEFT :
            # rotated piece overlaps left edge of board
            # try kicking it one place right
            result = self.board.testAndPlace(
                new_piece=new_piece,
                new_row=self.board.currentRow(),
                new_col=self.board.currentColumn()+1 )
        elif result == Board.RIGHT :
            # rotated piece overlaps right edge of board,
            # try kicking it one place left
            result = self.board.testAndPlace(
                new_piece=new_piece,
                new_row=self.board.currentRow(),
                new_col=self.board.currentColumn()-1 )
        # if the result (now) is OK, make rotate noise and return
        if result == Board.OK :
            # TODO: make rotate noise
            return True
        else :
            # TODO: make bonk noise
            return False

'''
Main Window
===========

The main window contains the Game object. It

* Provides a Toolbar with Pause and Restart buttons.
* Displays high scores.
* Implements music including volume and on/off.
* Records high scores in the Qt settings on shutdown.
* Records the app geometry in the Qt settings and restores it on startup.

'''

class Tetris(QMainWindow):

    def __init__(self, settings:QSettings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle('Tetris')
        '''
        Set Geometry
        ------------

        Recover the main window geometry from settings. Resize and position
        the default window to that geometry.
        '''
        self.move(self.settings.value("windowPosition", QPoint(50,50)))
        self.resize(self.settings.value("windowSize",QSize(500, 500)))

        '''
        Initialize SFX
        --------------

        Create sound effect objects for each of the .wav files loaded in the
        resources module: move, rotate, drop (manual), settle, line. Load them into
        a dict so they can be treated as a unit.

        Each QSoundEffect object loads its file, then can generate the sound with low
        latency when its play() method is called.

        The disadvantage of having one object per sound is, that each one has
        to have its volume adjusted individually.
        '''
        def makeSFX( path:str ) -> QSoundEffect :
            sfx = QSoundEffect()
            sfx.setSource(QUrl.fromLocalFile(':/'+path))
            sfx.setVolume(0.99)
            while not sfx.isLoaded():
                QApplication.instance().processEvents()
            return sfx
        self.sfx = dict()
        self.sfx['move'] = makeSFX( 'move.wav' )
        self.sfx['rotate'] = makeSFX('rotate.wav')
        self.sfx['drop'] = makeSFX('drop.wav')
        self.sfx['line'] = makeSFX('line.wav')
        self.sfx['settle'] = makeSFX('settle.wav')

        '''
        Initialize the Game
        --------------------

        Create the game and make it the central widget.
        Give it the saved high score from the settings.
        Make keyboard focus go to it.
        '''
        self.game = Game(self, self.settings.value("highScore",0), self.sfx)
        self.setCentralWidget(self.game)
        self.setFocusProxy(self.game)

        '''
        Initialize the Toolbar
        ----------------------

        Create the ToolBar and populate it with our actions. Connect
        each action's actionTriggered signal to its relevant slot.
        '''
        self.toolbar = QToolBar()
        self.addToolBar( self.toolbar )
        '''
        Set up the Play icon and connect it to playAction.
        '''
        self.play_action = self.toolbar.addAction(
            QIcon(QPixmap(':/icon_play.png')),'Play')
        self.play_action.triggered.connect(self.playAction)
        '''
        set up the Pause icon and connect it to pauseAction.
        '''
        self.pause_action = self.toolbar.addAction(
            QIcon(QPixmap(':/icon_pause.png')),'Pause')
        self.pause_action.triggered.connect(self.pauseAction)
        '''
        Set up the Restart icon and connect it to resetAction.
        '''
        self.reset_action = self.toolbar.addAction(
            QIcon(QPixmap(':/icon_reset.png')),'Reset')
        self.reset_action.triggered.connect(self.resetAction)
        '''
        With the control buttons created, set them to enabled or disabled
        states as appropriate.
        '''
        self.enableButtons()
        '''
        Insert the Mute button and the volume slider after a separator.
        Note the mute button action, unlike the other actions, is checkable,
        it remembers its state.
        '''
        self.toolbar.addSeparator()
        self.mute_action = self.toolbar.addAction(
            QIcon(QPixmap(':/icon_mute.png')),'Mute')
        self.mute_action.setCheckable(True)
        self.mute_action.triggered.connect(self.muteAction)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setTickPosition(QSlider.TicksBothSides)
        self.volume_slider.setRange(0,99)
        self.volume_slider.setTickInterval(25)
        self.volume_slider.setMaximumWidth(250)
        self.volume_slider.setMinimumWidth(50)
        self.volume_slider.valueChanged.connect(self.volumeAction)
        self.volume_slider.sliderReleased.connect(self.sliderAction)
        self.toolbar.addWidget(self.volume_slider)
        '''
        Recover the last volume value and last mute state from the settings.
        Call volumeAction to propogate the volume to the sfx objects.
        '''
        self.volume_slider.setValue(self.settings.value("volume",50))
        self.mute_action.setChecked(self.settings.value("mutestate",False))
        self.muted_volume = self.settings.value("mutedvol",50)
        self.volumeAction(self.volume_slider.value())


    '''
    Whenever the game state changes, enable or disable some combination of
    the control buttons.
    * Pause is enabled if the game is running and not paused.
    * Play is enabled if the game is not running, or if paused.
    * Reset is enabled if the game is running.
    '''
    def enableButtons(self):
        self.pause_action.setEnabled(
            self.game.isStarted and not self.game.isPaused )
        self.play_action.setEnabled(
            not(self.game.isStarted) or self.game.isPaused )
        self.reset_action.setEnabled(
            self.game.isStarted )

    '''
    Define Control Actions
    ----------------------

    These "slots" receive clicks on the control buttons.

    Play button: because of enableButtons(), this is only entered when the game
    state is either not-started, or paused.
    '''
    def playAction(self, toggled:bool):
        if self.game.isPaused :
            self.game.pause() # paused; toggle pause state
        else :
            self.game.start()
        self.enableButtons()
    '''
    Pause button: enableButtons ensures that Pause will only be
    enabled if the game is running.
    '''
    def pauseAction(self, toggled:bool):
        self.game.pause() # toggle to paused state
        self.enableButtons()

    def resetAction(self, toggled:bool):
        ans = QMessageBox.question(
            self, 'Reset clicked', 'Reset the game? State will be lost.' )
        if ans == QMessageBox.Ok or ans == QMessageBox.Yes :
            self.game.clear()
            self.game.start()
    '''
    This slot is called from the valueChanged signal of the volume slider,
    which can be the result of the user dragging the slider, or the program
    setting the value of the slider, as in muteAction below.

    Set the value on each of the QSoundEffect objects we own. Note that the
    QSoundEffect.setVolume() method wants a real, but the slider value is an int.
    '''
    def volumeAction(self, slider_value:int ) :
        real_volume = slider_value/100.0
        for sfx in self.sfx.values() :
            sfx.setVolume( real_volume )
    '''
    This action is called only when the user has dragged the volume slider
    and released it. The volumeAction volume change signal that calls
    volumeAction occurs separately; here we just want to release the Mute
    button if it is checked. N.B. calling setChecked does not cause the
    triggered signal that would invoke muteAction below.
    '''
    def sliderAction(self):
        self.mute_action.setChecked(False)
    '''
    This slot is called when the Mute button is clicked by the user. The Mute
    button action is checkable, and checked is the new state, on or off.

    When the mute state is now on, save the present volume slider value and
    set the volume to zero. When the state is now off, reset the volume
    slider to the saved value.
    '''
    def muteAction(self, checked:bool):
        if checked :
            self.muted_volume = self.volume_slider.value()
            self.volume_slider.setValue(0) # triggers entry to volumeAction
        else :
            self.volume_slider.setValue(self.muted_volume)
    '''
    Reimplement QWindow.closeEvent to save our geometry, the current high
    score, and various UI values.

    Note: it is not best design to fetch the possibly-changed high score by
    reaching into the game object, assuming it has a high_score attribute.
    '''
    def closeEvent(self, event:QEvent):
        self.settings.clear()
        self.settings.setValue("windowSize",self.size())
        self.settings.setValue("windowPosition",self.pos())
        self.settings.setValue("highScore",self.game.high_score)
        self.settings.setValue("volume",self.volume_slider.value())
        self.settings.setValue("mutestate",self.mute_action.isChecked())
        self.settings.setValue("mutedvol",self.muted_volume)
        super().closeEvent(event)


'''
Command-line execution.
TODO: decide on command parameters to support if any
TODO: define command parameters with argparse

currently this is basically unit test
'''

if __name__ == '__main__' :
    '''
    Initialize the random seed from the command line if there is an
    argument and it is convertable to int. Otherwise don't.
    '''
    try :
        random.seed( int( sys.argv[1] ) )
    except : # whatever...
        random.seed()
    '''
    Initialize the QT app including special handling for Linux
    '''
    from PyQt5.QtWidgets import QApplication
    import sys
    args = []
    if sys.platform.startswith('linux') :
        # avoid a GTK bug in Ubuntu Unity
        args = ['','-style','Cleanlooks']

    the_app = QApplication( args )
    the_app.setOrganizationName( "TassoSoft" )
    the_app.setOrganizationDomain( "nodomain.org" )
    the_app.setApplicationName( "Tetris" )
    '''
    Load the resources (icons) from resources.py, which was
    prepared using pyrrc5. This has to be done after the app is set up.
    '''
    import resources
    '''
    Access the QSettings object used by the main window.
    '''
    from PyQt5.QtCore import QSettings
    the_settings = QSettings()
    '''
    Create the main window (which creates everything else), passing
    the settings object for use in starting up and shutting down.
    Then display it and begin execution.
    '''
    the_main_window = Tetris(the_settings)
    the_main_window.show()

    # Unit test
    #for (key,sound) in the_main_window.sfx.items() :
        #print(key)
        #sound.play()
        #QTest.qWait(500)

    the_app.exec_()
