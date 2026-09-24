# -*- coding: utf-8 -*-
import re, html, sys
sys.path.insert(0,'/home/claude/gen')
from days import DAYS
s=open('/home/claude/out/index.html',encoding='utf-8').read()
arts=s[s.index('<main'):s.index('</main>')].split('<article class=')[1:]
assert len(arts)==7, len(arts)
ALLOWED_PROT={"Albume","Uova intere","Petto di pollo","Burger vegetale Lidl","Seitan","Tofu","Fiocchi di latte magri","Tonno al naturale","Ceci lessati","Lenticchie lessate"}
ALLOWED_CARB={"Pancarrè","Gallette di riso","Fette biscottate"}
ok=True
print("%-12s %-9s %8s %8s %7s | %7s %7s | %7s %7s" % ("giorno","catena","kcal t","kcal r","Δ%","C t","C r","P t","P r"))
for di,(a,d) in enumerate(zip(arts,DAYS)):
    meals=a.split('<div class="meal"')[1:]
    assert len(meals)==4, (d['iso'],len(meals))
    for opt in (0,1):
        K=C=P=G=0.0
        for m in meals:
            tots=re.findall(r'<span class="tk">([\d\.]+) kcal</span><span class="tm c">C (\d+)</span><span class="tm p">P (\d+)</span><span class="tm f">G (\d+)</span>',m)
            t=tots[opt]
            K+=float(t[0].replace('.','')); C+=int(t[1]); P+=int(t[2]); G+=int(t[3])
        # budget pasti = target giorno meno fueling
        fk=0.0;fc=0;fp=0
        mfs=re.search(r'Totale fueling <b>([\d\.]+) kcal</b> · C (\d+) g · P (\d+) g',a)
        if mfs: fk=float(mfs.group(1).replace('.','')); fc=int(mfs.group(2)); fp=int(mfs.group(3))
        tK=d['kcal']-fk; tC=d['C']-fc; tP=d['P']-fp
        dk=100*(K-tK)/tK; dc=100*(C-tC)/tC; dp=100*(P-tP)/tP
        bad = max(abs(dk),abs(dc),abs(dp))>10
        ok &= not bad
        print("%-12s opz.%d   %8.0f %8.0f %6.1f%% | %7.0f %7.0f | %7.0f %7.0f %s" %
              (d['iso'],opt+1,tK,K,dk,tC,C,tP,P,"❌" if bad else "✅"))
    # regole alimentari sulla cena
    cena=meals[3]
    for oi,blk in enumerate(cena.split('<div class="opt">')[1:]):
        foods=re.findall(r'<span class="fn">([^<]+)</span>',blk)
        foods=[html.unescape(f) for f in foods]
        np_=[f for f in foods if f in ALLOWED_PROT]; nc=[f for f in foods if f in ALLOWED_CARB]
        if len(np_)!=1 or len(nc)!=1:
            print("  ❌ CENA %s opz.%d proteine=%s carbo=%s" % (d['iso'],oi+1,np_,nc)); ok=False
    pranzo=meals[1]
    for oi,blk in enumerate(pranzo.split('<div class="opt">')[1:]):
        foods=[html.unescape(f) for f in re.findall(r'<span class="fn">([^<]+)</span>',blk)]
        np_=[f for f in foods if f in ALLOWED_PROT]
        if len(np_)!=1:
            print("  ❌ PRANZO %s opz.%d proteine=%s" % (d['iso'],oi+1,np_)); ok=False
print()
print("miele presente:", "miele" in s.lower())
print("'Pane' generico:", bool(re.search(r'<span class="fn">Pane</span>',s)))
print("sfondo:", re.search(r'--page:\s*([^;]+);',s).group(1))
print("data odierna in DATA:", '"2026-09-24"' in s)
print("ESITO:", "✅ tutto entro tolleranza" if ok else "❌ fuori tolleranza")
