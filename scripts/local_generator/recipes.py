# -*- coding: utf-8 -*-
"""Template ricette. Vincoli dello spec: UNA sola fonte proteica e UN solo
carboidrato per piatto, pesi a crudo, niente miele (marmellata al suo posto),
'Pancarre' mai 'Pane'."""

# (nome_alimento, min_g, max_g, step)
COLAZIONE = [
    [("Latte di soia", 250, 350, 50), ("Fiocchi d'avena", 40, 160, 5),
     ("Burro di arachidi", 10, 30, 5), ("Marmellata", 0, 220, 10)],
    [("Latte di soia", 200, 300, 50), ("Corn flakes s/zuccheri", 60, 220, 5),
     ("Whey", 10, 40, 5), ("Marmellata", 0, 130, 10)],
]

PRANZO = [
    [("Riso (crudo)", 60, 260, 5), ("Tonno al naturale", 60, 200, 5),
     ("Mais", 0, 140, 10), ("Olio EVO", 8, 45, 1)],
    [("Pasta (cruda)", 60, 240, 5), ("Ceci lessati", 120, 420, 10),
     ("Grana", 0, 25, 5), ("Olio EVO", 5, 40, 1)],
    [("Riso (crudo)", 60, 260, 5), ("Lenticchie lessate", 120, 420, 10),
     ("Grana", 0, 25, 5), ("Olio EVO", 5, 40, 1)],
]

SPUNTINO = [
    [("Yogurt greco 0%", 100, 300, 25), ("Banana", 0, 240, 20),
     ("Mandorle", 5, 45, 5)],
    [("Gallette di riso", 15, 140, 5), ("Fiocchi di latte magri", 60, 300, 10),
     ("Marmellata", 0, 150, 10), ("Mandorle", 5, 50, 5)],
]

# cena: UNA proteina + UN carboidrato + verdure + olio (+ un solo condimento)
CENA_PROT = [("Albume", 150, 450, 25), ("Petto di pollo", 100, 260, 10),
             ("Uova intere", 100, 250, 25), ("Burger vegetale Lidl", 100, 250, 10),
             ("Seitan", 100, 260, 10), ("Tofu", 100, 280, 10),
             ("Fiocchi di latte magri", 150, 350, 25)]
CENA_CARB = [("Pancarrè", 30, 220, 10), ("Gallette di riso", 15, 120, 5),
             ("Fette biscottate", 20, 140, 5)]
CENA_COND = [("Ketchup", 0, 40, 5), ("Maionese", 0, 25, 5)]


def cena_template(i):
    p = CENA_PROT[i % len(CENA_PROT)]
    c = CENA_CARB[i % len(CENA_CARB)]
    cond = CENA_COND[i % len(CENA_COND)]
    return [p, c, ("Verdure miste", 200, 350, 50), ("Olio EVO", 5, 35, 1), cond]


def cena_template_alt(i):
    p = CENA_PROT[(i + 3) % len(CENA_PROT)]
    c = CENA_CARB[(i + 1) % len(CENA_CARB)]
    cond = CENA_COND[(i + 1) % len(CENA_COND)]
    return [p, c, ("Verdure miste", 200, 350, 50), ("Olio EVO", 5, 35, 1), cond]
