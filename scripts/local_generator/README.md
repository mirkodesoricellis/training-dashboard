# Generatore dashboard locale (pipeline Cowork)

Ricostruito da zero tre volte perché non persisteva fra le sessioni. **Da qui in avanti vive nel repo.**

| File | Ruolo |
|---|---|
| `foods.py` | Database alimenti (per 100 g / 100 ml). Solo gli alimenti ammessi dallo spec. |
| `recipes.py` | Template dei pasti con i vincoli: una proteina e un carboidrato per piatto, pesi a crudo. |
| `solver.py` | `lsq_linear` con bound sulle grammature: risolve le quantità dato il target macro del pasto. |
| `days.py` | **L'unico file da riscrivere a ogni run**: i 7 giorni, sedute, insight, recupero, fueling, target macro. |
| `build.py` | Emette `index.html`. Riusa `<style>` e `<script>` **verbatim** dall'`index.html` pubblicato. |
| `verify.py` | Controlla le 56 ricette (±15% sulle kcal) e le 14 catene giornaliere (±10% su kcal/C/P), più le regole alimentari. |
| `render_check.py` | Render headless 390×844: giorno di default, sfondo, overflow orizzontale, errori di console. |

## Uso

```
SRC=<index.html attuale>  # build.py lo legge per riusare CSS e JS
python3 build.py && python3 verify.py && python3 render_check.py
```

`build.py` e `render_check.py` hanno i path in testa al file: aggiornarli se cambia la sessione.
Il solver gira con numpy + scipy; il render con playwright/chromium.

## Regole implementate

- Split dei pasti **deviato** sui giorni ≥ 5 g/kg di carboidrati: C 30/38/12/20, P 15/28/13/44, G 11/36/14/39.
  Sui giorni a basso carboidrato: C 25/35/13/27, P 15/24/13/48, G 11/36/14/39. La deviazione è dichiarata in pagina.
- Il fueling è **sottratto** dal budget dei pasti (kcal e macro) e la sottrazione è dichiarata in pagina.
- Niente miele (marmellata), «Pancarrè» mai «Pane», pesi di riso e pasta a crudo.
- Icone: path **relativi**, mai `data:` URI (iOS li ignora).
