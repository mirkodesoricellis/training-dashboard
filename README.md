# training-dashboard

Dashboard settimanale allenamento & nutrizione, generata da Claude (Cowork) a
partire dai dati di COROS, Garmin e TrainingPeaks, pubblicata qui come
GitHub Pages: **https://mirkodesoricellis.github.io/training-dashboard/**

## Come funziona

1. Ogni sera una routine schedulata su Claude Cowork ingerisce i dati freschi
   e rigenera `index.html`, scrivendolo su questo Mac in questa cartella
   (via bridge desktop — richiede l'app desktop di Claude aperta).
2. Un job locale (`launchd`, vedi `install.sh`) rileva la modifica e fa
   `git commit` + `git push` in automatico.
3. Il telefono (o qualsiasi dispositivo) apre l'URL sopra e vede sempre
   l'ultima versione — nessun salvataggio manuale.

La logica di generazione della dashboard (regole sui pasti, formato,
metodologia calorica) vive nel progetto Claude "Training Hub", nel file
`claude/dashboard-generation-spec.md` — non in questo repo.

## Setup su una macchina nuova

```
git clone https://github.com/mirkodesoricellis/training-dashboard.git
cd training-dashboard
./install.sh
```

Lo script chiede un GitHub token (fine-grained, permesso "Contents: Read and
write" solo su questo repo — crealo su
https://github.com/settings/personal-access-tokens/new) e configura tutto:
remote con credenziali, script di push, job `launchd` schedulato alle 18:10
(personalizzabile con le variabili d'ambiente `PUSH_HOUR` / `PUSH_MINUTE`
prima di lanciare lo script).

Rilancia `./install.sh` in qualsiasi momento per rigenerare il job (es. dopo
aver ruotato il token).

## File

- `index.html` — la dashboard pubblicata (sovrascritta ogni sera)
- `install.sh` — setup/riparazione one-shot del job di auto-push
- `auto-push.sh` — generato da install.sh, gira via launchd
