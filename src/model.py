#!/usr/bin/env python2.7

import random
import collections
import math
import time
import string

import astar
import log

class InvalidMovementError(RuntimeError):
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
    MaxAPs = 25

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
        restAPs = self.aps
        if self.attributes.health > 0:
            self.aps = self.attributes.stamina * Soldier.MaxAPs / 100
            self.aps += min(5, restAPs)
            self.aps = min(Soldier.MaxAPs, self.aps)

    def useAPs(self, cost):
        if cost > self.aps:
            return False
        self.aps -= cost
        return True

    def pickup(self, item):
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

    def turnEnded(self, currentTeam):
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
                    tree = i != 0 and i != self.bf.w - 1 and random.randrange(6) == 0
                    if tree:
                        self.bf.terrain[i][j] = Tile(Tile.Base.Grass, Tile.Overlay.Tree)

    def addCoastLine(self, width, border):
        length = self._addInitialCoast(width, border)
        self._variateCoast(width, border, length)

    def _addInitialCoast(self, width, border):
        assert border >= 1 and border <= 4
        if border == 1:
            length = self.bf.h
            for i in xrange(width):
                for j in xrange(self.bf.h):
                    self.bf.terrain[i][j] = Tile(Tile.Base.Water, Tile.Overlay.NoOverlay)
        elif border == 2:
            length = self.bf.w
            for i in xrange(self.bf.w):
                for j in xrange(self.bf.h - width, self.bf.h):
                    self.bf.terrain[i][j] = Tile(Tile.Base.Water, Tile.Overlay.NoOverlay)
        elif border == 3:
            length = self.bf.w
            for i in xrange(self.bf.w):
                for j in xrange(width):
                    self.bf.terrain[i][j] = Tile(Tile.Base.Water, Tile.Overlay.NoOverlay)
        else:
            length = self.bf.h
            for i in xrange(self.bf.w - width, self.bf.w):
                for j in xrange(self.bf.h):
                    self.bf.terrain[i][j] = Tile(Tile.Base.Water, Tile.Overlay.NoOverlay)
        return length

    def _variateCoast(self, width, border, length):
        for i in xrange(6, 1, -1):
            for iteration in xrange(length / 4):
                rad = random.randrange(1, i)
                pos = random.randrange(0, length)
                water = random.choice([True, False])
                for j in xrange(rad * 2):
                    for k in xrange(rad * 2):
                        dist = (j - rad) * (j - rad) + (k - rad) * (k - rad)
                        if math.sqrt(dist) <= rad:
                            if border == 1:
                                px = width + k - rad
                                py = pos + j - rad
                            elif border == 2:
                                px = pos + j - rad
                                py = self.bf.h - (width + k - rad)
                            elif border == 3:
                                px = pos + j - rad
                                py = width + k - rad
                            else:
                                px = self.bf.w - (width + k - rad)
                                py = pos + j - rad
                            if px >= 0 and py >= 0 and px < self.bf.w and py < self.bf.h:
                                self.bf.terrain[px][py].base = Tile.Base.Water
                                if water:
                                    self.bf.terrain[px][py].overlay = Tile.Overlay.NoOverlay

    def _createInitialHouse(self):
        hwidth = random.randrange(5, 15)
        hheight = random.randrange(5, 15)
        hx = random.randrange(5, self.bf.w - hwidth - 5)
        hy = random.randrange(5, self.bf.h - hheight - 5)
        # now check whether the house would be in water or within another house
        for i in xrange(hx - 3, hx + hwidth + 1 + 3):
            for j in xrange(hy - 3, hy + hheight + 1 + 3):
                if self.bf.terrain[i][j].base == Tile.Base.Water or self.bf.terrain[i][j].base == Tile.Base.Floor:
                    return None
        return hx, hy, hwidth, hheight

    def _createHouseWalls(self, hx, hy, hwidth, hheight):
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

    def _createHouseDoor(self, hx, hy, hwidth, hheight):
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

    def addHouse(self):
        assert self.bf.w >= 30 and self.bf.h >= 30
        # multiple tries to ensure the house is not in water or within another house
        for tries in xrange(10):
            houseparams = self._createInitialHouse()
            if not houseparams:
                continue

            # not in water:
            # create walls
            self._createHouseWalls(*houseparams)

            # create door
            self._createHouseDoor(*houseparams)
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

