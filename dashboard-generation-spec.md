# Spec — Dashboard settimanale Allenamento & Nutrizione

Istruzioni per rigenerare la dashboard HTML da zero ogni volta che i dati di allenamento vengono aggiornati (ingestion giornaliera). Chi esegue questo task parte da una sessione nuova senza memoria della chat originale: questo file deve bastare da solo.

## Dati di partenza
Leggi dal progetto Training Hub (`project_read` / `project_search`):
- `claude/upcoming-workouts.md` — allenamenti pianificati prossimi giorni (TrainingPeaks/COROS)
- `claude/coros-daily-metrics.md` — recupero, HRV, RHR, sonno, stress
- `claude/coros-activity-log.md` — attività completate
- `claude/ingestion-status.md` — stato ultimo ingestion

Se servono dati più freschi o mancanti, usa i tool MCP diretti (COROS, TrainingPeaks via `mcp__remote-devices__trainingpeaks__*`, Garmin via `mcp__remote-devices__garmin__*`) prima di costruire la dashboard.

> Nota (pipeline cloud): quando questo file viene eseguito dentro `scripts/generate_dashboard.py` in GitHub Actions, i dati sopra NON sono disponibili (niente Projects tool, niente MCP locali). In quel contesto i dati arrivano già pronti nel JSON passato come messaggio utente (attività, wellness, planned workouts da intervals.icu, target macro già calcolati in Python) — usa quelli, non provare a chiamare tool.

## Profilo atleta
Mirko De Soricellis — 75.7 kg, 183 cm, 29 anni, uomo. FTP bici ~261W (verifica se aggiornato). BMR Mifflin-St Jeor ≈ 1761 kcal. Se il peso cambia nei dati, ricalcola BMR.

## Regola chiave: attività duplicate stesso giorno
Se in un giorno risultano **due sessioni della stessa disciplina** (es. due voci "Bike"), sono **alternative** (tipicamente outdoor vs rulli/indoor), NON da sommare. Usa solo la sessione più lunga/principale per il target calorico, e segnala l'alternativa in una nota nel giorno (campo `altNote` nel codice).

## Metodo di stima fabbisogno giornaliero
kcal giorno = BMR × 1.3 (attività base) + spesa energetica sessione.
- Bici: kcal ≈ (TSS/100) × FTP(W) × 3600/1000 (kJ meccanici ≈ kcal metabolici)
- Corsa: kcal ≈ 1 kcal/kg/km × peso × distanza
- Nuoto/Forza: stima da RPE/durata, moderata

Macro giorno:
- Proteine: 1.8 g/kg (2.0 g/kg nei giorni forza)
- Carboidrati: 3.5 g/kg (rest) fino a 8 g/kg (giorni bici lunghi/intensi)
- Grassi: kcal residue / 9

Split sui pasti: Colazione 22% · Pranzo 33% · Spuntino 12% · Cena 33% (kcal e macro).

