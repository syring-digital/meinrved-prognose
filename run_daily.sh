#!/bin/sh
# Täglicher Rechenlauf (07:30 und 13:30): neue Messwerte, DWD-Prognose, Pegel und WSA-Plan holen,
# Ensemble rechnen und die App-Datei ausgabe/app/prognose.json schreiben. Bricht beim ersten Fehler ab,
# damit nie eine halbe Datei veröffentlicht wird.
set -e
cd "$(dirname "$0")"
python3 fetch.py && python3 parse.py
python3 climate.py
python3 dwd_forecast.py
python3 live.py
python3 forecast3.py
python3 publish.py
# Archiv der Eingänge für spätere Prüfung der Wochenprognose
d=$(date +%Y-%m-%d_%H%M); mkdir -p archiv/$d
cp ausgabe/live.json ausgabe/dwd_eps.json ausgabe/app/prognose.json archiv/$d/