class TeamAI(object):
    class Personality(object):
        Defensive = 0
        Offensive = 1

    def __init__(self, bf):
        self.bf = bf
        self.myTeam = 1
        self.personalities = dict()
        for s in self.bf.soldiersInTeam(self.myTeam):
            p = random.choice([TeamAI.Personality.Defensive, TeamAI.Personality.Offensive])
            self.personalities[s] = p

    def coverScore(self, line):
        score = min(len(line), 10)
        for i, ((lx, ly), err) in enumerate(line):
            ol = self.bf.terrain[lx][ly].overlay
            if ol == Tile.Overlay.Tree:
                if i == 0:
                    score *= 2.0
                elif i == 1:
                    score *= 1.3
                elif i == 2:
                    score *= 1.1
            elif ol == Tile.Overlay.Wall:
                return 15
        return score

    def getPositionScores(self, pos, enemies):
        defScores = list([20])
        offScores = list([0])
        for e in enemies:
            epos = e.getPosition()
            line = getLine(pos[0], pos[1], epos[0], epos[1])[1:-1]
            defScores.append(self.coverScore(line))
            offScores.append(self.attackScore(line))
        return min(defScores), max(offScores)

    def attackScore(self, line):
        score = 10 - min(len(line), 9)
        ll = reversed(line)
        for i, ((lx, ly), err) in enumerate(ll):
            ol = self.bf.terrain[lx][ly].overlay
            sd = self.bf.soldierAt(lx, ly)
            if sd and sd.team == self.myTeam:
                return 0
            if ol == Tile.Overlay.Tree:
                if i == 0:
                    score *= 0.5
                elif i == 1:
                    score *= 0.8
                elif i == 2:
                    score *= 0.9
            elif ol == Tile.Overlay.Wall:
                return 0
        return score

    def _getPossibleCoverPositions(self, nearbyTrees, soldier, enemies):
        mypos = soldier.getPosition()
        positionsBehindTrees = set()
        for tx, ty in nearbyTrees:
            for e in enemies:
                ex, ey = e.getPosition()
                dx, dy = ex - tx, ey - ty
                px = tx
                py = ty
                if not abs(dy) > 2 * abs(dx):
                    px -= math.copysign(1, dx)
                if not abs(dx) > 2 * abs(dy):
                    py -= math.copysign(1, dy)
                if px >= 0 and py >= 0 and px < self.bf.w and py < self.bf.h and (mypos == px, py or self.bf.passable(px, py)):
                    positionsBehindTrees.add((px, py))
        return positionsBehindTrees

    def findCombatPosition(self, soldier, enemies):
        assert enemies
        nearbyTrees = list()
        myposx, myposy = soldier.getPosition()
        for x in xrange(max(0, myposx - 5), min(self.bf.w, myposx + 5)):
            for y in xrange(max(0, myposy - 5), min(self.bf.h, myposy + 5)):
                if self.bf.terrain[x][y].overlay == Tile.Overlay.Tree:
                    nearbyTrees.append((x, y))
        positionsBehindTrees = self._getPossibleCoverPositions(nearbyTrees, soldier, enemies)

        if not positionsBehindTrees:
            return None

        places = dict()
        for px, py in positionsBehindTrees:
            defScore, offScore = self.getPositionScores((px, py), enemies)
            places[(px, py)] = defScore, offScore

        return self._decideCombatPosition(soldier, places)

    def _decideCombatPosition(self, soldier, places):
        personality = self.personalities[soldier]
        if personality == TeamAI.Personality.Defensive:
            best = sorted(places.items(), key=lambda (k, (d, o)): d, reverse=True)
            return best[0][0]
        elif personality == TeamAI.Personality.Offensive:
            best = sorted(places.items(), key=lambda (k, (d, o)): o, reverse=True)
            return best[0][0]
        else:
            assert False

    def findShotTarget(self):
        s = self.bf.getCurrentSoldier()
        mypos = s.getPosition()
        enemies = self.bf.enemySoldiersSeenByTeam(self.myTeam)
        bestScore = 0
        bestTarget = None
        for e in enemies:
            epos = e.getPosition()
            line = getLine(mypos[0], mypos[1], epos[0], epos[1])[1:-1]
            offScore = self.attackScore(line)
            if offScore > bestScore:
                bestScore = offScore
                bestTarget = epos
        return bestTarget

    def getInput(self):
        while True:
            (yield)

            currTeam = self.bf.getCurrentSoldier().team
            assert currTeam == self.myTeam
            for s in self.bf.soldiersInTeam(self.myTeam):
                self.bf.setCurrentSoldier(s)
                cover = self.findMovePosition()
                if cover:
                    self.bf.moveTo(cover[0], cover[1])
                    while self.bf.moveTarget:
                        (yield)
                    while True:
                        while self.bf.shootLine:
                            (yield)
                        shotTgt = self.findShotTarget()
                        if not shotTgt:
                            break
                        shot = self.bf.shoot(shotTgt[0], shotTgt[1], 1)
                        if not shot:
                            break
            self.bf.endTurn()

    def findMovePosition(self):
        s = self.bf.getCurrentSoldier()
        enemies = self.bf.enemySoldiersSeenByTeam(self.myTeam)
        if enemies:
            cover = self.findCombatPosition(s, enemies)
            return cover
        else:
            return None

    def movementUpdated(self, noaps, newSoldiers, newItems):
        if noaps or noaps == False:
            self.bf.moveTarget = None
        if newSoldiers:
            cover = self.findMovePosition()
            if cover:
                self.bf.moveTo(cover[0], cover[1])

