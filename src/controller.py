#!/usr/bin/env python2.7

import curses

import model

class ControllerState(object):
    def __init__(self, bf):
        self.cursorpos = 5, 5
        self.bf = bf
        self.movementRequested = False
        self.aiming = 0
        self.message = ''
        self.pressedKeyCode = 0
        self.warp = False
        self.showInventory = False
        self.running = True

    def moveCursor(self, x, y):
        self.message = ''
        self.stopAim()
        if self.warp:
            x = x * 10
            y = y * 10
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
            if self.bf.shoot(self.cursorpos[0], self.cursorpos[1], self.aiming):
                self.message = 'Shot!'
            else:
                self.message = 'Not enough APs to shoot.'
        self.stopAim()

class Controller(model.BattlefieldListener):
    def __init__(self, bf):
        self.bf = bf
        self.state = ControllerState(self.bf)
        self.bf.addListener(self)

    def currentSoldierChanged(self):
        soldier = self.bf.getCurrentSoldier()
        if soldier and soldier.team == 0:
            self.state.cursorpos = soldier.getPosition()

    def getInput(self):
        while True:
            c = (yield)
            self.state.pressedKeyCode = c
            if c == ord('q'):
                self.state.running = False

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
            elif c == 53:
                self.state.warp = not self.state.warp
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
                self.state.message = 'Controlling %s.' % self.bf.getCurrentSoldier().getName()
            elif c == curses.KEY_F3:
                self.state.stopAim()
                self.bf.setCurrentSoldier(0, 1)
                self.state.message = 'Controlling %s.' % self.bf.getCurrentSoldier().getName()
            elif c == curses.KEY_F4:
                self.state.stopAim()
                self.bf.setCurrentSoldier(0, 2)
                self.state.message = 'Controlling %s.' % self.bf.getCurrentSoldier().getName()
            elif c == curses.KEY_F5:
                self.state.stopAim()
                self.bf.setCurrentSoldier(0, 3)
                self.state.message = 'Controlling %s.' % self.bf.getCurrentSoldier().getName()
            elif c == ord(' '):
                self.state.stopAim()
                self.state.message = 'End of turn...'
                self.bf.endTurn()
                while True:
                    c = (yield)
                    soldier = self.bf.getCurrentSoldier()
                    if soldier and soldier.team == 0:
                        self.state.cursorpos = soldier.getPosition()
                        break
            elif c == ord('f'):
                self.state.aim()
            elif c == ord('F'):
                self.state.shoot()

            elif c == ord('i') or c == ord('d'):
                self.state.dropping = c == ord('d')
                self.state.showInventory = True
                while True:
                    c = (yield)
                    if not self.state.dropping and (c == ord('i') or c == ord('q') or c == ord(' ') or c == ord('\n')):
                        self.state.showInventory = False
                        break
                    elif self.state.dropping:
                        if c == ord(' ') or c == ord('\n'):
                            self.state.showInventory = False
                            break
                        else:
                            soldier = self.bf.getCurrentSoldier()
                            it = soldier.removeFromInventory(chr(c))
                            if it:
                                self.bf.addItem(it, soldier.getPosition())
                                self.state.showInventory = False
                                self.state.message = 'Dropped %s.' % it.getName()
                                break

            elif c == ord(','):
                soldier = self.bf.getCurrentSoldier()
                pos = soldier.getPosition()
                items = self.bf.itemsAt(pos[0], pos[1])
                if items:
                    item = items[0]
                    char = soldier.pickup(item)
                    if char:
                        self.bf.removeItem(item, pos)
                        self.state.message = '%c - %s.' % (char, item.getName())

