#!/usr/bin/env python2.7

import curses
import time

import model
import controller

class Tile(object):
    def __init__(self):
        self.tile = dict()
        self.t

class Path(object):
    def __init__(self, bf, start, end):
        self.bf = bf
        self.start = start
        self.end = end
        self.path = self.bf.getPath(self.start, self.end)
        self.calcPathCost()

    def calcPathCost(self):
        path_cost = None
        if self.path:
            path_cost = [0]
            curr_path_cost = 0
            for n in self.path[1:]:
                curr_path_cost += self.bf.movementCost(n[0], n[1])
                path_cost.append(curr_path_cost)
            self.path = zip(self.path, path_cost)

    def getPath(self):
        return self.path

    def changeCoord(self, start, end):
        if start != self.start or end != self.end:
            self.start = start
            self.end = end
            self.path = self.bf.getPath(self.start, self.end)
            self.calcPathCost()

class View(object):
    infobarHeight = 8

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.bf = model.Battlefield()
        self.path = Path(self.bf, (0,0), (0,0))
        self.animDelay = 10

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
        curses.init_pair(5, 7, 0) # path with enough APs, selected soldier name
        curses.init_pair(6, 7, 1) # path without enough APs, unselected soldier name, bullet

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

    def drawTerrain(self):
        for x in xrange(min(self.winx - 1, self.bf.w)):
            for y in xrange(min(self.winy - 1 - View.infobarHeight, self.bf.h)):
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

    def drawInfobar(self):
        xpos = 0
        ypos = self.winy - 1 - View.infobarHeight
        currsold = self.bf.getCurrentSoldier()
        for sold in self.bf.soldiers:
            if sold.team == 0:
                if sold == currsold:
                    color = 5
                else:
                    color = 6
                self.stdscr.addstr(ypos, xpos, sold.getName(), curses.color_pair(color))
                self.stdscr.addstr(ypos + 1, xpos, '%-4d' % sold.getAPs(), curses.color_pair(color))
                xpos += 20

        xpos = 0
        if currsold.team == 0:
            if self.path.getPath():
                neededAPs = self.path.getPath()[-1][1]
                infostr = '%-4d' % neededAPs
            else:
                infostr = '    '
            self.stdscr.addstr(ypos + 2, xpos, infostr)

            if self.controller.state.aiming != 0:
                dist = self.bf.distance(currsold.getPosition(), self.controller.state.cursorpos)
                shootstr = 'Shooting. Aim: %d, distance: %d     ' % (self.controller.state.aiming, dist)
            else:
                shootstr = ' ' * 40
            self.stdscr.addstr(ypos + 3, xpos, shootstr)

    def drawPath(self):
        if self.bf.shootLine:
            return
        soldier = self.bf.getCurrentSoldier()
        if soldier.team != 0:
            return
        self.path.changeCoord(soldier.getPosition(), self.controller.state.cursorpos)
        if self.path.getPath():
            for p in self.path.getPath()[1:]:
                if p[1] < soldier.getAPs():
                    color = 5
                else:
                    color = 6
                self.stdscr.addch(p[0][1], p[0][0], 'x', curses.color_pair(color))

    def drawBullet(self):
        sl = self.bf.shootLine
        if not sl:
            return
        bt = sl[0][0]
        self.stdscr.addch(bt[1], bt[0], '.', curses.color_pair(6))

    def draw(self):
        self.drawTerrain()
        self.drawPath()
        self.drawBullet()
        self.drawInfobar()
        self.stdscr.move(self.controller.state.cursorpos[1], self.controller.state.cursorpos[0])
        self.stdscr.refresh()

    def getInput(self):
        soldier = self.bf.getCurrentSoldier()
        if soldier.team != 0:
            self.bf.updateAI()
        else:
            if self.bf.moveTarget or self.bf.shootLine:
                if self.animDelay > 0:
                    self.animDelay -= 1
                else:
                    self.animDelay = 10
                    if self.bf.moveTarget:
                        self.bf.updateMovement()
                    elif self.bf.shootLine:
                        self.bf.updateShot()
            else:
                self.running = self.controller.getInput()

def main(stdscr):
    view = View(stdscr)
    view.run()

if __name__ == '__main__':
    curses.wrapper(main)