class Island(object):
    def __init__(self, seed=None):
        if seed is None:
            seed = int(time.time())
        random.seed(seed)
        log.log('Random seed: %d' % seed)

        self.sectors = dict()
        self.currSector = 2, 3
        self.islandSize = 3, 4
        self.bf = None

        for i in xrange(3):
            self.sectors[i] = dict()
            for j in xrange(4):
                border = 0
                if i == 0:
                    border |= 0x01
                if i == 2:
                    border |= 0x08
                if j == 0:
                    border |= 0x04
                if j == 3:
                    border |= 0x02
                self.sectors[i][j] = Battlefield(border)
                if i != self.currSector[0] or j != self.currSector[1]:
                    self.sectors[i][j].addEnemySoldiers()

        self.playerSoldiers = list()

        names = soldierNames()
        for i in xrange(4):
            wp = WeaponType.Magnum357
            bt = BulletType.Cal357
            s = Soldier(0, 0, 0, getSoldierAttributes(False, names))
            s.addToInventory(Weapon(wp))
            for j in xrange(3):
                s.addToInventory(Clip(bt))
            self.playerSoldiers.append(s)

        self.placeSoldiers(0)

    def getCurrentBattlefield(self):
        return self.bf

    def placeSoldiers(self, direction):
        self.bf = self.sectors[self.currSector[0]][self.currSector[1]]

        for i, s in enumerate(self.playerSoldiers):
            x = self.bf.w / 2
            y = i + self.bf.h / 2
            xd = 1
            yd = 1
            if direction == 1:
                x = self.bf.w - 1
                xd = -1
            elif direction == 2:
                y = i
            elif direction == 3:
                y = self.bf.h - i - 1
                yd = -1
            elif direction == 4:
                x = 0
            for tries in xrange(10):
                if self.bf.passable(x, y):
                    break
                x += xd
                y += yd
            s.x = x
            s.y = y

        self.bf.setCurrentSoldier(self.playerSoldiers[0])
        for s in self.playerSoldiers:
            self.bf.soldiers.append(s)

    def travel(self, direction):
        assert direction >= 1 and direction <= 4
        nx, ny = self.currSector
        if direction == 1:
            nx -= 1
        elif direction == 2:
            ny += 1
        elif direction == 3:
            ny -= 1
        else:
            nx += 1
        if nx < 0 or ny < 0 or nx >= self.islandSize[0] or ny >= self.islandSize[1]:
            return False

        self.bf.removeSoldiersFromTeam(0)
        self.currSector = nx, ny
        self.placeSoldiers(direction)
        return True

