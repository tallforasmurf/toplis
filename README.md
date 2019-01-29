### toplis
Variations on tetris, especially aiming at a "topless" one where you can't fail, it just keeps compressing unfilled rows down "underfoot" so there's always room for the next piece.
Initial inspiration was the PyQt5-based Tetris by Jan Bodnar, found at http://zetcode.com/gui/pyqt5/tetris/. (See also [github/janbodnar](https://github.com/janbodnar) but he doesn't keep much there.)

## standard.py
This is basically Jan Bodnar's PyQt5 Tetris, rewritten. It is a minimal, but playable, Tetris.

I rewrote it because that was the fastest way to understand it. The original is a nice program, but not over-supplied with commentary. And it's quite subtle in some ways. My rewrite differs at these points:
* Nomenclature and logic changed to match the [Official Tetris Guidelines](http://tetris.wikia.com/wiki/Tetris_Guideline), in particular,

* standardized colors
* use of a "7-bag randomizer" instead of raw random pieces
* Added copious commentary
* Converted several loop-nests into tuple comprehensions
* Some small changes to logic

## polished.py
This is the above program with many bells and whistles added:

* Start and Pause buttons in the main window
* Music and sounds implemented
* timer interval shortens as number of filled lines goes up
* remembers highest score
* "wall kick" feature
* ability to "hold" a piece
* preview display of the five upcoming pieces

## toplis.py

Will be the above with the infinite height added so you can build up many unfilled lines and still recover.
