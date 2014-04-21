#!/usr/bin/env python2.7

import curses
import time

import model
import controller

class Tile(object):
    def __init__(self):
        self.tile = dict()
        self.t

class View(object):
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.bf = model.Battlefield()

    def run(self):
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, 1, 7) # soldier team 1
        curses.init_pair(2, 4, 7) # soldier team 2
        curses.init_pair(3, 2, 0) # tree
        curses.init_pair(4, 3, 0) # grass

        self.stdscr.leaveok(0)

        self.winy, self.winx = self.stdscr.getmaxyx()
        self.running = True
        self.controller = controller.Controller(self.bf, self.stdscr)

        while self.running:
            self.draw()
            self.getInput()

        # cleanup
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def draw(self):
        for x in xrange(min(self.winx - 1, self.bf.w)):
            for y in xrange(min(self.winy - 1, self.bf.h)):
                terr = self.bf.terrain[x][y]
                sold = self.bf.soldierAt(x, y)
                if sold:
                    char = '@'
                    if sold.team == 0:
                        color = 1
                    else:
                        color = 2
                elif terr.tree:
                    char = 'T'
                    color = 3
                else:
                    char = '.'
                    color = 4
                self.stdscr.addch(y, x, char, curses.color_pair(color))

        self.stdscr.move(self.controller.state.cursorpos[1], self.controller.state.cursorpos[0])
        self.stdscr.refresh()

    def getInput(self):
        self.running = self.controller.getInput()

def main(stdscr):
    view = View(stdscr)
    view.run()

if __name__ == '__main__':
    curses.wrapper(main)

