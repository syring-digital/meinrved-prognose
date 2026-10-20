#!/bin/sh
# Überträgt den Stand von Tools/Prognose in das GitHub-Repository syring-digital/meinrved-prognose
# (Spiegel außerhalb von iCloud). Nur Dateien, die nicht per .gitignore ausgeschlossen sind.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(git -C "$SRC" rev-parse --show-toplevel)"
DST="$HOME/Library/Application Support/MeinRVED-Prognose/repo"
if [ ! -d "$DST/.git" ]; then
  git clone -q https://github.com/syring-digital/meinrved-prognose.git "$DST"
  # öffentliches Repository: anonyme GitHub-Adresse statt privater E-Mail
  git -C "$DST" config user.name "Jakob Syring"
  git -C "$DST" config user.email "345268148+syring-digital@users.noreply.github.com"
fi
cd "$ROOT"
git ls-files --cached --others --exclude-standard -- Tools/Prognose | sed 's|^Tools/Prognose/||' > /tmp/meinrved-prognose-dateien
cd "$DST"
git ls-files | grep -vxF -f /tmp/meinrved-prognose-dateien | while read -r f; do git rm -q -- "$f"; done
rsync -a --files-from=/tmp/meinrved-prognose-dateien "$SRC"/ "$DST"/
git add -A
if git diff --cached --quiet; then echo "Keine Änderungen."; exit 0; fi
git commit -q -m "${1:-Stand aus Mein RVED übernommen}"
git push -q origin HEAD:main
echo "Übertragen: $(git log --oneline -1)"
