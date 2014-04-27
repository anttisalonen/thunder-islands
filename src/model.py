#!/usr/bin/env python2.7

import random
import collections
import math
import time
import string

import astar
import log

class InvalidMovementError(object):
    pass

class Tile(object):
    class Base(object):
        Grass = 0
        Water = 1
        Floor = 2
        Pathway = 3

    class Overlay(object):
        NoOverlay = 0
        Tree = 1
        Wall = 2

    def __init__(self, basetiletype, overlay):
        self.base = basetiletype
        self.overlay = overlay

    def movementCost(self):
        if not self.passable():
            raise InvalidMovementError()
        if self.base == Tile.Base.Grass:
            return 3
        elif self.base == Tile.Base.Water:
            return 7
        elif self.base == Tile.Base.Floor:
            return 2
        elif self.base == Tile.Base.Pathway:
            return 2
        assert False

    def passable(self):
        return self.overlay == Tile.Overlay.NoOverlay

class WeaponType(object):
    Magnum357 = 0
    RifleG12 = 1

class BulletType(object):
    Cal357 = 0
    Gauge12 = 1

class Item(object):
    def getName(self):
        raise NotImplementedError('Derived class must implement this')

class Clip(Item):
    def __init__(self, btype):
        self.btype = btype

    def getName(self):
        if self.btype == BulletType.Cal357:
            return '.357 clip'
        elif self.btype == BulletType.Gauge12:
            return '12g clip'
        assert False

class Weapon(Item):
    def __init__(self, wtype):
        self.wtype = wtype

    def getName(self):
        if self.wtype == WeaponType.Magnum357:
            return '.357 Magnum'
        elif self.wtype == WeaponType.RifleG12:
            return '12g rifle'
        assert False

def soldierNames():
    names = ['Antti', 'Eppi', 'Purzel', 'Maija', 'Misse', 'Donald', 'Dagobert', 'Mickey', 'Goofy', 'Arnold', 'Bruce', 'Sylvester', 'Renny']
    for n in names:
        yield n

class SoldierAttributes(object):
    def __init__(self, name, stamina, health):
        self.name = name
        self.stamina = stamina
        self.health = health

def getSoldierAttributes(enemy, names):
    stamina = random.randrange(50, 90)
    health = random.randrange(50, 90)
    if enemy:
        return SoldierAttributes('enemy', stamina, health)
    else:
        return SoldierAttributes(names.next(), stamina, health)

class Soldier(object):
    APsToPickup = 4

    def __init__(self, x, y, team, attributes):
        self.x = x
        self.y = y
        self.team = team
        self.attributes = attributes
        self.aps = 0
        self.inventory = dict()
        self.wieldedItem = None

    def setPosition(self, pos):
        self.x, self.y = pos[0], pos[1]

    def getPosition(self):
        return self.x, self.y

    def getName(self):
        return self.attributes.name

    def decreaseHealth(self, num):
        assert num > 0
        self.attributes.health -= num
        if self.attributes.health < 0:
            self.attributes.health = 0
        if self.attributes.health == 0:
            self.aps = 0

    def alive(self):
        return self.attributes.health > 0

    def getHealth(self):
        return self.attributes.health

    def getAPs(self):
        return self.aps

    def refreshAPs(self):
        if self.attributes.health > 0:
            self.aps = self.attributes.stamina * 25 / 100

    def useAPs(self, cost):
        if cost > self.aps:
            return False
        self.aps -= cost
        return True

    def pickup(self, item):
        if not self.useAPs(Soldier.APsToPickup):
            return False
        return self.addToInventory(item)

    def addToInventory(self, item):
        nl = None
        for c in string.ascii_lowercase + string.ascii_uppercase:
            if c not in self.inventory:
                nl = c
                break
        if not nl:
            return None

        assert nl not in self.inventory
        self.inventory[nl] = item
        if self.wieldedItem is None and isinstance(item, Weapon):
            self.wieldedItem = nl
        return nl

    def removeFromInventory(self, char):
        try:
            item = self.inventory[char]
        except KeyError:
            return None
        else:
            del self.inventory[char]
            if self.wieldedItem == char:
                self.wieldedItem = None
            return item

    def getInventory(self):
        return self.inventory

    def hasAPsToPickup(self):
        return self.aps >= Soldier.APsToPickup

class BattlefieldListener(object):
    def currentSoldierChanged(self):
        pass

