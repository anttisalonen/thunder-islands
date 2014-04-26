#!/usr/bin/env python2.7

import curses
import time
import os
import argparse

import model
import controller

class Path(object):
    maxDistanceToPath = 20
    def __init__(self, bf, start, end):
        self.bf = bf
        self.start = start
        self.end = end
        if self.bf.distance(self.start, self.end) < Path.maxDistanceToPath:
            self.path = self.bf.getPath(self.start, self.end)
            self.calcPathCost()
        else:
            self.path = None

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
            if self.bf.distance(self.start, self.end) < Path.maxDistanceToPath:
                self.path = self.bf.getPath(self.start, self.end)
                self.calcPathCost()
            else:
                self.path = None

class View(object):
    infobarHeight = 8
    statusbarHeight = 2
    leftPanelWidth = 14
    rightPanelWidth = 14
    animDelay = 3

    def __init__(self, stdscr, seed):
        self.stdscr = stdscr
        self.bf = model.Battlefield(seed)
        self.path = Path(self.bf, (0,0), (0,0))
        self.animDelay = View.animDelay
        self.hitPoint = None
        self.screenOffset = 0, 0

    def run(self):
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)
        curses.start_color()
        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)
        curses.init_pair(1, 1, 7) # soldier team 1
        curses.init_pair(2, 4, 7) # soldier team 2
        curses.init_pair(3, 2, 0) # tree
        curses.init_pair(4, 3, 0) # grass
        curses.init_pair(5, 7, 0) # path with enough APs, selected soldier name
        curses.init_pair(6, 7, 1) # path without enough APs, unselected soldier name, bullet
        curses.init_pair(7, 7, 3) # bullet hit
        curses.init_pair(8, 4, 0) # water
        curses.init_pair(9, 6, 0) # wall
        curses.init_pair(10, 7, 0) # floor

        self.stdscr.leaveok(0)

        self.winy, self.winx = self.stdscr.getmaxyx()
        self.running = True
        self.controller = controller.Controller(self.bf)

        g = self.controller.getInput()
        g.next()
        while self.running:
            self.draw()
            self.getInput(g)

        # cleanup
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def posOnScreen(self, pos):
        cpx, cpy = pos
        return cpx - self.screenOffset[0] + View.leftPanelWidth, cpy - self.screenOffset[1] + View.statusbarHeight

    def cursorPosOnScreen(self):
        return self.posOnScreen(self.controller.state.cursorpos)

    def drawTerrain(self):
        for x in xrange(self.screenOffset[0], min(self.winx - View.leftPanelWidth - View.rightPanelWidth + self.screenOffset[0], self.bf.w)):
            for y in xrange(self.screenOffset[1], min(self.winy - View.statusbarHeight - View.infobarHeight + self.screenOffset[1], self.bf.h)):
                terr = self.bf.terrain[x][y]
                sold = self.bf.soldierAt(x, y)
                items = self.bf.itemsAt(x, y)
                attr = 0
                if sold:
                    char = '@'
                    if sold.team == 0:
                        color = 1
                    else:
                        color = 2
                elif items:
                    item = items[0]
                    char, color, attr = self.itemDisplay(item)
                    self.addch((x, y), char, color, attr)
                elif terr.overlay == model.Tile.Overlay.Tree:
                    char = 'T'
                    color = 3
                elif terr.overlay == model.Tile.Overlay.Wall:
                    char = 'w'
                    color = 9
                    attr = curses.A_BOLD
                elif terr.base == model.Tile.Base.Water:
                    char = '~'
                    color = 8
                elif terr.base == model.Tile.Base.Grass:
                    char = '.'
                    color = 4
                elif terr.base == model.Tile.Base.Grass:
                    char = '.'
                    color = 4
                elif terr.base == model.Tile.Base.Floor:
                    char = '.'
                    color = 10
                elif terr.base == model.Tile.Base.Pathway:
                    char = '+'
                    color = 122
                else:
                    assert False, 'Can\'t display base %d, overlay %d' % (terr.base, terr.overlay)
                self.addch((x, y), char, color, attr)

    @staticmethod
    def itemDisplay(item):
        if isinstance(item, model.Weapon):
            char = '&'
            if item.wtype == model.WeaponType.Magnum357:
                return char, 245, 0
            elif item.wtype == model.WeaponType.RifleG12:
                return char, 161, 0
            assert False
        elif isinstance(item, model.Clip):
            char = 'c'
            if item.btype == model.WeaponType.Magnum357:
                return char, 245, 0
            elif item.btype == model.WeaponType.RifleG12:
                return char, 161, 0
            assert False
        assert False, '%s' % item

    def drawHeader(self):
        if self.controller.state.message:
            msg = self.controller.state.message[:79]
        else:
            msg = ''
        self.stdscr.addstr(0, 0, '%-80s' % msg)

    def drawSidePanels(self):
        xpos = 0
        ypos = View.statusbarHeight
        currsold = self.bf.getCurrentSoldier()
        ind = 0
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
                    assert View.leftPanelWidth == View.rightPanelWidth
                    self.stdscr.addstr(ypos + 1, xpos, ' ' * View.leftPanelWidth)
                    self.stdscr.addstr(ypos + 2, xpos, ' ' * View.leftPanelWidth)
                ypos += 3
                ind += 1
                if ind == 2:
                    xpos = self.winx - View.rightPanelWidth - 1
                    ypos = View.statusbarHeight

    def drawInfobar(self):
        xpos = 0
        ypos = self.winy - View.infobarHeight
        currsold = self.bf.getCurrentSoldier()
        if currsold.team == 0:
            if self.path.getPath():
                neededAPs = self.path.getPath()[-1][1]
                infostr = 'Needed APs: %-4d' % neededAPs
            else:
                infostr = '                    '
            self.stdscr.addstr(ypos + 0, xpos, infostr)

            if self.controller.state.aiming != 0:
                dist = self.bf.distance(currsold.getPosition(), self.controller.state.cursorpos)
                shootstr = 'Shooting. Aim: %d, distance: %d     ' % (self.controller.state.aiming, dist)
            else:
                shootstr = ' ' * 40
            self.stdscr.addstr(ypos + 1, xpos, shootstr)
            coordTuple = (self.controller.state.cursorpos[0], self.controller.state.cursorpos[1], self.screenOffset[0], self.screenOffset[1])
            self.stdscr.addstr(ypos + 2, xpos, '(%d, %d) (%d, %d)       ' % coordTuple)
            self.stdscr.addstr(ypos + 3, xpos, '%d  ' % self.controller.state.pressedKeyCode)

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
                self.addch(p[0], 'x', color)

    def drawOverlay(self):
        soldier = self.bf.getCurrentSoldier()
        row = 5
        if self.controller.state.showInventory:
            if not soldier.getInventory():
                msg = 'Inventory is empty.'
                self.stdscr.addstr(row, 30, '%-30s' % msg)
            else:
                for k, v in sorted(soldier.getInventory().items()):
                    msg = '%c  %s%s' % (k, v.getName(), ' (wielded)' if k == soldier.wieldedItem else '')
                    self.stdscr.addstr(row, 30, '%-30s' % msg)
                    row += 1

    def addch(self, pos, ch, color, attr = 0):
        pos = self.posOnScreen(pos)
        if pos[1] < self.winy - View.infobarHeight and \
                pos[1] >= View.statusbarHeight and \
                pos[0] < self.winx - View.rightPanelWidth and \
                pos[0] >= View.leftPanelWidth:
            self.stdscr.addch(pos[1], pos[0], ch, curses.color_pair(color) | attr)

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
        self.drawSidePanels()
        self.drawInfobar()
        self.drawHeader()
        self.drawOverlay()
        cp = self.cursorPosOnScreen()
        self.stdscr.move(cp[1], cp[0])
        self.stdscr.refresh()

    def getInput(self, g):
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
                    self.animDelay = View.animDelay
                    if self.bf.moveTarget:
                        if self.bf.updateMovement():
                            self.controller.state.message = 'No more APs to move.'
                    elif self.bf.shootLine:
                        self.hitPoint = self.bf.updateShot()
                        if self.hitPoint:
                            soldierHit = self.hitPoint[2]
                            if soldierHit:
                                self.controller.state.message = 'Hit %s!' % soldierHit.getName()
            else:
                curses.curs_set(1)
                c = self.stdscr.getch()
                g.send(c)
                self.running = self.controller.state.running
                self.checkScreenScroll()

    def checkScreenScroll(self):
        cp = self.controller.state.cursorpos
        sx = max(0, self.screenOffset[0], cp[0] - self.winx + View.leftPanelWidth + 1 + View.rightPanelWidth)
        sx = min(cp[0], sx)
        sy = max(0, self.screenOffset[1], cp[1] - self.winy + View.statusbarHeight + 1 + View.infobarHeight)
        sy = min(cp[1], sy)
        self.screenOffset = sx, sy

def main(stdscr, seed):
    view = View(stdscr, seed)
    view.run()

if __name__ == '__main__':
    os.environ['TERM'] = 'xterm-256color'

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--seed', help='random seed', type=int)
    args = parser.parse_args()
    curses.wrapper(lambda stdscr: main(stdscr, args.seed))

