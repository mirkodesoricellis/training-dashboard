# -*- coding: utf-8 -*-
import sys, html, datetime, math, re
sys.path.insert(0, '/home/claude/gen')
import numpy as np
from foods import F, UNIT
from solver import solve, totals, fmt_g
import recipes as R
from days import DAYS, PESO, BASE

SRC = '/mnt/user-data/uploads/training-dashboard/index.html'
OUT = '/home/claude/out/index.html'

src = open(SRC, encoding='utf-8').read()
STYLE = src[src.index('<style>'):src.index('</style>') + len('</style>')]
SCRIPT = src[src.index('<script>'):src.index('</script>') + len('</script>')]

GIORNI = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
MESI = ['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio',
        'agosto','settembre','ottobre','novembre','dicembre']

def nfmt(x, dec=0):
    s = ('%.{}f'.format(dec)) % x
    if dec: i, d = s.split('.')
    else:   i, d = s, None
    neg = i.startswith('-'); i = i.lstrip('-')
    out = ''
    while len(i) > 3:
        out = '.' + i[-3:] + out; i = i[:-3]
    out = i + out
    if d is not None: out += ',' + d
    return ('-' if neg else '') + out

def e(s): return html.escape(s, quote=False)

# ---------- split dei pasti ----------
SPLIT_HIGH = dict(C=[.30,.38,.12,.20], P=[.15,.28,.13,.44], G=[.11,.36,.14,.39])
SPLIT_LOW  = dict(C=[.25,.35,.13,.27], P=[.15,.32,.18,.35], G=[.11,.36,.14,.39])
MEALS = [("☀️","Colazione"), ("🍽️","Pranzo"), ("🍎","Spuntino"), ("🌙","Cena")]

def fuel_tot(items):
    t = np.zeros(4)
    for n, g in items: t += np.array(F[n]) * (g/100.0)
    return t

def ring_svg(kcal, C, P, G):
    r = 52.0; circ = 2*math.pi*r
    kc, kp, kg = C*4, P*4, G*9
    tot = kc+kp+kg
    segs = []; off = 0.0
    for val, var in ((kc,'--carb'), (kp,'--prot'), (kg,'--fat')):
        L = circ*val/tot
        segs.append('<circle class="arc" cx="62" cy="62" r="52" stroke="var(%s)" '
                    'stroke-dasharray="%.1f %.1f" stroke-dashoffset="-%.1f"/>'
                    % (var, L, circ-L, off))
        off += L
    return ('<svg viewBox="0 0 124 124" role="img" aria-label="Ripartizione dei macro">'
            '<circle cx="62" cy="62" r="52" class="track"/>' + ''.join(segs) +
            '<text x="62" y="60" class="rk">%s</text><text x="62" y="76" class="rl">kcal</text></svg>'
            % nfmt(kcal))

def food_ul(pairs):
    li = ''.join('<li><span class="fn">%s</span><span class="fg">%s</span></li>'
                 % (e(n), fmt_g(n, g)) for n, g in pairs if round(g) > 0)
    return '<ul class="fl">%s</ul>' % li

def tot_div(t, cls='tot'):
    return ('<div class="%s"><span class="tk">%s kcal</span><span class="tm c">C %d</span>'
            '<span class="tm p">P %d</span><span class="tm f">G %d</span></div>'
            % (cls, nfmt(t[0]), round(t[1]), round(t[2]), round(t[3])))

REPORT = []

def build_meal(di, mi, target, templates):
    icon, nome = MEALS[mi]
    opts = []
    for oi, tpl in enumerate(templates):
        names, gr, t = solve(tpl, target)
        pairs = list(zip(names, gr))
        err = 100.0*(t[0]-target[0])/target[0]
        REPORT.append((DAYS[di]['iso'], nome, oi+1, target[0], t[0], err))
        opts.append('<div class="opt"><h4>Opzione %d</h4>%s%s</div>'
                    % (oi+1, food_ul(pairs), tot_div(t)))
    head = ('<button class="mh" onclick="toggleMeal(%d,%d)" aria-expanded="false">'
            '<span class="mi">%s</span><b>%s</b>'
            '<span class="mt">~%s kcal · C %d · P %d · G %d</span>'
            '<span class="chev">▸</span></button>'
            % (di, mi, icon, nome, nfmt(target[0]), round(target[1]), round(target[2]), round(target[3])))
    return ('<div class="meal" id="m%d-%d">%s<div class="mb"><div class="mbi">%s</div></div></div>'
            % (di, mi, head, ''.join(opts)))