class TerrainCreator(object):
    def __init__(self, bf):
        self.bf = bf
        self.doorways = list()
        for i in xrange(self.bf.w):
            self.bf.terrain[i] = dict()
            for j in xrange(self.bf.h):
                self.bf.terrain[i][j] = Tile(Tile.Base.Grass, Tile.Overlay.NoOverlay)

    def addRandomForest(self):
        for i in xrange(self.bf.w):
            for j in xrange(self.bf.h):
                if self.bf.terrain[i][j].base != Tile.Base.Water:
                    tree = i != 0 and i != self.bf.w - 1 and random.randrange(3) == 0
                    if tree:
                        self.bf.terrain[i][j] = Tile(Tile.Base.Grass, Tile.Overlay.Tree)

    def addCoastLine(self, width):
        for i in xrange(self.bf.w):
            for j in xrange(width):
                self.bf.terrain[i][j] = Tile(Tile.Base.Water, Tile.Overlay.NoOverlay)
        for i in xrange(6, 1, -1):
            for iteration in xrange(self.bf.w / 4):
                rad = random.randrange(1, i)
                pos = random.randrange(0, self.bf.w)
                water = random.choice([True, False])
                for j in xrange(rad * 2):
                    for k in xrange(rad * 2):
                        dist = (j - rad) * (j - rad) + (k - rad) * (k - rad)
                        if math.sqrt(dist) <= rad:
                            px = pos + j - rad
                            py = width + k - rad
                            if px >= 0 and py >= 0 and px < self.bf.w and py < self.bf.h:
                                self.bf.terrain[px][py].base = Tile.Base.Water
                                if water:
                                    self.bf.terrain[px][py].overlay = Tile.Overlay.NoOverlay

    def addHouse(self):
        assert self.bf.w >= 30 and self.bf.h >= 30
        # multiple tries to ensure the house is not in water or within another house
        for tries in xrange(10):
            hwidth = random.randrange(5, 15)
            hheight = random.randrange(5, 15)
            hx = random.randrange(5, self.bf.w - hwidth - 5)
            hy = random.randrange(5, self.bf.h - hheight - 5)
            # now check whether the house would be in water or within another house
            blocked = False
            for i in xrange(hx - 3, hx + hwidth + 1 + 3):
                for j in xrange(hy - 3, hy + hheight + 1 + 3):
                    if self.bf.terrain[i][j].base == Tile.Base.Water or self.bf.terrain[i][j].base == Tile.Base.Floor:
                        blocked = True
                        break
                if blocked:
                    break
            if blocked:
                continue

            # not in water:
            # create walls
            for i in xrange(hx, hx + hwidth + 1):
                self.bf.terrain[i][hy] = Tile(Tile.Base.Floor, Tile.Overlay.Wall)
            for i in xrange(hx, hx + hwidth + 1):
                self.bf.terrain[i][hy + hheight] = Tile(Tile.Base.Floor, Tile.Overlay.Wall)
            for i in xrange(hy, hy + hheight + 1):
                self.bf.terrain[hx][i] = Tile(Tile.Base.Floor, Tile.Overlay.Wall)
            for i in xrange(hy, hy + hheight + 1):
                self.bf.terrain[hx + hwidth][i] = Tile(Tile.Base.Floor, Tile.Overlay.Wall)

            # create floor
            for i in xrange(hx + 1, hx + hwidth):
                for j in xrange(hy + 1, hy + hheight):
                    self.bf.terrain[i][j] = Tile(Tile.Base.Floor, Tile.Overlay.NoOverlay)

            # create door
            dwall = random.choice(range(4))
            if dwall == 0 or dwall == 1:
                dx = hx + random.randrange(2, hwidth - 1)
                if dwall == 0:
                    dy = hy
                else:
                    dy = hy + hheight
            else:
                dy = hy + random.randrange(2, hheight - 1)
                if dwall == 2:
                    dx = hx
                else:
                    dx = hx + hwidth
            self.bf.terrain[dx][dy] = Tile(Tile.Base.Floor, Tile.Overlay.NoOverlay)

            # clear trees right at the door
            for i in xrange(dx - 1, dx + 2):
                for j in xrange(dy - 1, dy + 2):
                    if self.bf.terrain[i][j].overlay == Tile.Overlay.Tree:
                        self.bf.terrain[i][j].overlay = Tile.Overlay.NoOverlay

            self.doorways.append((dx, dy))
            return

    def addPaths(self):
        for i in self.doorways:
            for j in self.doorways:
                if i <= j:
                    continue
                path = self.bf.getPath(i, j)
                assert path
                if path:
                    for p in path:
                        if self.bf.terrain[p[0]][p[1]].base == Tile.Base.Pathway:
                            coords = [p]
                        else:
                            coords = [p, (p[0] - 1, p[1]), (p[0], p[1] - 1), (p[0] + 1, p[1]), (p[0], p[1] + 1)]
                        for cx, cy in coords:
                            if cx >= 0 and cy >= 0 and cx < self.bf.w and cy < self.bf.h:
                                if self.bf.terrain[cx][cy].base == Tile.Base.Grass:
                                    self.bf.terrain[cx][cy] = Tile(Tile.Base.Pathway, Tile.Overlay.NoOverlay)

    def addWeapon(self):
        for i in xrange(self.bf.h):
            j = random.randrange(self.bf.w)
            if self.bf.terrain[j][i].base == Tile.Base.Grass and self.bf.terrain[j][i].overlay == Tile.Overlay.NoOverlay:
                self.bf.addItem(Weapon(WeaponType.RifleG12), (j, i))
                return True
        return False

