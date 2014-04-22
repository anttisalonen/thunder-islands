#!/usr/bin/env python2.7

import curses

import model

class ControllerState(object):
    def __init__(self, bf):
        self.cursorpos = 5, 5
        self.bf = bf
        self.freeCursor = False
        self.movementRequested = False
        self.aiming = 0
        self.message = ''

    def moveCursor(self, x, y):
        self.message = ''
        self.stopAim()
        nx = self.cursorpos[0] + x
        ny = self.cursorpos[1] + y
        nx = min(nx, self.bf.w - 1)
        nx = max(nx, 0)
        ny = min(ny, self.bf.h - 1)
        ny = max(ny, 0)
        self.cursorpos = nx, ny

    def aim(self):
        self.aiming += 1
        if self.aiming == 5:
            self.aiming = 0

    def stopAim(self):
        self.aiming = 0

    def shoot(self):
        if self.aiming != 0:
            self.bf.shoot(self.cursorpos[0], self.cursorpos[1], self.aiming)
            self.message = 'Shot!'
        self.stopAim()

class Controller(model.BattlefieldListener):
    def __init__(self, bf, stdscr):
        self.stdscr = stdscr
        self.bf = bf
        self.state = ControllerState(self.bf)
        self.bf.addListener(self)

    def currentSoldierChanged(self):
        soldier = self.bf.getCurrentSoldier()
        if soldier and soldier.team == 0:
            self.state.cursorpos = soldier.getPosition()
            self.state.freeCursor = True
        else:
            self.state.freeCursor = False

    def getInput(self):
        c = self.stdscr.getch()
        if c == ord('q'):
            return False

        if self.state.freeCursor:
            if c == curses.KEY_DOWN or c == 50:
                self.state.moveCursor(0, 1)
            elif c == curses.KEY_UP or c == 56:
                self.state.moveCursor(0, -1)
            elif c == curses.KEY_LEFT or c == 52:
                self.state.moveCursor(-1, 0)
            elif c == curses.KEY_RIGHT or c == 54:
                self.state.moveCursor(1, 0)
            elif c == 49:
                self.state.moveCursor(-1, 1)
            elif c == 51:
                self.state.moveCursor(1, 1)
            elif c == 55:
                self.state.moveCursor(-1, -1)
            elif c == 57:
                self.state.moveCursor(1, -1)
            elif c == 10 or c == 13 or c == curses.KEY_ENTER:
                self.state.stopAim()
                self.bf.moveTo(self.state.cursorpos[0], self.state.cursorpos[1])
            elif c == curses.KEY_F2:
                self.state.stopAim()
                self.bf.setCurrentSoldier(0, 0)
                self.state.message = 'Controlling %s' % self.bf.getCurrentSoldier().getName()
            elif c == curses.KEY_F3:
                self.state.stopAim()
                self.bf.setCurrentSoldier(0, 1)
                self.state.message = 'Controlling %s' % self.bf.getCurrentSoldier().getName()
            elif c == curses.KEY_F4:
                self.state.stopAim()
                self.bf.setCurrentSoldier(0, 2)
                self.state.message = 'Controlling %s' % self.bf.getCurrentSoldier().getName()
            elif c == curses.KEY_F5:
                self.state.stopAim()
                self.bf.setCurrentSoldier(0, 3)
                self.state.message = 'Controlling %s' % self.bf.getCurrentSoldier().getName()
            elif c == ord(' '):
                self.state.stopAim()
                self.state.message = 'End of turn'
                self.bf.endTurn()
            elif c == ord('f'):
                self.state.aim()
            elif c == ord('F'):
                self.state.shoot()
        return True

