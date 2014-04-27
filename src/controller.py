#!/usr/bin/env python2.7

import curses
import string

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
        self.showPickupMenu = False
        self.running = True
        self.currentSoldierIndex = 0
        self.soldierCursorPos = dict()
        self.center = False
        self.droppedItem = None

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

    def turnEnded(self, currentTeam):
        if currentTeam == 0:
            self.bf.setCurrentSoldier(0, self.state.currentSoldierIndex)

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
                self.state.soldierCursorPos[self.state.currentSoldierIndex] = self.state.cursorpos
            elif c >= curses.KEY_F2 and c <= curses.KEY_F5:
                self.state.stopAim()
                self.state.currentSoldierIndex = c - curses.KEY_F2
                self.bf.setCurrentSoldier(0, self.state.currentSoldierIndex)
                try:
                    self.state.cursorpos = self.state.soldierCursorPos[self.state.currentSoldierIndex]
                except KeyError:
                    self.state.cursorpos = self.bf.getCurrentSoldier().getPosition()
                self.state.message = 'Controlling %s.' % self.bf.getCurrentSoldier().getName()
            elif c == ord(' '):
                self.state.stopAim()
                self.state.message = 'End of turn...'
                self.bf.endTurn()
            elif c == ord('f'):
                self.state.aim()
            elif c == ord('F'):
                self.state.shoot()

            elif c == ord('i') or c == ord('d'):
                self.state.dropping = c == ord('d')
                self.state.showInventory = True
                while True:
                    c = (yield)
                    if not self.state.dropping and (c == ord('i') or c == ord('q') or self.exitItemMenu(c)):
                        self.state.showInventory = False
                        break
                    elif self.state.dropping:
                        if self.exitItemMenu(c):
                            break
                        else:
                            soldier = self.bf.getCurrentSoldier()
                            it = soldier.removeFromInventory(chr(c))
                            if it:
                                self.bf.addItem(it, soldier.getPosition())
                                self.state.message = 'Dropped %s.' % it.getName()
                                self.state.droppedItem = it
                                break
                self.state.showInventory = False

            elif c == ord(','):
                soldier = self.bf.getCurrentSoldier()
                if soldier.hasAPsToPickup():
                    pos = soldier.getPosition()
                    items = self.bf.itemsAt(pos[0], pos[1])
                    if items:
                        if len(items) > 1:
                            self.state.message = 'Select item to pick up.'
                            self.state.showPickupMenu = True
                            self.state.itemMenu = dict(zip(string.ascii_lowercase, items))
                            c = (yield)
                            try:
                                item = self.state.itemMenu[chr(c)]
                            except KeyError:
                                pass
                            else:
                                self.pickup(item)
                            self.state.showPickupMenu = False
                        else:
                            self.pickup(items[0])
                else:
                    self.state.message = 'Not enough APs to pick up an item.'

            elif c == ord('c') or c == ord('z'):
                self.state.center = True

    def pickup(self, item):
        soldier = self.bf.getCurrentSoldier()
        pos = soldier.getPosition()
        char = soldier.pickup(item)
        if char:
            self.bf.removeItem(item, pos)
            self.state.message = '%c - %s.' % (char, item.getName())

    def exitItemMenu(self, c):
        return c == ord(' ') or c == ord('\n')


