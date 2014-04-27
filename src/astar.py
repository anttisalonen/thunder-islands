#!/usr/bin/env python2.7

from heapq import heappush, heappop
import sys
import math

def solve(graphfunc, costfunc, heurfunc, goaltestfunc, start):
    visited = set()
    costHere = dict() # real (g) cost
    path = list()
    parents = dict()
    openNodes = list() # key is the total (f) cost

    heappush(openNodes, (0, start))
    while True:
        current = heappop(openNodes)[1]
        if current in visited:
            continue

        visited.add(current)
        children = graphfunc(current)
        if goaltestfunc(current):
            path.append(current)
            break

        for child in children:
            if child in visited:
                continue

            edgeCost = costfunc(current, child)
            if edgeCost < 0:
                print >> sys.stderr, 'A*: negative cost'
                continue
            try:
                ch = costHere[current]
            except KeyError:
                ch = 0
            thisGCost = ch + edgeCost

            addThisAsParent = True
            try:
                costPrev = costHere[child]
                # already in open list => check if cost is less than previous
                if costPrev <= thisGCost:
                    addThisAsParent = False
            except KeyError:
                pass

            if addThisAsParent:
                thisFCost = thisGCost + heurfunc(child)
                parents[child] = current
                heappush(openNodes, (thisFCost, child))
                costHere[child] = thisGCost
        if not openNodes:
            break
    
    if not path:
        return None

    curr = path[0]
    while True:
        try:
            nextNode = parents[curr]
        except KeyError:
            break
        else:
            path.append(nextNode)
            curr = nextNode

    path.reverse()
    return path

def main():
    def gf(n):
        if n == (0, 0):
            return [(1, 1)]
        elif n == (1, 1):
            return [(0, 0), (1, 0), (2, 2)]
        elif n == (1, 0):
            return [(1, 1)]
        elif n == (2, 2):
            return [(1, 1), (3, 2)]
        elif n == (3, 2):
            return [(2, 2), (2, 3)]
        elif n == (2, 3):
            return [(3, 2), (3, 3)]
        elif n == (3, 3):
            return [(2, 3)]
    def costfunc(n1, n2):
        return 3
    def heurfunc(n):
        return 0
    start = (0, 0)
    goal = (3, 3)
    path = solve(gf, costfunc, manhattanHeuristics(goal), makeGoalFunc(goal), start)
    print path

def simplifyCostFunc(costfunc):
    return lambda x, y: costfunc(y)

def euclidHeuristics(goal):
    return lambda x: euclidDistance(x, goal)

def euclidDistance(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)

def manhattanHeuristics(goal):
    return lambda x: abs(goal[0] - x[0]) + abs(goal[1] - x[1])

def makeGoalFunc(goal):
    return lambda x: x == goal

if __name__ == '__main__':
    main()

