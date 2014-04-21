#!/usr/bin/env python2.7

import random
import collections
import astar

class InvalidMovementError(object):
    pass

class PQueue(object):
    def __init__(self):
        self.d = collections.OrderedDict()
        self.d2 = collections.OrderedDict()

    def push(self, prio, item):
        self.d[item] = prio
        try:
            self.d2[prio].append(item)
        except KeyError:
            self.d2[prio] = list()
            self.d2[prio].append(item)

    def pop(self):
        itl = self.d2.items()[0][1] # may raise IndexError
        it = itl.pop()
        if not itl:
            del self.d2.items()[0]
        del self.d[it]
        return it

    def setPriority(self, prio, item):
        oldprio = self.d[item]
        itl = self.d2[oldprio]
        itl = [x for x in x if x != item]
        try:
            self.d2[prio].append(item)
        except KeyError:
            self.d2[prio] = list()
            self.d2[prio].append(item)
        self.d[item] = prio

    def empty(self):
        return bool(self.d)

class Tile(object):
    def __init__(self, tree):
        self.tree = tree

def soldierNames():
    names = ['Antti', 'Eppi', 'Purzel', 'Maija', 'Misse', 'Donald', 'Dagobert', 'Mickey', 'Goofy', 'Arnold', 'Bruce', 'Sylvester', 'Renny']
    for n in names:
        yield n

class SoldierAttributes(object):
    def __init__(self, name, stamina):
        self.name = name
        self.stamina = stamina

def getSoldierAttributes(enemy, names):
    stamina = random.randrange(50, 90)
    if enemy:
        return SoldierAttributes('enemy', stamina)
    else:
        return SoldierAttributes(names.next(), stamina)

class Soldier(object):
    def __init__(self, x, y, team, attributes):
        self.x = x
        self.y = y
        self.team = team
        self.attributes = attributes
        self.aps = 0

    def setPosition(self, pos):
        self.x, self.y = pos[0], pos[1]

    def getPosition(self):
        return self.x, self.y

    def getName(self):
        return self.attributes.name

    def getAPs(self):
        return self.aps

    def refreshAPs(self):
        self.aps = self.attributes.stamina * 25 / 100

class BattlefieldListener(object):
    def currentSoldierChanged(self):
        pass

class Battlefield(object):
    def __init__(self):
        random.seed(21)

        self.w = 80
        self.h = 40
        self.soldiers = list()
        self.terrain = dict()
        self.listeners = list()
        self.moveTarget = None
        self.currentSoldierIndex = 0

        names = soldierNames()
        for i in xrange(8):
            t = i % 2
            if t == 0:
                x = 0
            else:
                x = self.w - 1

            self.soldiers.append(Soldier(x, i, t, getSoldierAttributes(t != 0, names)))

        for i in xrange(self.w):
            self.terrain[i] = dict()
            for j in xrange(self.h):
                tree = i != 0 and i != self.w - 1 and random.randrange(3) == 0
                self.terrain[i][j] = Tile(tree)

        for s in self.soldiers:
            s.refreshAPs()

    def addListener(self, listener):
        self.listeners.append(listener)
        listener.currentSoldierChanged()

    def soldierAt(self, x, y):
        for s in self.soldiers:
            if s.x == x and s.y == y:
                return s
        return None

    def getCurrentSoldier(self):
        return self.soldiers[self.currentSoldierIndex]

    def setCurrentSoldier(self, team, number):
        thisNum = 0
        thisIndex = 0
        for sold in self.soldiers:
            if sold.team == team:
                if thisNum == number:
                    self.currentSoldierIndex = thisIndex
                    for l in self.listeners:
                        l.currentSoldierChanged()
                    return
                thisNum += 1
            thisIndex += 1

    def getPath(self, start, end):
        if not self.passable(end[0], end[1]):
            return None

        def neighbours(v):
            ret = list()
            for i in xrange(-1, 2):
                for j in xrange(-1, 2):
                    if i == 0 and j == 0:
                        continue
                    nx = v[0] + i
                    ny = v[1] + j
                    if nx < 0 or ny < 0 or nx >= self.w or ny >= self.h:
                        continue
                    if self.passable(nx, ny):
                        ret.append((nx, ny))
            return ret

        def costfunc(n1, n2):
            return self.movementCost(n2[0], n2[1])

        path = astar.solve(neighbours, costfunc, astar.manhattanHeuristics(end),
                astar.makeGoalFunc(end), start)
        return path

    def passable(self, x, y):
        if self.terrain[x][y].tree:
            return False
        if self.soldierAt(x, y) != None:
            return False
        return True

    def movementCost(self, x, y):
        if not self.passable(x, y):
            raise InvalidMovementError()
        return 3

    def moveTo(self, x, y):
        self.moveTarget = self.getPath(self.getCurrentSoldier().getPosition(), (x, y))

    def updateMovement(self):
        soldier = self.getCurrentSoldier()
        assert soldier.getPosition() == self.moveTarget[0]
        self.moveTarget.pop(0)
        if not self.moveTarget:
            return
        nextStep = self.moveTarget[0]
        assert self.passable(nextStep[0], nextStep[1]), '%dx%d is not passable' % nextStep
        cost = self.movementCost(nextStep[0], nextStep[1])
        if soldier.aps < cost:
            self.moveTarget = None
            return
        soldier.aps -= cost
        soldier.setPosition(nextStep)

    def endTurn(self):
        currentTeam = self.getCurrentSoldier().team
        nextTeam = 1 if currentTeam == 0 else 0
        if nextTeam == 0:
            for s in self.soldiers:
                s.refreshAPs()
        self.setCurrentSoldier(nextTeam, 0)

    def updateAI(self):
        self.endTurn()

def main():
    bf = Battlefield()

if __name__ == '__main__':
    main()