class Battlefield(object):
    def __init__(self, border):
        self.w = 80
        self.h = 40
        self.soldiers = list()
        self.terrain = dict()
        self.listeners = list()
        self.moveTarget = None
        self.shootLine = None
        self.shotDistance = None
        self.currentSoldier = None
        self.friendly = True

        self.items = collections.defaultdict(list)

        self.createTerrain(border)

        for s in self.soldiers:
            s.refreshAPs()

    def addEnemySoldiers(self):
        self.friendly = False
        for i in xrange(4):
            for j in xrange(5):
                x = random.randrange(30, self.w)
                y = random.randrange(20, self.h)
                if self.passable(x, y):
                    break

            if i % 3 != 0:
                wp = WeaponType.Magnum357
                bt = BulletType.Cal357
            else:
                wp = WeaponType.RifleG12
                bt = BulletType.Gauge12
            s = Soldier(x, y, 1, getSoldierAttributes(True, None))
            if i == 0:
                self.setCurrentSoldier(s)
            s.addToInventory(Weapon(wp))
            for j in xrange(3):
                s.addToInventory(Clip(bt))
            self.soldiers.append(s)

    def removeSoldiersFromTeam(self, teamnum):
        self.soldiers = [s for s in self.soldiers if s.team != teamnum]

    def createTerrain(self, border):
        tc = TerrainCreator(self)
        tc.addRandomForest()
        if border & 0x01:
            tc.addCoastLine(8, 1)
        if border & 0x02:
            tc.addCoastLine(8, 2)
        if border & 0x04:
            tc.addCoastLine(8, 3)
        if border & 0x08:
            tc.addCoastLine(8, 4)
        for tries in xrange(3):
            tc.addHouse()
        tc.addPaths()
        tc.addWeapon()

    def addListener(self, listener):
        self.listeners.append(listener)

    def soldierAt(self, x, y):
        for s in self.soldiers:
            if s.x == x and s.y == y and s.alive():
                return s
        return None

    def getCurrentSoldier(self):
        return self.currentSoldier

    def setCurrentSoldier(self, soldier):
        self.currentSoldier = soldier

    def getPath(self, start, end):
        if not self.passable(end[0], end[1]):
            return None

        def neighbours(v):
            ret = list()
            for i, j in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                nx = v[0] + i
                ny = v[1] + j
                if nx < 0 or ny < 0 or nx >= self.w or ny >= self.h:
                    continue
                if self.passable(nx, ny):
                    ret.append((nx, ny))
            return ret

        def costfunc(n1, n2):
            return self.movementCost(n2[0], n2[1])

        path = astar.solve(neighbours, costfunc, astar.euclidHeuristics(end),
                astar.makeGoalFunc(end), start)
        return path

    def passable(self, x, y):
        if not self.terrain[x][y].passable():
            return False
        return self.soldierAt(x, y) == None

    def movementCost(self, x, y):
        return self.terrain[x][y].movementCost()

    def moveTo(self, x, y):
        self.moveTarget = self.getPath(self.getCurrentSoldier().getPosition(), (x, y))

    def updateMovement(self):
        soldier = self.getCurrentSoldier()
        assert soldier.getPosition() == self.moveTarget[0]
        self.moveTarget.pop(0)
        if not self.moveTarget:
            return False, set(), set()
        nextStep = self.moveTarget[0]
        assert self.passable(nextStep[0], nextStep[1]), '%dx%d is not passable' % nextStep
        cost = self.movementCost(nextStep[0], nextStep[1])

        if not self.friendly and not soldier.useAPs(cost):
            self.moveTarget = None
            return True, set(), set()

        soldiersSeenBefore = set(self.enemySoldiersSeenBySoldier(soldier))
        itemsSeenBefore = set(self.itemsSeenBySoldier(soldier))

        soldier.setPosition(nextStep)

        soldiersSeenAfter = set(self.enemySoldiersSeenBySoldier(soldier))
        itemsSeenAfter = set(self.itemsSeenBySoldier(soldier))

        newSoldiersSeen = soldiersSeenAfter - soldiersSeenBefore
        newItemsSeen = itemsSeenAfter - itemsSeenBefore
        return None, newSoldiersSeen, newItemsSeen

    def endTurn(self):
        self.moveTarget = None
        assert self.shootLine is None or self.shootLine == list()
        currentTeam = self.getCurrentSoldier().team
        nextTeam = 1 if currentTeam == 0 else 0
        prevCurrentSoldier = self.getCurrentSoldier()
        if nextTeam == 0:
            for s in self.soldiers:
                s.refreshAPs()

        self.currentSoldier = None
        for s in self.soldiers:
            if s.alive() and self.currentSoldier is None and s.team == nextTeam:
                self.currentSoldier = s
                break
        if not self.currentSoldier:
            self.currentSoldier = prevCurrentSoldier
            return True
        assert self.currentSoldier is not None

        assert currentTeam != nextTeam
        for l in self.listeners:
            l.turnEnded(nextTeam)
        return False

    @staticmethod
    def distance(a, b):
        xd = abs(a[0] - b[0])
        yd = abs(a[1] - b[1])
        return math.sqrt(xd * xd + yd * yd)

    def shoot(self, x, y, aiming):
        assert aiming > 0 and aiming < 5
        sold = self.getCurrentSoldier()
        if not self.friendly and not sold.useAPs(10):
            return False

        soldpos = sold.getPosition()
        shootLine = getLine(soldpos[0], soldpos[1], x, y)
        self.shootLine = shootLine[1:10]
        self.shotDistance = 0
        return True

    def updateShot(self):
        shotpos = self.shootLine.pop(0)
        self.shotDistance += 1
        x, y = shotpos[0]
        soldierToHit = self.soldierAt(x, y)
        hit = None
        if soldierToHit:
            prob = 1.0 - self.shotDistance * 0.05 # TODO: weapon and shooter dependent
            didHit = random.uniform(0, 1) < prob
            if didHit:
                hit = soldierToHit
        if hit:
            self.shootLine = None
            hit.decreaseHealth(40) # TODO: weapon and shooter dependent
            return x, y, hit
        else:
            ol = self.terrain[x][y].overlay
            if self.shotDistance > 10: # TODO: weapon dependent
                self.shootLine = None
                return x, y, None
            elif ol == Tile.Overlay.NoOverlay:
                return None
            elif ol == Tile.Overlay.Tree:
                blockProb = (self.shotDistance - 1) * 0.1
            elif ol == Tile.Overlay.Wall:
                blockProb = 1.0
            else:
                assert False, 'No blocking information for %d' % ol
            if random.uniform(0, 1) < blockProb:
                self.shootLine = None
                return x, y, None
            else:
                return None

    def addItem(self, item, position):
        self.items[position].append(item)

    def removeItem(self, item, position):
        items = self.items[position]
        items.remove(item)
        if len(items) == 0:
            del self.items[position]

    def itemsAt(self, x, y):
        if (x, y) in self.items:
            return self.items[(x, y)]
        else:
            return list()

    def itemsSeenByTeam(self, teamnum):
        ret = dict()
        slist = self.soldiersInTeam(teamnum)
        for pos, items in self.items.items():
            for s in slist:
                if self.visibilityTo(s, pos) > 0.0:
                    ret[pos] = items
                    break
        return ret

    def soldiersInTeam(self, teamnum):
        return [s for s in self.soldiers if s.team == teamnum and s.alive()]

    def soldierSeenByTeam(self, teamnum, soldier):
        if not soldier.alive():
            return False
        pos = soldier.getPosition()
        for s in self.soldiersInTeam(teamnum):
            if self.visibilityTo(s, pos) > 0.0:
                return True
        return False

    def enemySoldiersSeenByTeam(self, teamnum):
        ret = set()
        for s in self.soldiersInTeam(teamnum):
            for n in self.enemySoldiersSeenBySoldier(s):
                ret.add(n)
        return ret

    def enemySoldiersSeenBySoldier(self, soldier):
        ret = list()
        enemyTeam = 1 if soldier.team == 0 else 0
        for s in self.soldiersInTeam(enemyTeam):
            if self.visibilityTo(soldier, s.getPosition()) > 0.0:
                ret.append(s)
        return ret

    def itemsSeenBySoldier(self, soldier):
        ret = list()
        pos = soldier.getPosition()
        for pos, items in self.items.items():
            if self.visibilityTo(soldier, pos) > 0.0:
                for it in items:
                    ret.append((pos, it))
        return ret

    def visibilityTo(self, soldier, position):
        spos = soldier.getPosition()
        line = getLine(spos[0], spos[1], position[0], position[1])[1:-1]
        visibility = 1.0
        for (lx, ly), e in line:
            ol = self.terrain[lx][ly].overlay
            if ol == Tile.Overlay.NoOverlay:
                drop = 0.05
            elif ol == Tile.Overlay.Tree:
                drop = 0.35
            elif ol == Tile.Overlay.Wall:
                drop = 1.0
            else:
                assert False, 'No visibility information for %d' % ol
            visibility -= drop
        return visibility

    def isFriendly(self):
        return self.friendly

    def pickup(self, item):
        soldier = self.getCurrentSoldier()
        if not self.friendly and not soldier.useAPs(Soldier.APsToPickup):
            return False
        pos = soldier.getPosition()
        char = soldier.pickup(item)
        if char:
            self.removeItem(item, pos)
        return char

def getLine(x0, y0, x1, y1):
    # Bresenham
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    if x0 < x1:
        sx = 1
    else:
        sx = -1
    if y0 < y1:
        sy = 1
    else:
        sy = -1
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