def build_day(di, d):
    y, m, dd = [int(x) for x in d['iso'].split('-')]
    dt = datetime.date(y, m, dd)
    parts = []
    accent = {'crit': 'intensa', 'warn': 'media', 'good': 'leggera'}[d['dot']]
    parts.append('<article class="day %s" data-iso="%s">' % (accent, d['iso']))
    parts.append('<header class="dh"><div><h1>%s</h1><span class="tag %s">%s</span></div>'
                 '<span class="today" hidden>Oggi</span></header>'
                 % (e(d['titolo']), {'crit':'crit','warn':'warn','good':'good'}[d['dot']], e(d['tag'])))
    # fabbisogno
    parts.append('<section class="card need"><h2>🎯 Fabbisogno</h2><div class="ring">%s'
                 '<ul class="leg">'
                 '<li><i style="background:var(--carb)"></i><b>Carboidrati</b><span>%d g · %s g/kg</span></li>'
                 '<li><i style="background:var(--prot)"></i><b>Proteine</b><span>%d g · %s g/kg</span></li>'
                 '<li><i style="background:var(--fat)"></i><b>Grassi</b><span>%d g · %d%%</span></li>'
                 '</ul></div><p class="needn">%s</p></section>'
                 % (ring_svg(d['kcal'], d['C'], d['P'], d['G']),
                    d['C'], nfmt(d['cpk'],1), d['P'], nfmt(d['ppk'],1),
                    d['G'], round(100.0*d['G']*9/d['kcal']), d['needn']))
    # allenamento
    ss = []
    for s in d['sessions']:
        ss.append('<div class="sess"><div class="sh"><span class="si">%s</span>'
                  '<div><b>%s</b><span class="ss">%s</span></div>'
                  '<span class="skc">%s</span></div>'
                  '<div class="sm">%s</div><p class="sn">%s</p></div>'
                  % (s['icon'], e(s['nome']), e(s['sub']), s['kcal'],
                     ''.join('<span>%s</span>' % e(x) for x in s['metrics']), s['nota']))
    for cls, txt in d.get('flags', []):
        ss.append('<div class="flag %s">%s</div>' % (cls, txt))
    parts.append('<section class="card"><h2>💪 Allenamento</h2>%s</section>' % ''.join(ss))
    # insight
    if d.get('insight'):
        parts.append('<section class="card ins"><h2>🔎 Insight</h2>%s</section>'
                     % ''.join('<p class="rn">%s</p>' % p for p in d['insight']))
    # recupero
    if d.get('recovery'):
        rows = ''.join('<div class="rr"><span class="rl2">%s</span><span class="rv %s">%s</span>'
                       '<span class="rx">%s</span></div>' % (lbl, cls, val, xtr)
                       for lbl, cls, val, xtr in d['recovery']['rows'])
        parts.append('<section class="card rec"><h2>🧡 Recupero</h2><div class="rgrid">%s</div>'
                     '<p class="rn">%s</p></section>' % (rows, d['recovery']['nota']))
    # fueling
    fk = np.zeros(4)
    if d.get('fuel'):
        f = d['fuel']
        it = fuel_tot(f['intra']); pt = fuel_tot(f['post']); fk = it + pt
        blocks = ['<div class="fb"><h3>Pre</h3><p class="fnote">%s</p></div>' % f['pre']]
        if f['intra']:
            blocks.append('<div class="fb"><h3>Intra</h3><p class="fnote">%s</p>%s%s</div>'
                          % (f['intra_note'], food_ul(f['intra']), tot_div(it, 'tot sm')))
        else:
            blocks.append('<div class="fb"><h3>Intra</h3><p class="fnote">%s</p></div>' % f['intra_note'])
        if f['post']:
            blocks.append('<div class="fb"><h3>Post</h3><p class="fnote">%s</p>%s%s</div>'
                          % (f['post_note'], food_ul(f['post']), tot_div(pt, 'tot sm')))
        else:
            blocks.append('<div class="fb"><h3>Post</h3><p class="fnote">%s</p></div>' % f['post_note'])
        parts.append('<section class="card"><h2>%s</h2><p class="fsum">Totale fueling '
                     '<b>%s kcal</b> · C %d g · P %d g · G %d g, sottratti dal budget dei pasti.</p>'
                     '<div class="fgrid">%s</div></section>'
                     % (f['titolo'], nfmt(fk[0]), round(fk[1]), round(fk[2]), round(fk[3]),
                        ''.join(blocks)))
    # pasti
    mk = d['kcal'] - fk[0]; mC = d['C'] - fk[1]; mP = d['P'] - fk[2]; mG = d['G'] - fk[3]
    sp = SPLIT_HIGH if d['cpk'] >= 5.0 else SPLIT_LOW
    flags = []
    if d['cpk'] >= 5.0:
        flags.append('<div class="flag dev">⚠️ <b>Deviazione dichiarata sullo split dei pasti.</b> '
                     'A %s g/kg di carboidrati lo split 22/33/12/33 non si realizza con <b>una sola</b> '
                     'fonte di carboidrati a cena: i carboidrati vanno su <b>colazione 30%%</b> e '
                     '<b>pranzo 38%%</b> (cena 20%%), le proteine sulla <b>cena 44%%</b>. '
                     'Grassi 11/36/14/39 su tutti i giorni, perché la colazione ammessa ne ha poca.'
                     % nfmt(d['cpk'],1))
    else:
        flags.append('<div class="flag dev">⚠️ <b>Split dichiarato.</b> Carboidrati 25/35/13/27, '
                     'proteine 15/32/18/35, grassi 11/36/14/39: giornata a basso carboidrato, '
                     'le proteine si distribuiscono su pranzo e cena senza superare il 35%% a cena: '
                     'oltre, una <b>sola</b> fonte proteica non ci arriva.</div>')
    if fk[0] > 0:
        flags.append('<div class="flag dev">⚡ I pasti coprono <b>%s kcal</b>: il fueling '
                     '(%s kcal) è già sottratto.</div>' % (nfmt(mk), nfmt(fk[0])))
    meals = []
    tpls = [R.COLAZIONE,
            [R.PRANZO[di % 3], R.PRANZO[(di + 1) % 3]],
            R.SPUNTINO,
            [R.cena_template(di), R.cena_template_alt(di)]]
    for mi in range(4):
        tC, tP, tG = mC*sp['C'][mi], mP*sp['P'][mi], mG*sp['G'][mi]
        tk = tC*4 + tP*4 + tG*9
        meals.append(build_meal(di, mi, (tk, tC, tP, tG), tpls[mi]))
    parts.append('<section class="card mealsc"><h2>🍴 Pasti</h2>%s%s</section>'
                 % (''.join(flags), ''.join(meals)))
    parts.append('</article>')
    return ''.join(parts), (mk, mC, mP, mG)

