#!/usr/bin/env python3
"""Icona Training Hub: tre anelli attività (nuoto/bici/corsa) su blu notte."""
from PIL import Image, ImageDraw
import math

BG_TOP, BG_BOT = (29, 74, 117), (16, 41, 68)
ORANGE, BLUE, GREEN = (235, 104, 52), (57, 135, 229), (27, 175, 122)

def ring(d, cx, cy, r, w, start, end, col):
    """Arco con estremità arrotondate."""
    d.arc([cx-r, cy-r, cx+r, cy+r], start, end, fill=col, width=w)
    for a in (start, end):
        x = cx + r*math.cos(math.radians(a))
        y = cy + r*math.sin(math.radians(a))
        d.ellipse([x-w/2, y-w/2, x+w/2, y+w/2], fill=col)

def build(size, rings=3):
    S = size*4                      # supersampling
    im = Image.new('RGB', (S, S), BG_BOT)
    d = ImageDraw.Draw(im)
    # gradiente verticale morbido
    for y in range(S):
        t = y/(S-1)
        d.line([(0, y), (S, y)], fill=tuple(
            round(BG_TOP[i] + (BG_BOT[i]-BG_TOP[i])*t) for i in range(3)))
    # bagliore diagonale appena accennato
    from PIL import ImageFilter
    glow = Image.new('L', (S, S), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-S*0.30, -S*0.50, S*0.80, S*0.40], fill=48)
    glow = glow.filter(ImageFilter.GaussianBlur(S*0.10))
    im = Image.composite(Image.new('RGB', (S, S), (92, 138, 184)), im, glow)
    d = ImageDraw.Draw(im)

    cx = cy = S/2
    if rings == 3:
        specs = [(0.360, 0.066, -90, 205, ORANGE),
                 (0.258, 0.066, -90, 140, BLUE),
                 (0.156, 0.066, -90,  75, GREEN)]
    else:                            # versione semplificata per i formati piccoli
        specs = [(0.335, 0.110, -90, 195, ORANGE),
                 (0.175, 0.110, -90,  95, BLUE)]
    for rr, ww, a0, a1, col in specs:
        ring(d, cx, cy, S*rr, int(S*ww), a0, a1, col)

    return im.resize((size, size), Image.LANCZOS)

for n in (180, 192, 512):
    build(n).save(f'/tmp/icon-{n}.png', optimize=True)
build(32, rings=2).save('/tmp/icon-32.png', optimize=True)
build(64, rings=2).save('/tmp/icon-64.png', optimize=True)

# anteprima affiancata
prev = Image.new('RGB', (180*3+60, 190), (238, 238, 235))
prev.paste(build(180), (10, 5))
prev.paste(build(64, rings=2).resize((180, 180), Image.NEAREST), (200, 5))
prev.paste(build(32, rings=2).resize((180, 180), Image.NEAREST), (390, 5))
prev.save('/tmp/icon-preview.png')
print('ok')
