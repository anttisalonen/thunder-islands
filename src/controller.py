#!/usr/bin/env python2.7

import curses
import string
import cPickle as pickle

import model

class ViewFlags(object):
    def __init__(self):
        self.running = True
        self.center = False
        self.droppedItem = None
        self.travelling = 0

class ViewState(object):
    def __init__(self, bf):
        self.cursorpos = 5, 5
        self.bf = bf
        self.aiming = 0
        self.message = ''
        self.pressedKeyCode = 0
        self.showInventory = False
        self.showPickupMenu = False
        self.itemMenu = dict()

    def moveCursor(self, x, y, warp):
        self.message = ''
        self.stopAim()
        if warp:
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

def exitItemMenu(c):
    return c == ord(' ') or c == ord('\n')

class Controller(model.BattlefieldListener):
    def __init__(self, bf, saveable):
        self.bf = bf
        self.saveable = saveable
        self.soldierCursorPos = dict()
        self.warp = False
        self.cstate = ViewState(self.bf)
        self.cflags = ViewFlags()
        self.bf.addListener(self)
        self.mySoldiers = self.bf.soldiersInTeam(0)
        try:
            self.currentSoldier = self.mySoldiers[0]
        except IndexError:
            self.currentSoldier = None

    def turnEnded(self, currentTeam):
        if self.currentSoldier and currentTeam == 0:
            self.bf.setCurrentSoldier(self.currentSoldier)

    def getInput(self):
        while True:
            c = (yield)
            self.cstate.pressedKeyCode = c
            if c == ord('q'):
                self.cflags.running = False

            # Need to have all (yield) calls in this function apparently.
            if c == ord('i') or c == ord('d'):
                dropping = c == ord('d')
                self.cstate.showInventory = True
                while True:
                    c = (yield)
                    if not dropping and (c == ord('i') or c == ord('q') or exitItemMenu(c)):
                        self.cstate.showInventory = False
                        break
                    elif dropping:
                        if exitItemMenu(c):
                            break
                        else:
                            soldier = self.bf.getCurrentSoldier()
                            it = soldier.removeFromInventory(chr(c))
                            if it:
                                self.bf.addItem(it, soldier.getPosition())
                                self.cstate.message = 'Dropped %s.' % it.getName()
                                self.cflags.droppedItem = it
                                break
                self.cstate.showInventory = False
            elif c == ord(','):
                soldier = self.bf.getCurrentSoldier()
                if soldier.hasAPsToPickup():
                    pos = soldier.getPosition()
                    items = self.bf.itemsAt(pos[0], pos[1])
                    if items:
                        if len(items) > 1:
                            self.cstate.message = 'Select item to pick up.'
                            self.cstate.showPickupMenu = True
                            self.cstate.itemMenu = dict(zip(string.ascii_lowercase, items))
                            c = (yield)
                            try:
                                item = self.cstate.itemMenu[chr(c)]
                            except KeyError:
                                pass
                            else:
                                self.pickup(item)
                            self.cstate.showPickupMenu = False
                        else:
                            self.pickup(items[0])
                else:
                    self.cstate.message = 'Not enough APs to pick up an item.'

            self._handleCursorMove(c)
            self._handleUIChange(c)
            self._handleAction(c)

    def pickup(self, item):
        char = self.bf.pickup(item)
        if char:
            self.cstate.message = '%c - %s.' % (char, item.getName())

    def _handleCursorMove(self, c):
        if c == curses.KEY_DOWN or c == 50:
            self.cstate.moveCursor(0, 1, self.warp)
        elif c == curses.KEY_UP or c == 56:
            self.cstate.moveCursor(0, -1, self.warp)
        elif c == curses.KEY_LEFT or c == 52:
            self.cstate.moveCursor(-1, 0, self.warp)
        elif c == curses.KEY_RIGHT or c == 54:
            self.cstate.moveCursor(1, 0, self.warp)
        elif c == 49:
            self.cstate.moveCursor(-1, 1, self.warp)
        elif c == 51:
            self.cstate.moveCursor(1, 1, self.warp)
        elif c == 53:
            self.warp = not self.warp
        elif c == 55:
            self.cstate.moveCursor(-1, -1, self.warp)
        elif c == 57:
            self.cstate.moveCursor(1, -1, self.warp)

    def _handleUIChange(self, c):
        try:
            cc = chr(c)
        except ValueError:
            cc = None
        if c >= curses.KEY_F2 and c <= curses.KEY_F5:
            self.cstate.stopAim()
            soldIndex = c - curses.KEY_F2
            try:
                sold = self.mySoldiers[soldIndex]
            except IndexError:
                pass
            else:
                if sold.alive():
                    self.bf.setCurrentSoldier(sold)
                    self.currentSoldier = sold
                try:
                    self.cstate.cursorpos = self.soldierCursorPos[self.currentSoldier]
                except KeyError:
                    self.cstate.cursorpos = self.bf.getCurrentSoldier().getPosition()
                self.cstate.message = 'Controlling %s.' % self.bf.getCurrentSoldier().getName()
        elif cc == 'c' or cc == 'z':
            self.cflags.center = True
        elif cc == 's':
            self._saveGame()

    def _saveGame(self):
        with open('game.sav', 'wb') as f:
            pickle.dump(self.saveable, f)
        self.cstate.message = 'Game saved.'

    def _handleAction(self, c):
        try:
            cc = chr(c)
        except ValueError:
            cc = None

        if c == 10 or c == 13 or c == curses.KEY_ENTER:
            if self.currentSoldier:
                self.cstate.stopAim()
                self.bf.moveTo(self.cstate.cursorpos[0], self.cstate.cursorpos[1])
                self.soldierCursorPos[self.currentSoldier] = self.cstate.cursorpos
        elif cc == ' ':
            self.cstate.stopAim()
            self.cstate.message = 'End of turn...'
            if self.bf.endTurn() and not self.bf.isFriendly():
                self.cstate.message = 'Sector won!'
        elif cc == 'f':
            self.cstate.aim()
        elif cc == 'F':
            self.cstate.shoot()

        self._handleTravel(cc)

    def _handleTravel(self, cc):
        if cc == 'h' or cc == 'j' or cc == 'k' or cc == 'l':
            if cc == 'h':
                self.cflags.travelling = 1
            elif cc == 'j':
                self.cflags.travelling = 2
            elif cc == 'k':
                self.cflags.travelling = 3
            else:
                self.cflags.travelling = 4

