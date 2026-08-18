#!/bin/bash
# Setup/riparazione automatica: repo locale + job di auto-push su GitHub Pages.
# Uso su una macchina nuova:
#   git clone https://github.com/<user>/<repo>.git
#   cd <repo>
#   ./install.sh
# Rilancialo in qualsiasi momento per rigenerare il job (es. dopo aver
# ruotato il token, o cambiato orario di push).

set -e

GITHUB_USER="${GITHUB_USER:-mirkodesoricellis}"
REPO_NAME="${REPO_NAME:-training-dashboard}"
LOCAL_DIR="${LOCAL_DIR:-$HOME/$REPO_NAME}"
PUSH_HOUR="${PUSH_HOUR:-18}"
PUSH_MINUTE="${PUSH_MINUTE:-10}"

echo "== Setup dashboard auto-pubblicata =="
echo "Repo:     ${GITHUB_USER}/${REPO_NAME}"
echo "Cartella: ${LOCAL_DIR}"
echo "Orario push: ${PUSH_HOUR}:$(printf '%02d' "$PUSH_MINUTE")"
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
if [ -z "$GITHUB_TOKEN" ]; then
  echo
  echo "Serve un GitHub Personal Access Token (fine-grained, scope 'Contents: Read and write' solo su questo repo)."
  echo "Crealo su: https://github.com/settings/personal-access-tokens/new"
  read -srp "Incolla il token: " GITHUB_TOKEN
  echo
fi
git remote set-url origin "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
echo "Remote configurato con le credenziali di push."

# 3. Script di auto-push: commit+push solo se index.html è cambiato
cat > "$LOCAL_DIR/auto-push.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
git add -A
git diff --cached --quiet && exit 0
git commit -m "Aggiornamento automatico $(date '+%Y-%m-%d %H:%M')" -q
git push -q
EOF
chmod +x "$LOCAL_DIR/auto-push.sh"
echo "auto-push.sh creato."

# 4. Job launchd (macOS) schedulato all'orario scelto
PLIST_LABEL="com.${GITHUB_USER}.${REPO_NAME}-push"
PLIST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
mkdir -p "$HOME/Library/LaunchAgents"
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
    <dict>
        <key>Hour</key>
        <integer>${PUSH_HOUR}</integer>
        <key>Minute</key>
        <integer>${PUSH_MINUTE}</integer>
    </dict>
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

echo
echo "== Fatto =="
echo "Dashboard live: https://${GITHUB_USER}.github.io/${REPO_NAME}/"
echo "Il bridge desktop di Claude scriverà ${LOCAL_DIR}/index.html ogni sera;"
echo "questo job lo pusha in automatico alle ${PUSH_HOUR}:$(printf '%02d' "$PUSH_MINUTE")."
