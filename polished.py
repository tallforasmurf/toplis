'''
        Tetris implemented in PyQt

This is an expansion of the simple game (see standard.py) using the same
techniques, but adding full game features such as wall-kick, next-piece
preview, score records, and sound. In general game play conforms to the
Tetris Guideline for play as described at
    http://tetris.wikia.com/wiki/Random_Generator

The GUI structure is based on a QMainWindow. The provided Tool Bar offers
buttons for Pause, Restart, Sound, Music, and for a display of high scores.

The status line shows the game state, either paused or count of completed
lines.

The central widget is a QFrame which implements the game; it is in effect the
"controller" in an MVC design. The Game contains a Board composed of cells in
22 rows and 10 columns (both "model" and "view"). To its right is a small 4x4
Board showing the next piece to come.

'''

from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
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
    QSettings,
    QSize,
    pyqtSignal
    )
from PyQt5.QtGui import (
    QColor,
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
We begin by defining the Tetronimo, the basic game piece.

Name the seven Tetronimoes via an IntEnum. 'O', 'I', 'T' and so forth are the
standardized names for the shapes.

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
Assign standardized colors for the Tetronimoes, as specified in the Tetris
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
Assign each Tetronimoe its shape and initial orientation.

Per the guidelines, quote,
    "The playfield is ... 10 by 20 ..."
    "The tetriminoes spawn horizontally with J, L and T spawning flat-side first."
    "The I and O spawn in the middle columns
     The rest spawn in the left-middle columns"

As I interpret that, if the columns are numbered 0-9, the O spawns in columns
4, 5, and the I in columns 3, 4, 5, 6. The others (which are all 3 squares
wide when horizontal) spawn in columns 3, 4, 5.

The following design is due to Jan Bodnar (see URL in standard.py). Each
Tetronimo is described by a list of four (x,y) tuples that specify four cells
centered in an x-y coordinate plane. The initial values specify the initial
(spawn) rotation of a Tetronimo, where (x=0,y=0) corresponds to column 4 row
20.

For example the Z is:
                (-1,1)(0,1)
                      (0,0) (1,0)
while the L is:
                            (1,1)
                (-1,0)(0,0) (1,0)

This design has the very nice property that rotation is easy. To rotate a
shape left, replace the tuples of the original shape with the tuple
comprehension,

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
Define the class of Tetronimo game pieces, T_mo. A game piece knows its shape
name and color, and its current shape in terms of a tuple of the four (x,y)
values of each of its cells, initialized as in T_Shapes above.

A T_mo can rotate, but note that the rotate_left() and rotate_right() methods
do NOT modify shape of the "self" T_mo. They return a NEW T_mo intended to
replace this one. This is done so that the game can test a rotation. If the
new, rotated T_mo is legal, it will replace the old; but if it it collides
with something, the original T_mo is left unchanged.

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
    we cannot type-declare these methods as "-> T_mo" because when these
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
This global instance of T_mo is the only one of type N. It is referenced from
any unoccupied board cell, giving empty cells their color.
'''
NO_T_mo = T_mo( T_ShapeNames.N )

'''
        Board

The Board object displays as an array of square cells. The number of rows and
columns are initialization parameters. Each cell consists of a reference to a
T_mo; the color of that T_mo is the color of the cell. Empty cells all refer
to the global NO_T_mo, and so have a light gray color.

The cells are drawn during a paint event, and the paintEvent() method and its
subroutines are the bulk of the Board logic.

The Board keeps a reference to a "current" T_mo. On the main board this is
the T_mo that the user is controlling. During a paintEvent, the current T_mo
is drawn separately, after the other cells.

The Board also provides the test() method, which tests the four cells of the
current T_mo against the existing cells and the Board margins. It returns one
of three values,

  * Board.OK when the cells of the current T_mo do not overlap a colored
    cell and do not extend outside the board.

  * Board.TOUCH when a cell of the current T_mo overlaps a cell that is not
    empty. (This is tested before the following tests.)

  * Board.LEFT when a cell of the current T_mo would fall outside the left
    board margin.

  * Board.RIGHT when it would fall outside the right margin.

Finally the Board provides the settle() method, which merges the current T_mo
into the cells of the board, and then looks for completed lines. If any lines
are now complete, they are deleted from the display and empty lines are added
at the top. The number of deleted lines is returned.

In order to ensure that all board cells are drawn as squares, the aspect
ratio of the board must be preserved during a resize event. Supposedly this
can be done by implementing the hasHeightForWidth and heightForWidth
methods but in fact those are never called during a resize. What does work is
the method described here:

https://stackoverflow.com/questions/8211982/qt-resizing-a-qlabel-containing-a-qpixmap-while-keeping-its-aspect-ratio

which is, during a resizeEvent, to call setContentsMargins() to set new margins
which force the resized height and width into the proper ratio.

'''
class Board(QFrame):
    OK = 0
    TOUCH = 1
    LEFT = 2
    RIGHT = 3
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
        grow. Note any growth will be preceded by a resize event, and see
        resizeEvent() below for how that is handled to maintain square cells.
        '''
        self.setMinimumHeight(int(10*rows))
        self.setMinimumWidth(int(10*columns))
        sp = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setSizePolicy(sp)
        '''
        The board contents is rows*columns cells, each referring to a T_mo.
        '''
        self.size = rows*columns
        self.clear() # populate the board with empty cells
        '''
        Slots to hold info about the current piece
        '''
        self._current = NO_T_mo # type: T_mo
        self._col = 0
        self._row = 0

    def clear(self):
        self.cells = [NO_T_mo]*self.size
        self.update( self.contentsRect() ) # force a paint event

    '''
    Place a T_mo at a certain column and row of the board.

    The positions of the 4 cells of the T_mo will be painted on actual board
    locations by adding col & row to the T_mo.coords tuple.

    This method is not called unless our test() method has returned OK for
    this T_mo at these coordinates.
    '''

    def current(self, piece:T_mo, col:int, row:int ):
        self._current = piece
        self._col = col
        self._row = row

    '''
    A paint event occurs when the Qt app thinks this QFrame should be
    updated. The event handler is responsible for drawing all the shapes in
    the contents rectangle of this widget. The contents margins that may be
    set during a resize event to maintain the aspect ratio, are not painted
    here. They are painted by the containing widget.
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
                                self.cells[v*self.cols + h]
                                )

        if self._current is not NO_T_mo:
            '''
            Draw the active tetronimo at its given location.
            '''
            for i in range(4):
                x = self._col + self._current.x(i)
                y = self._row + self._current.y(i)
                self.drawCell(painter,
                                rect.left() + x * self.cell_width,
                                rect.top() + (self.rows - y - 1) * self.cell_height,
                                self.current
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
        Game frame

A frame that contains the playing field (a Board), a display of the upcoming
T_mo (also a Board), a display of the current count of lines and current
score.

The logic in this frame implements the rules of the game, responding
appropriately to keystrokes and timer events to move the current piece
and update the board when the current piece stops moving.

TODO:
    initialize the UI
    implement the timer
    implement keystrokes
    implement piece movement
    implement signal to parent on game over
    implement signals to parent for SFX

'''

class Game(QFrame):
    def __init__(self, parent):
        super().__init__()
        self.board = Board(self,22,10)
        hb = QHBoxLayout()
        hb.addWidget(self.board,2)
        self.setLayout(hb)
        self.clear()

    def start(self):
        self.started = True
        self.ended = False
        print('started')

    def pause(self):
        self.paused = not self.paused
        print('paused {}'.format(self.paused))

    def clear(self):
        print('cleared')
        self.board.clear()
        self.started = False
        self.paused = False
        self.ended = True

'''
        Main Window

Hosts the Game object.
Provides a Toolbar with Pause and Restart buttons.
Displays high scores
Implements music including volume and on/off
Records high scores and current geometry in settings on shutdown.

'''

class Tetris(QMainWindow):

    def __init__(self, settings:QSettings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle('Tetris')
        '''
        Recover the main window geometry from settings, and the previous high
        score.
        TODO: decide where high score display goes and initialize it.
        '''
        self.move(self.settings.value("windowPosition", QPoint(50,50)))
        self.resize(self.settings.value("windowSize",QSize(500, 500)))
        self.high_score = self.settings.value("highScore",0)
        '''
        Create sound effect objects for each of the .wav files loaded in the
        resources module: move, rotate, drop (manual), settle, line. Load them into
        a dict so they can be treated as a unit.

        Each QSoundEffect loads its file, then generates the sound with low
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
        Create the game and make it the central widget.
        '''
        self.game = Game(self)
        self.setCentralWidget(self.game)

        '''
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
    * Reset is enabled if the game running.
    '''
    def enableButtons(self):
        self.pause_action.setEnabled(
            self.game.started and not self.game.paused )
        self.play_action.setEnabled(
            not(self.game.started) or self.game.paused )
        self.reset_action.setEnabled(
            self.game.started )

    '''
    Slots to receive clicks on the control buttons.

    Play button: because of enableButtons, the game state is either
    not-started, or paused.
    '''
    def playAction(self, toggled:bool):
        if self.game.paused :
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
    .setVolume() method wants a real, where the slider value is an int.
    '''
    def volumeAction(self, slider_value:int ) :
        for sfx in self.sfx.values() :
            sfx.setVolume( slider_value/100.0 )
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

    When the state is now on, save the present volume slider value and set
    the volume to zero. When the state is now off, reset the volume slider to
    the saved value.
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
    '''
    def closeEvent(self, event:QEvent):
        self.settings.clear()
        self.settings.setValue("windowSize",self.size())
        self.settings.setValue("windowPosition",self.pos())
        self.settings.setValue("highScore",self.high_score)
        self.settings.setValue("volume",self.volume_slider.value())
        self.settings.setValue("mutestate",self.mute_action.isChecked())
        self.settings.setValue("mutedvol",self.muted_volume)



'''
Command-line execution.
TODO: decide on command parameters to support if any
TODO: define command parameters with argparse
TODO: implement QSettings storage for high score
TODO: implement QSettings storage for closing geometry

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
    the settings object for use starting up and shutting down.
    Then display it and begin execution.
    '''
    the_main_window = Tetris(the_settings)
    the_main_window.show()

    # Unit test
    for (key,sound) in the_main_window.sfx.items() :
        print(key)
        sound.play()
        QTest.qWait(500)

    the_app.exec_()
