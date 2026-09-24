# -*- coding: utf-8 -*-
"""Solver NNLS con vincoli di intervallo sulle grammature delle ricette."""
import numpy as np
from scipy.optimize import lsq_linear
from foods import F

# peso relativo degli obiettivi: carbo e proteine contano piu' dei grassi,
# le kcal sono la risultante e vengono ricontrollate a posteriori.
W = np.array([1.0 / 60.0, 1.0 / 12.0, 1.0 / 14.0])  # C, P, G


def solve(items, target):
    """items: [(nome, lo_g, hi_g, step)] ; target: (kcal, C, P, G) -> (grammi, totali)"""
    names = [it[0] for it in items]
    lo = np.array([it[1] for it in items], float)
    hi = np.array([it[2] for it in items], float)
    A = np.array([[F[n][1], F[n][2], F[n][3]] for n in names], float).T  # 3 x n
    b = np.array([target[1], target[2], target[3]], float)
    Aw = A * W[:, None]
    bw = b * W
    res = lsq_linear(Aw, bw, bounds=(lo / 100.0, hi / 100.0), max_iter=400)
    x = res.x * 100.0
    # arrotondamento allo step, riproiettato nei bound
    for k, it in enumerate(items):
        st = it[3]
        x[k] = min(max(round(x[k] / st) * st, lo[k]), hi[k])
    return names, x, totals(names, x)


def totals(names, grams):
    t = np.zeros(4)
    for n, g in zip(names, grams):
        t += np.array(F[n]) * (g / 100.0)
    return t


def fmt_g(name, g):
    from foods import UNIT
    return "%d %s" % (int(round(g)), UNIT.get(name, "g"))
