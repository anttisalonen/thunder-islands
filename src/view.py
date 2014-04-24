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
        self.hitPoint = None

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
        curses.init_pair(7, 7, 3) # bullet hit

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

    def posOnScreen(self, pos):
        cpx, cpy = pos
        return cpx, cpy + 1

    def cursorPosOnScreen(self):
        return self.posOnScreen(self.controller.state.cursorpos)

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
                self.addch((x, y), char, color)

    def drawHeader(self):
        if self.controller.state.message:
            msg = self.controller.state.message[:79]
        else:
            msg = ''
        self.stdscr.addstr(0, 0, '%-80s' % msg)

    def drawInfobar(self):
        xpos = 0
        ypos = self.winy - View.infobarHeight
        currsold = self.bf.getCurrentSoldier()
        for sold in self.bf.soldiers:
            if sold.team == 0:
                if sold == currsold:
                    color = 5
                else:
                    color = 6
                self.stdscr.addstr(ypos, xpos, sold.getName(), curses.color_pair(color))
                if sold.alive():
                    self.stdscr.addstr(ypos + 1, xpos, 'APs:    %-4d' % sold.getAPs(), curses.color_pair(color))
                    self.stdscr.addstr(ypos + 2, xpos, 'Health: %-4d' % sold.getHealth(), curses.color_pair(color))
                else:
                    self.stdscr.addstr(ypos + 1, xpos, '                ')
                    self.stdscr.addstr(ypos + 2, xpos, '                ')
                xpos += 20

        yoffset = 3
        xpos = 0
        if currsold.team == 0:
            if self.path.getPath():
                neededAPs = self.path.getPath()[-1][1]
                infostr = 'Needed APs: %-4d' % neededAPs
            else:
                infostr = '                    '
            self.stdscr.addstr(ypos + yoffset + 0, xpos, infostr)

            if self.controller.state.aiming != 0:
                dist = self.bf.distance(currsold.getPosition(), self.controller.state.cursorpos)
                shootstr = 'Shooting. Aim: %d, distance: %d     ' % (self.controller.state.aiming, dist)
            else:
                shootstr = ' ' * 40
            self.stdscr.addstr(ypos + yoffset + 1, xpos, shootstr)

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
                pos = self.posOnScreen(p[0])
                self.addch(p[0], 'x', color)

    def addch(self, pos, ch, color):
        pos = self.posOnScreen(pos)
        self.stdscr.addch(pos[1], pos[0], ch, curses.color_pair(color))

    def drawBullet(self):
        if self.hitPoint:
            self.addch(self.hitPoint[0:2], '*', 7)
            return
        sl = self.bf.shootLine
        if not sl:
            return
        bt = sl[0][0]
        self.addch(bt, '.', 6)

    def draw(self):
        self.drawTerrain()
        self.drawPath()
        self.drawBullet()
        self.drawInfobar()
        self.drawHeader()
        cp = self.cursorPosOnScreen()
        self.stdscr.move(cp[1], cp[0])
        self.stdscr.refresh()

    def getInput(self):
        soldier = self.bf.getCurrentSoldier()
        if soldier.team != 0:
            self.bf.updateAI()
        else:
            if self.bf.moveTarget or self.bf.shootLine or self.hitPoint:
                curses.curs_set(0)
                if self.animDelay > 0:
                    self.animDelay -= 1
                else:
                    self.hitPoint = None
                    self.animDelay = 10
                    if self.bf.moveTarget:
                        if self.bf.updateMovement():
                            self.controller.state.message = 'No more APs to move.'
                    elif self.bf.shootLine:
                        self.hitPoint = self.bf.updateShot()
                        if self.hitPoint:
                            soldierHit = self.hitPoint[2]
                            self.controller.state.message = 'Hit %s!' % soldierHit.getName()
            else:
                curses.curs_set(1)
                self.running = self.controller.getInput()

def main(stdscr):
    view = View(stdscr)
    view.run()

if __name__ == '__main__':
    curses.wrapper(main)