class Battlefield(object):
    def __init__(self, seed = None):
        if seed is None:
            seed = int(time.time())
        random.seed(seed)
        log.log('Random seed: %d' % seed)

        self.w = 80
        self.h = 40
        self.soldiers = list()
        self.terrain = dict()
        self.listeners = list()
        self.moveTarget = None
        self.shootLine = None
        self.currentSoldierIndex = 0

        self.items = collections.defaultdict(list)

        names = soldierNames()
        for i in xrange(8):
            t = i % 2
            if t == 0:
                x = 0
            else:
                x = self.w - 1

            if i % 3 != 0:
                wp = WeaponType.Magnum357
                bt = BulletType.Cal357
            else:
                wp = WeaponType.RifleG12
                bt = BulletType.Gauge12
            s = Soldier(x, i + 20, t, getSoldierAttributes(t != 0, names))
            s.addToInventory(Weapon(wp))
            for i in xrange(3):
                s.addToInventory(Clip(bt))
            self.soldiers.append(s)

        self.createTerrain()

        for s in self.soldiers:
            s.refreshAPs()

    def createTerrain(self):
        tc = TerrainCreator(self)
        tc.addRandomForest()
        tc.addCoastLine(8)
        for i in xrange(3):
            tc.addHouse()
        tc.addPaths()
        tc.addWeapon()

    def addListener(self, listener):
        self.listeners.append(listener)
        listener.currentSoldierChanged()

    def soldierAt(self, x, y):
        for s in self.soldiers:
            if s.alive() and s.x == x and s.y == y:
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
                    if sold.alive():
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
        if not self.terrain[x][y].passable():
            return False
        if self.soldierAt(x, y) != None:
            return False
        return True

    def movementCost(self, x, y):
        return self.terrain[x][y].movementCost()

    def moveTo(self, x, y):
        self.moveTarget = self.getPath(self.getCurrentSoldier().getPosition(), (x, y))

    def updateMovement(self):
        soldier = self.getCurrentSoldier()
        assert soldier.getPosition() == self.moveTarget[0]
        self.moveTarget.pop(0)
        if not self.moveTarget:
            return False
        nextStep = self.moveTarget[0]
        assert self.passable(nextStep[0], nextStep[1]), '%dx%d is not passable' % nextStep
        cost = self.movementCost(nextStep[0], nextStep[1])
        if soldier.aps < cost:
            self.moveTarget = None
            return True
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

    @staticmethod
    def distance(a, b):
        xd = abs(a[0] - b[0])
        yd = abs(a[1] - b[1])
        return math.sqrt(xd * xd + yd * yd)

    def shoot(self, x, y, aiming):
        assert aiming > 0 and aiming < 5
        sold = self.getCurrentSoldier()
        if not sold.useAPs(10):
            return False

        soldpos = sold.getPosition()
        shootLine = self.line(soldpos[0], soldpos[1], x, y)
        self.shootLine = shootLine[1:10]
        return True

    def updateShot(self):
        shotpos = self.shootLine.pop(0)
        x, y = shotpos[0]
        hit = self.soldierAt(x, y)
        if hit:
            self.shootLine = None
            hit.decreaseHealth(40)
            return x, y, hit
        if not self.terrain[x][y].passable():
            self.shootLine = None
            return x, y, None

    def line(self, x0, y0, x1, y1):
        # Bresenham
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        if x0 < x1: sx = 1
        else:       sx = -1
        if y0 < y1: sy = 1
        else:       sy = -1
        err = dx - dy
        origErr = err

        ret = list()
        errRet = list()

        while True:
            if x0 == x1 and y0 == y1:
                errRet.append(0)
            else:
                errRet.append(abs((origErr - err) / float(max(dx, dy))))
            ret.append((x0, y0))
            if x0 == x1 and y0 == y1:
                return zip(ret, errRet)
            e2 = 2 * err
            if e2 > -dy:
                err = err - dy
                x0 = x0 + sx
            if e2 < dx:
                err = err + dx
                y0 = y0 + sy

    def addItem(self, item, position):
        self.items[position].append(item)

    def removeItem(self, item, position):
        items = self.items[position]
        items.remove(item)

    def itemsAt(self, x, y):
        if (x, y) in self.items:
            return self.items[(x, y)]
        else:
            return list()

def main():
    bf = Battlefield()
    ps1 = [(0, 0), (5, 6), (8, 8), (3, 2), (3298, 489), (347, 38)]
    ps2 = [(84, 47), (347, 48), (337, 38), (357, 38), (347, 28), (37, 3), (2, 2), (0, 0), (3, 2), (484, 9293), (484, 484), (200, 200)]
    for sp in ps1:
        for ep in ps2:
            l = bf.line(sp[0], sp[1], ep[0], ep[1])
            print sp, ep, max(l[1]), sum(l[1]) / float(len(l[1]))

if __name__ == '__main__':
    main()