arts = []; chains = []
for di, d in enumerate(DAYS):
    a, ch = build_day(di, d); arts.append(a); chains.append(ch)

# strip pillole
pills = []
for di, d in enumerate(DAYS):
    y, m, dd = [int(x) for x in d['iso'].split('-')]
    wd = GIORNI[datetime.date(y, m, dd).weekday()]
    pills.append('<button class="pill" data-i="%d" onclick="go(%d)"><span class="pd">%s</span>'
                 '<span class="pn">%d</span><i class="dot %s"></i></button>'
                 % (di, di, wd, dd, d['dot']))

MESI_ABBR = ['gen','feb','mar','apr','mag','giu','lug','ago','set','ott','nov','dic']
_d0 = datetime.date(*[int(x) for x in DAYS[0]['iso'].split('-')])
_d1 = datetime.date(*[int(x) for x in DAYS[-1]['iso'].split('-')])
if _d0.month == _d1.month:
    RANGE_SHORT = '%d\u2013%d %s' % (_d0.day, _d1.day, MESI_ABBR[_d0.month-1])
    RANGE_LONG  = '%d-%d %s' % (_d0.day, _d1.day, MESI[_d0.month-1])
else:
    RANGE_SHORT = '%d %s \u2013 %d %s' % (_d0.day, MESI_ABBR[_d0.month-1], _d1.day, MESI_ABBR[_d1.month-1])
    RANGE_LONG  = '%d %s \u2013 %d %s' % (_d0.day, MESI[_d0.month-1], _d1.day, MESI[_d1.month-1])

