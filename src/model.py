#!/usr/bin/env python2.7

import random

class Tile(object):
    def __init__(self, tree):
        self.tree = tree

class Soldier(object):
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team

class Battlefield(object):
    def __init__(self):
        self.w = 80
        self.h = 40
        self.soldiers = list()
        self.terrain = dict()
        for i in xrange(8):
            t = i % 2
            if t == 0:
                x = 0
            else:
                x = self.w - 1
            self.soldiers.append(Soldier(x, i, t))

        random.seed(21)

        for i in xrange(self.w):
            self.terrain[i] = dict()
            for j in xrange(self.h):
                tree = i != 0 and i != self.w - 1 and random.randrange(3) == 0
                self.terrain[i][j] = Tile(tree)

    def soldierAt(self, x, y):
        for s in self.soldiers:
            if s.x == x and s.y == y:
                return s
        return None

def main():
    bf = Battlefield()

if __name__ == '__main__':
    main()

