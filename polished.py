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
    QMainWindow,
    QMessageBox,
    QSlider,
    QToolBar
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
        Game frame

A frame that contains the playing field, a display of the upcoming T_mo,
and a display of the current count of lines and current score.

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
        # set up the Play icon and connect it.
        self.play_action = self.toolbar.addAction(
            QIcon(QPixmap(':/icon_play.png')),'Play')
        self.play_action.triggered.connect(self.playAction)
        # set up the Pause icon and connect it.
        self.pause_action = self.toolbar.addAction(
            QIcon(QPixmap(':/icon_pause.png')),'Pause')
        self.pause_action.triggered.connect(self.pauseAction)
        # set up the Restart icon and connect it
        self.reset_action = self.toolbar.addAction(
            QIcon(QPixmap(':/icon_reset.png')),'Reset')
        self.reset_action.triggered.connect(self.resetAction)
        # set the game buttons to enabled or disabled states
        self.enableButtons()
        # Insert the Mute button and the volume slider after a separator
        self.toolbar.addSeparator()
        self.mute_action = self.toolbar.addAction(
            QIcon(QPixmap(':/icon_mute.png')),'Mute')
        self.mute_action.triggered.connect(
            lambda : self.volumeAction(0)
            )
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setTickPosition(QSlider.TicksBothSides)
        self.volume_slider.setRange(0,99)
        self.volume_slider.setTickInterval(25)
        self.volume_slider.setMaximumWidth(250)
        self.volume_slider.setMinimumWidth(50)
        self.volume_slider.valueChanged.connect(self.volumeAction)
        self.volume_slider.setValue(
            self.settings.value("volume",50) )
        self.toolbar.addWidget(self.volume_slider)


    '''
    These slots receive clicks on toolbar icons - probably will
    be replaced with calls direct into game object.
    '''
    def enableButtons(self):
        self.pause_action.setEnabled(
            self.game.started and not self.game.paused )
        self.play_action.setEnabled(
            not(self.game.started) or self.game.paused )
        self.reset_action.setEnabled(
            self.game.started )
    def playAction(self, toggled:bool):
        print('Play')
        if self.game.paused :
            self.game.pause() # toggle pause to off
        else :
            self.game.start()
        self.enableButtons()

    def pauseAction(self, toggled:bool):
        print('Pause')
        self.game.pause()
        self.enableButtons()
    def resetAction(self, toggled:bool):
        print('Reset')
        ans = QMessageBox.question(
            self, 'Reset clicked', 'Reset the game? State will be lost.' )
        if ans == QMessageBox.Ok or ans == QMessageBox.Yes :
            self.game.clear()
            self.game.start()
    '''
    This slot is called from the valueChanged signal of the volume slider,
    or directly by on the triggered action of the mute button.
    '''
    def volumeAction(self, slider_value:int ) :
        print('volume {}'.format(slider_value))

    '''
    Reimplement QWindow.closeEvent to save our geometry
    and the current high score.
    '''
    def closeEvent(self, event:QEvent):
        self.settings.clear()
        self.settings.setValue("windowSize",self.size())
        self.settings.setValue("windowPosition",self.pos())
        self.settings.setValue("highScore",self.high_score)
        self.settings.setValue("volume",self.volume_slider.value())



'''
Command-line execution.
TODO: decide on command parameters to support if any
TODO: define command parameters with argparse
TODO: implement QSettings storage for high score
TODO: implement QSettings storage for closing geometry

currently this is basically unit test
'''

if __name__ == '__main__' :
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

    the_main_window = Tetris(the_settings)
    the_main_window.show()
    for (key,sound) in the_main_window.sfx.items() :
        print(key)
        sound.play()
        QTest.qWait(500)

    the_app.exec_()