## Metodologia stima calorica — nota di trasparenza
Il fabbisogno giornaliero (BMR × 1.3 + spesa sessione) è un calcolo standard verificabile (Mifflin-St Jeor + TSS/FTP o kcal/kg/km), non stimato a caso. I valori nutrizionali dei singoli alimenti nelle ricette sono invece **stime standard/generiche** (tipo tabelle USDA/CREA), non verificate su un database di prodotto reale come OpenFoodFacts — per alimenti confezionati specifici (marca) possono scostarsi di un 10-20%. Se possibile, verifica su OpenFoodFacts (https://world.openfoodfacts.org, ricerca prodotto — l'endpoint API diretto può essere bloccato da robots.txt, usare WebSearch o la pagina prodotto) i valori dei prodotti confezionati abituali dell'utente (es. corn flakes senza zuccheri, burger vegetale Lidl, marca whey) per aumentare la precisione; altrimenti dichiara sempre che si tratta di stime generiche con tolleranza ±10-15%.

## Fueling sportivo (solo se sessione singola >60 min o TSS alto)
Aggiungi sezione Pre / Intra / Post con quantità esatte (non range):
- Pre (2–3h prima): pasto ricco di carbo, povero di fibre/grassi
- Intra: gel (25g carbo cad.) + bevanda isotonica (sodio), quantità proporzionali alla durata (~60-90g carbo/ora per sessioni intense >90min)
- Post (entro 30-45min): whey + carbo ad alto IG
- Supplementi: caffeina pre (2-3mg/kg) se sessione mattutina, creatina 5g/die continuativa nei periodi di alto volume

### Fueling sportivo — macro obbligatori per fase
Ogni blocco Pre / Intra / Post nella sezione fueling deve mostrare, oltre alla lista alimenti con quantità esatte, anche il **totale macro della fase** (kcal, carbo, proteine, grassi), nello stesso stile dei box "totale ricetta" dei pasti principali (campi `preTotals`/`intraTotals`/`postTotals` nell'oggetto `fuel`, resi con `fuelTotalsHtml()`). Se una fase non prevede alimenti a sé stanti (es. "Pre = il pasto principale già pianificato" oppure "Intra = solo acqua"), ometti il box macro per quella fase (`null`, nessun numero fittizio).

## Insight allenamento (obbligatorio nei giorni con attività completata)
Per ogni giorno in cui il payload riporta almeno un'attività completata (`activities_completed` non vuoto, o `activities` con `completed: true` a seconda della struttura JSON), genera un breve blocco "Insight" (3-5 frasi, non un elenco puntato lunghissimo) che commenta la sessione in modo concreto, non generico. Usa i dati numerici disponibili nel payload per motivare ogni osservazione, ad esempio:
- confronta il carico della sessione (`training_load`/TSS) e la durata/distanza con le sessioni recenti simili, se i dati storici sono disponibili;
- collega lo stato di recupero (HRV, RHR, sonno, stress dei giorni precedenti) all'intensità della sessione appena fatta — es. "HRV sotto media e RHR elevato ieri: oggi hai comunque tenuto intensità alta, tienilo d'occhio nei prossimi 2-3 giorni";
- segnala pattern utili (es. sessione outdoor vs indoor, ritmo/passo/potenza medi fuori norma rispetto al solito, giorno con doppia sessione della stessa disciplina — vedi regola duplicati);
- se il payload include un target pianificato (`planned_workouts`/`planned_workouts_trainingpeaks`) per lo stesso giorno, confronta il fatto con il pianificato (es. TSS pianificato vs reale, durata pianificata vs reale) e commenta scostamenti significativi.

Evita frasi vuote tipo "ottimo lavoro" o "continua così" senza numeri a supporto: ogni insight deve citare almeno un dato concreto dal payload. Se un giorno non ha attività completate (solo pianificate o rest day), ometti del tutto il blocco Insight per quel giorno — non inventare contenuto.

Posiziona il blocco Insight nella vista del giorno, in una card dedicata subito sotto il riepilogo attività/carico e prima dei blocchi pasto.

## Alimenti reali dell'utente — USA SOLO QUESTI
**Colazione** (2 opzioni, alternative):
- Opzione 1: Avena + Latte di soia + Burro di arachidi
- Opzione 2: Latte di soia + Corn flakes senza zuccheri + Whey (NIENTE burro di arachidi qui, resta un pasto pulito cereali+shake)

**Pranzo**: Riso o Pasta (**peso a CRUDO, mai cotto** — dividi il peso cotto per 2.8 se hai calcolato su cotto per il riso, per 2.3 per la pasta) + **UNA SOLA fonte proteica/legume a scelta tra**: tonno, ceci, lenticchie (mai due legumi insieme nello stesso piatto) + eventuale mais come contorno + grana come condimento facoltativo + olio EVO.

**Spuntino**: libero, usa alternative semplici e pulite (yogurt greco, frutta, frutta secca, gallette, fiocchi di latte magri) — 1-2 opzioni.

**Cena**: **UNA SOLA fonte proteica principale a scelta tra**: albume, uova, petto di pollo, burger vegetale Lidl, seitan, tofu, fiocchi di latte + **UN SOLO tipo di carboidrato** (pancarrè, oppure gallette, oppure fette biscottate — MAI due insieme) + verdure abbondanti + olio EVO + condimento facoltativo (ketchup o maionese, non entrambi).

⚠️ REGOLA CRITICA: mai combinare più fonti proteiche diverse nello stesso piatto (es. mai albume+seitan, mai uova+seitan+fette), e mai più tipi di pane/carboidrato nello stesso pasto (es. mai pancarrè+fette biscottate insieme). Un pasto realistico ha UNA proteina e UNA base di carboidrati, non un accozzaglia per far tornare i numeri.

## Preferenze alimentari — correzioni utente
- **Pancarrè, non "pane" generico**: l'utente mangia abitualmente pancarrè (pane in cassetta a fette). Nel testo delle ricette scrivi sempre "Pancarrè", non "Pane". I valori nutrizionali standard (~265 kcal, 49g carb, 8g proteine, 3.3g grassi per 100g) sono comunque una buona approssimazione per il pancarrè.
- **Niente miele**: l'utente non gradisce il miele. Non usarlo mai come fonte di zuccheri/dolcificante nelle ricette (colazione, spuntino, pre-workout). Usa **marmellata** come alternativa (quantità leggermente superiori a parità di carboidrati: marmellata ha ~250 kcal/65g carb per 100g contro miele ~304 kcal/82g carb per 100g, quindi per pareggiare i carbo servono grammi di marmellata pari a circa 1.25× i grammi di miele che si userebbero).

Ogni pasto mostra: target macro "circa" (kcal/C/P/F) + 1-2 opzioni con grammi esatti e il totale macro effettivo della ricetta proposta (tolleranza accettabile ±10-15%, non serve precisione al grammo).

## Formato output — HTML unico, mobile-first
File singolo self-contained (CSS+JS inline). Caratteristiche:
- **Sfondo bianco puro** (`--page` e `--surface-1`/`--surface-2` a `#ffffff` in light mode; `--surface-3` un grigio chiarissimo `#f6f6f5` solo per dare profondità ai blocchi pasto annidati). In dark mode restano i toni scuri esistenti (`#101010`/`#1a1a19`).
- Vista **un giorno alla volta**, frecce ← → per navigare, pallini cliccabili, frecce tastiera
- **Il giorno mostrato di default deve essere calcolato dinamicamente dalla data reale**, non hardcodato: ogni giorno ha un campo `iso` (es. `"2026-08-18"`), e all'avvio lo script calcola `new Date()` lato browser e cerca il giorno con `iso` corrispondente (`DATA.findIndex(d => d.iso === todayISO())`). Se la data odierna cade fuori dai 7 giorni pianificati, fallback al primo giorno. Il badge "Oggi" segue lo stesso indice calcolato, non un indice fisso.
- **Pasti espandibili al tocco** ("esplodibili"): ogni blocco pasto (Colazione/Pranzo/Spuntino/Cena) mostra di default solo intestazione + target macro compatto (riga singola, con una chevron ▸ che ruota); il dettaglio con le opzioni/ricette complete si apre/chiude cliccando sull'intestazione (`toggleMeal(idx)`, classe `.open` sul contenitore, transizione su `max-height`). Nessuna opzione visibile finché non si espande.
- Meta tag per installazione home screen mobile: `apple-mobile-web-app-capable`, `mobile-web-app-capable`, `theme-color` (`#173a5e`), safe-area insets. **Icona home screen definita — includi sempre questi tag esatti nell'`<head>`, non generarne di nuovi:**

```html
<link rel="apple-touch-icon" sizes="180x180" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAIAAACyr5FlAAACaElEQVR4nO3cMUtVcRyA4bz5CRqSaGwMgmhKaG1qKMIxoU3QpF1QhKDRSZCaWluawi9QNLpE9A0UGvoESnv00r1XOucSzzMezuH/G15+w384Syur61fgTyZjD8DiEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdpeYAzDvc2nj68P8BBM/ly8v3J1uvfHt64fu3kw8E0n59fXNx88Hzu0+/dvvXxze40b57++Hn38cu5D7oMm4MkDpI4SOIgiYMkDpI4SOIgiYMkDtIQ1+eb+0eb+0ezfvXi2aOdjbVp3nx//Gn71dvZ5+IvbA6SOEjiIImDJA6SOEjiIImDNMQl2H/p6mRy9vnd2FP8WzYHSRwkcZDEQRIHSRwkcZDEQRIHSRwk1+dzGuwXDCOyOUjiIImDJA6SOEjiIImDJA6SOEjiIImDJA6SOEjiIImDJA6SOEjiIImDJA6SOEjiIImDtLSyuj72DCwom4MkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SOIgiYMkDpI4SMtf73wbewYWlM1BEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRBEgdJHCRxkMRB+gXpxygEWLUUZwAAAABJRU5ErkJggg==">
<link rel="icon" type="image/png" sizes="512x512" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAIAAAB7GkOtAAAH1klEQVR4nO3XsUrWYRyG4Yw/JM2CDU05ftAiLSItDZ2Dg0vgIYiTNDQ4GDQIwQc1RYMQtXxjW2NLEOEghZOn0REEJuYr3de1v7zPdvNbWt3YvgVAz+3RAwAYQwAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiptEDbq6fn+d3l++MXsFFHb79dPjm4+XePn40O361e7V7Lmhza+/07HzI15ezPltbzPeHfP302fNvJ7+GfP2/cgEARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABETaMH3FwPnuyMnvBHXz+8vH9v5fr/PXq3ePH6+Pr/Bf4FFwBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAEDUNHoApH15fzB6Al0uAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgKhp9ABI29zaOz07H73iL6zP1hbz/dEruBouAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIgSAIAoAQCIEgCAKAEAiBIAgCgBAIhaWt3YHr0BgAFcAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQNX1/+GP0BgAGcAEARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQJQAAEQJAECUAABECQBAlAAARAkAQNRvf/sn/M9CSL0AAAAASUVORK5CYII=">
<link rel="icon" type="image/png" sizes="32x32" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAmklEQVR4nGMUt4pjoCVgoqnpoxaMWjBqAQMDAwMDC6bQrZ0z+Hg4McUv3XzgllS/d2Gztorc2l3HsxtnQMTXT6m0NNTYcfhcQsVEoixQc8+AMLbNrjPSUt6492R63TSyfTAs44AYEOxmGexmSYxKMn2wdtdxCet4CDp+/gb1LSAeDH0LGEerzFELRi0YBhawXNG7RlMLhn4QAQCTUiSohY/mdwAAAABJRU5ErkJggg==">
<meta name="theme-color" content="#173a5e">
```

  Icona: sfondo pieno blu scuro `#173a5e` (mai trasparente — iOS renderizza la trasparenza come sfondo nero/bianco sporco sull'home screen, causa del problema segnalato), barra accento arancio `#eb6834` in basso, testo "TH" bianco centrato. Se in futuro serve rigenerarla (es. altro nome/branding), mantieni sempre uno sfondo opaco a tinta unita: mai PNG con canale alpha trasparente per le icone home screen.
- Palette dataviz: carbo blu (`#2a78d6`/dark `#3987e5`), proteine arancio (`#eb6834`/dark `#d95926`), grassi verde (`#1baf7a`/dark `#199e70`), status good/warning/serious/critical (`#0ca30c`/`#fab219`/`#ec835a`/`#d03b3b`) — palette validata, non cambiare gli hex
- Dark mode automatico (`prefers-color-scheme`) + toggle manuale
- Card con ombre morbide leggere, accento colorato per intensità giornata, icone sport (🏊🏃🚴🏋️) e pasto (☀️🍽️🍎🌙)
- Footer con metodologia e fonti dati

## Pubblicazione

### Pipeline cloud autonoma (nuova, in verifica dal 2026-08-18)
La dashboard può essere generata e pubblicata interamente da GitHub Actions, senza Mac acceso né sessione Cowork. Vedi il documento di progetto `claude/cloud-pipeline-setup.md` per l'architettura completa (intervals.icu + tp2intervals + Strava + `.github/workflows/dashboard.yml` + `scripts/generate_dashboard.py`). Finché non è verificata end-to-end, resta **fallback** la pipeline locale descritta sotto — non disattivarla.

### Pipeline locale (fallback, launchd sul Mac — invariata)
La dashboard è pubblicata live su **https://mirkodesoricellis.github.io/training-dashboard/**, che si aggiorna da sé sul telefono dell'utente (nessun salvataggio manuale). La pipeline:

1. Scrivi il file HTML nella working directory di questa sessione (self-contained come sopra).
2. `SendUserFile` per consegnarlo in chat (status: "proactive", display: "render") — utile come conferma/backup.
3. Copia il file sul Mac dell'utente nella cartella locale collegata al repo GitHub Pages, usando `mcp__remote-devices__device_commit_files` con `devicePath: "~/training-dashboard/index.html"`. Questo richiede il device bridge connesso (desktop app aperta) — se non disponibile in questa sessione schedulata, salta silenziosamente questo passaggio (va bene, il file resta comunque in chat come fallback; l'auto-push locale del giorno semplicemente non troverà nulla di nuovo).
4. **Non serve fare il push git da questa sessione** — un job locale (`launchd`, script `~/training-dashboard/auto-push.sh`, con `RunAtLoad` oltre all'orario fisso 18:10) sul Mac dell'utente fa commit+push automaticamente. Il push da questa sessione cloud NON funziona comunque: un proxy di sicurezza del sandbox blocca i push verso repository esterni non pre-autorizzati — non tentare `git push` da qui, è un vicolo cieco già verificato.
5. Se il device bridge non è connesso per più giorni di fila, avvisa l'utente nel messaggio di chat che la pubblicazione su GitHub Pages non si è aggiornata (il file in chat resta comunque disponibile).
6. Aggiorna anche l'artifact persistito Cowork (id: `dashboard-settimana-training-nutrition`) con `update_artifact` se il device bridge è connesso — passo opzionale, non bloccante.
7. Il repo GitHub (`training-dashboard`) contiene anche `install.sh` e `README.md` per reinstallare il job locale su un'altra macchina — non toccarli in questa pipeline, riguardano solo il setup locale, non la generazione della dashboard.
8. Aggiorna questo spec se emergono correzioni ai dati/preferenze/formato (es. nuove alternative alimentari o richieste di design comunicate dall'utente in chat) — mantienilo allineato nel tempo.

### ⚠️ Manutenzione: due copie di questo file
Questo spec esiste in **due posti**: qui nel progetto Training Hub (fonte di verità per le sessioni Cowork interattive) e come `dashboard-generation-spec.md` alla radice del repo `training-dashboard` (letto da `scripts/generate_dashboard.py` nella pipeline cloud, che non ha accesso al progetto Claude). Se aggiorni regole nutrizionali/formato qui, copia lo stesso contenuto anche nel repo (via device bridge o commit manuale), altrimenti la pipeline cloud userà regole vecchie.
