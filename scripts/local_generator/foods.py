# -*- coding: utf-8 -*-
"""Database alimenti (per 100 g / 100 ml) — SOLO alimenti ammessi dallo spec."""
# nome: (kcal, carbo_g, prot_g, grassi_g)
F = {
    "Latte di soia":            (39,  2.5,  3.3,  1.8),   # per 100 ml
    "Fiocchi d'avena":          (370, 60.0, 13.5, 7.0),
    "Burro di arachidi":        (600, 12.0, 25.0, 50.0),
    "Marmellata":               (250, 65.0, 0.4,  0.1),
    "Corn flakes s/zuccheri":   (378, 84.0, 7.5,  0.9),
    "Whey":                     (393, 6.0,  80.0, 5.0),
    "Riso (crudo)":             (350, 78.0, 7.0,  0.6),
    "Pasta (cruda)":            (355, 71.0, 12.5, 1.5),
    "Tonno al naturale":        (103, 0.0,  23.0, 1.0),
    "Ceci lessati":             (120, 16.0, 7.0,  2.5),
    "Lenticchie lessate":       (116, 17.0, 9.0,  0.4),
    "Mais":                     (90,  18.0, 3.0,  1.2),
    "Grana":                    (392, 0.0,  33.0, 29.0),
    "Olio EVO":                 (900, 0.0,  0.0,  100.0),
    "Yogurt greco 0%":          (57,  4.0,  10.0, 0.4),
    "Mandorle":                 (600, 5.0,  21.0, 53.0),
    "Gallette di riso":         (387, 81.0, 8.0,  2.8),
    "Fiocchi di latte magri":   (90,  3.5,  12.0, 3.0),
    "Banana":                   (89,  23.0, 1.1,  0.3),
    "Mela":                     (52,  14.0, 0.3,  0.2),
    "Albume":                   (48,  0.7,  11.0, 0.2),
    "Uova intere":              (143, 0.7,  12.6, 9.5),
    "Petto di pollo":           (110, 0.0,  23.0, 1.5),
    "Burger vegetale Lidl":     (190, 6.0,  17.0, 11.0),
    "Seitan":                   (121, 4.0,  24.0, 1.0),
    "Tofu":                     (145, 2.0,  16.0, 8.0),
    "Pancarrè":                 (265, 49.0, 8.0,  3.3),
    "Fette biscottate":         (410, 75.0, 11.0, 6.0),
    "Verdure miste":            (25,  4.0,  1.5,  0.3),
    "Ketchup":                  (110, 25.0, 1.2,  0.2),
    "Maionese":                 (680, 1.5,  1.0,  75.0),
    "Gel (1 pz = 32 g)":        (312, 78.0, 0.0,  0.0),
    "Bevanda isotonica":        (24,  6.0,  0.0,  0.0),   # per 100 ml
}
UNIT = {"Latte di soia": "ml", "Bevanda isotonica": "ml"}