head = '''<!DOCTYPE html>
<html lang="it"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Training Hub &mdash; ''' + RANGE_LONG + '''</title>
<link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="512x512" href="icon-512.png">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
<link rel="manifest" href="site.webmanifest">
<meta name="theme-color" content="#173a5e">
<meta name="apple-mobile-web-app-title" content="Training Hub">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
'''

footer = '''<footer class="foot"><b>Metodo</b> — Fabbisogno = BMR Mifflin-St Jeor (75,7 kg · 183 cm · 29 anni → 1.761 kcal) × 1,3 + spesa della seduta.
<b>Bici</b>: NP inversa dal TSS di TrainingPeaks con <b>FTP 297 W</b> (Regola 18), +5% sulle uscite ≥ 3 h. Dove il TSS manca (26/09) si usa l'intensità dell'uscita gemella del 19/09; dove è corrotto (Regola 20) si ricostruisce dall'IF della pianificata. A consuntivo vale la misura Garmin.
<b>Corsa</b>: a consuntivo la misura COROS; a preventivo 1 kcal/kg/km <b>+8,4%</b> su strada (media di sette verifiche) (sul trail la formula sovrastima del 42%). <b>Nuoto</b>: <b>141 kcal/km</b>, aggiornato con la quinta misura del 23/09 (range 122-159). <b>Forza</b>: 309 kcal/h, misura COROS.
<b>Fonti</b>: COROS (corsa, nuoto, forza, sonno, passi, HRV, stress), Garmin (bici), TrainingPeaks (piano e TSS). Piano caricato fino al <b>02/10</b>.
<b>Valori nutrizionali</b>: stime standard tipo CREA/USDA, non verificate su database di prodotto. Tolleranza ±10-15%; tutte le ricette sono verificate programmaticamente entro ±15% sulle kcal del pasto. Pesi di riso e pasta <b>a crudo</b>. Una sola fonte proteica e un solo carboidrato per piatto; pancarrè, mai «pane»; marmellata al posto del miele.
<b>CTL/ATL/TSB</b> non disponibili (<code>tp_get_fitness</code> → HTTP 402): si usa il load ratio COROS, che resta un <b>limite inferiore</b> (~878 TSS di bici mai entrati nel modello).</footer>'''

doc = (head + STYLE + '<body>\n'
       '<header class="top"><div class="topin">\n'
       ' <div class="brand">Training Hub <span>· ' + RANGE_SHORT + '</span></div>\n'
       ' <div class="nav">\n'
       '  <button class="ib" onclick="step(-1)" aria-label="Giorno precedente">←</button>\n'
       '  <button class="ib" onclick="step(1)" aria-label="Giorno successivo">→</button>\n'
       '  <button class="ib" onclick="theme()" aria-label="Tema chiaro o scuro">◑</button>\n'
       ' </div></div>\n'
       ' <div class="strip" id="strip">' + ''.join(pills) + '</div>\n'
       '</header>\n'
       '<main class="wrap" id="main">' + ''.join(arts) + footer + '</main>\n'
       + re.sub(r'var DATA=\[[^\]]*\]',
                'var DATA=[' + ', '.join('"%s"' % d['iso'] for d in DAYS) + ']',
                SCRIPT, count=1)
       + '</body></html>\n')

import os
os.makedirs('/home/claude/out', exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(doc)

# ---------- verifica ----------
bad = [r for r in REPORT if abs(r[5]) > 15.0]
print("ricette: %d totali, %d fuori ±15%%" % (len(REPORT), len(bad)))
for r in bad: print("  FUORI", r)
print("\ncatene giornaliere (pasti, fueling escluso):")
ok = True
for di, d in enumerate(DAYS):
    mk, mC, mP, mG = chains[di]
    # somma effettiva opzione 1 di ogni pasto
    print("  %s  budget pasti %s kcal · C %d · P %d · G %d" %
          (d['iso'], nfmt(mk), round(mC), round(mP), round(mG)))
print("\nbytes:", len(doc))
