#!/bin/bash
# Setup/riparazione automatica: repo locale + job di auto-push su GitHub Pages.
# Uso su una macchina nuova:
#   git clone https://github.com/<user>/<repo>.git
#   cd <repo>
#   ./install.sh
# Rilancialo in qualsiasi momento per rigenerare il job (es. dopo aver
# ruotato il token, o cambiato orari di push).

set -e

GITHUB_USER="${GITHUB_USER:-mirkodesoricellis}"
REPO_NAME="${REPO_NAME:-training-dashboard}"
LOCAL_DIR="${LOCAL_DIR:-$HOME/$REPO_NAME}"
# Orari di push nel formato HH:MM separati da virgola.
PUSH_TIMES="${PUSH_TIMES:-09:40,14:10,18:10}"

echo "== Setup dashboard auto-pubblicata =="
echo "Repo:     ${GITHUB_USER}/${REPO_NAME}"
echo "Cartella: ${LOCAL_DIR}"
echo "Orari push: ${PUSH_TIMES}"
echo

# 1. Clona il repo (pubblico, non serve token per leggerlo) se non esiste già
if [ ! -d "$LOCAL_DIR/.git" ]; then
  echo "Clono il repo in ${LOCAL_DIR}..."
  git clone "https://github.com/${GITHUB_USER}/${REPO_NAME}.git" "$LOCAL_DIR"
else
  echo "Repo già presente in ${LOCAL_DIR}, salto il clone."
fi

cd "$LOCAL_DIR"

# 2. Serve un token con permesso di scrittura per poter pushare.
#    Non viene MAI salvato in un file tracciato da git (il repo è pubblico).
#    Se il remote ha già delle credenziali configurate (rilanci successivi),
#    salta la richiesta.
CURRENT_REMOTE="$(git remote get-url origin 2>/dev/null || echo '')"
if [[ "$CURRENT_REMOTE" == *"@github.com"* ]]; then
  echo "Remote già configurato con credenziali di push, salto la richiesta del token."
else
  if [ -z "$GITHUB_TOKEN" ]; then
    echo
    echo "Serve un GitHub Personal Access Token (fine-grained, scope 'Contents: Read and write' solo su questo repo)."
    echo "Crealo su: https://github.com/settings/personal-access-tokens/new"
    read -srp "Incolla il token: " GITHUB_TOKEN
    echo
  fi
  git remote set-url origin "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
  echo "Remote configurato con le credenziali di push."
fi

# 3. Script di auto-push: commit+push solo se qualcosa è cambiato.
#    Se un'altra pipeline (es. GitHub Actions) ha pushato nel frattempo e la
#    storia locale è divergente, si riallinea a origin/main (senza toccare i
#    file su disco, che sono comunque riscritti freschi ad ogni run) prima
#    di ricommittare, così il push resta sempre un fast-forward pulito.
cat > "$LOCAL_DIR/auto-push.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
git fetch origin --quiet 2>/dev/null || true
if git rev-parse --verify origin/main >/dev/null 2>&1; then
  git reset --mixed origin/main --quiet
fi
git add -A
git diff --cached --quiet && exit 0
git commit -m "Aggiornamento automatico $(date '+%Y-%m-%d %H:%M')" -q
git push -q
EOF
chmod +x "$LOCAL_DIR/auto-push.sh"
echo "auto-push.sh creato (con auto-riallineamento a origin/main)."

# 4. Job launchd (macOS) schedulato a tutti gli orari indicati in PUSH_TIMES
PLIST_LABEL="com.${GITHUB_USER}.${REPO_NAME}-push"
PLIST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
mkdir -p "$HOME/Library/LaunchAgents"

INTERVALS_XML=""
IFS=',' read -ra TIMES_ARR <<< "$PUSH_TIMES"
for t in "${TIMES_ARR[@]}"; do
  h="${t%%:*}"
  m="${t##*:}"
  h=$((10#$h))
  m=$((10#$m))
  INTERVALS_XML="${INTERVALS_XML}
        <dict>
            <key>Hour</key>
            <integer>${h}</integer>
            <key>Minute</key>
            <integer>${m}</integer>
        </dict>"
done

cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${LOCAL_DIR}/auto-push.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>${INTERVALS_XML}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOCAL_DIR}/push.log</string>
    <key>StandardErrorPath</key>
    <string>${LOCAL_DIR}/push-error.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Job launchd installato e caricato (${PLIST_LABEL})."
echo "RunAtLoad attivo: scatta anche ad ogni avvio/login del Mac, oltre agli"
echo "orari fissi — così recupera da solo un push rimasto in sospeso se il"
echo "Mac era spento a uno degli orari programmati."

echo
echo "== Fatto =="
echo "Dashboard live: https://${GITHUB_USER}.github.io/${REPO_NAME}/"
echo "Il bridge desktop di Claude scrive ${LOCAL_DIR}/index.html quando serve"
echo "(richiede l'app desktop di Claude aperta in quel momento). Questo job"
echo "pusha in automatico agli orari: ${PUSH_TIMES}, e ad ogni avvio del Mac."
