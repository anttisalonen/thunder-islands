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
        self.currentSoldier = None
        self.soldierCursorPos = dict()
        self.center = False
        self.droppedItem = None
        self.travelling = 0

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
        self.mySoldiers = self.bf.soldiersInTeam(0)
        try:
            self.state.currentSoldier = self.mySoldiers[0]
        except IndexError:
            self.state.currentSoldier = None

    def turnEnded(self, currentTeam):
        if self.state.currentSoldier and currentTeam == 0:
            self.bf.setCurrentSoldier(self.state.currentSoldier)

    def getInput(self):
        while True:
            c = (yield)
            try:
                cc = chr(c)
            except ValueError:
                cc = None
            self.state.pressedKeyCode = c
            if cc == 'q':
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
                if self.state.currentSoldier:
                    self.state.stopAim()
                    self.bf.moveTo(self.state.cursorpos[0], self.state.cursorpos[1])
                    self.state.soldierCursorPos[self.state.currentSoldier] = self.state.cursorpos
            elif c >= curses.KEY_F2 and c <= curses.KEY_F5:
                self.state.stopAim()
                soldIndex = c - curses.KEY_F2
                try:
                    sold = self.mySoldiers[soldIndex]
                except IndexError:
                    pass
                else:
                    if sold.alive():
                        self.bf.setCurrentSoldier(sold)
                        self.state.currentSoldier = sold
                    try:
                        self.state.cursorpos = self.state.soldierCursorPos[self.state.currentSoldier]
                    except KeyError:
                        self.state.cursorpos = self.bf.getCurrentSoldier().getPosition()
                    self.state.message = 'Controlling %s.' % self.bf.getCurrentSoldier().getName()
            elif cc == ' ':
                self.state.stopAim()
                self.state.message = 'End of turn...'
                if self.bf.endTurn() and not self.bf.isFriendly():
                    self.state.message = 'Sector won!'
            elif cc == 'f':
                self.state.aim()
            elif cc == 'F':
                self.state.shoot()

            elif cc == 'i' or cc == 'd':
                self.state.dropping = cc == 'd'
                self.state.showInventory = True
                while True:
                    c = (yield)
                    if not self.state.dropping and (cc == 'i' or cc == 'q' or self.exitItemMenu(cc)):
                        self.state.showInventory = False
                        break
                    elif self.state.dropping:
                        if self.exitItemMenu(cc):
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

            elif cc == ',':
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

            elif cc == 'c' or cc == 'z':
                self.state.center = True

            elif cc == 'h' or cc == 'j' or cc == 'k' or cc == 'l':
                if cc == 'h':
                    self.state.travelling = 1
                elif cc == 'j':
                    self.state.travelling = 2
                elif cc == 'k':
                    self.state.travelling = 3
                else:
                    self.state.travelling = 4

    def pickup(self, item):
        char = self.bf.pickup(item)
        if char:
            self.state.message = '%c - %s.' % (char, item.getName())

    def exitItemMenu(self, cc):
        return cc == ' ' or cc == '\n'


