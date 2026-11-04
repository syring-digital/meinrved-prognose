"""Aktuelle Messwerte für die Prognose: Pegel Edersee, Zufluss Schmittlotheim, Restabfluss Hann. Münden (Bonaforth + Letzter Heller)
und die WSA-Vorhersage samt Abgabeplan.

Nichts davon wird hier selbst abgerufen: Die zentrale Datensammlung (Repository meinrved-pegel, Lauf kurz vor diesem) holt PEGELONLINE
und das WSA-PDF einmal und veröffentlicht live.json. Dieses Skript lädt nur die Datei, prüft ihr Alter und schreibt ausgabe/live.json;
daten/bfg/pegelonline_rest.csv (Restabfluss Hann. Münden = Bonaforth + Letzter Heller) wird fortgeschrieben."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, DATA, fetch_url

SRC = os.environ.get('PEGEL_LIVE') or 'https://syring-digital.github.io/meinrved-pegel/live.json'
MAX_ALTER = dt.timedelta(hours=14)     # zwei Läufe je Tag; älter heißt: die Sammlung ist ausgefallen

if __name__ == '__main__':
    out = json.loads(fetch_url(SRC, timeout=30))
    alter = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(out['abgerufen'])
    if alter > MAX_ALTER:
        raise SystemExit(f'live.json ist {alter} alt (Grenze {MAX_ALTER}): Lauf der Datensammlung prüfen')
    rest = out['hmue_tage']
    po = os.path.join(DATA, 'bfg', 'pegelonline_rest.csv')
    os.makedirs(os.path.dirname(po), exist_ok=True)
    old = {}
    if os.path.exists(po):
        for line in open(po).read().splitlines()[1:]:
            k, v = line.split(','); old[k] = float(v)
    old.update(rest)
    with open(po, 'w') as fh:
        fh.write('date,Q_hmue\n'); [fh.write(f'{k},{old[k]}\n') for k in sorted(old)]
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, 'live.json'), 'w'), indent=1)
    print('Edersee', out['see']['letzter'], '| Schmittlotheim', out['schmittlotheim']['letzter'], f"({out['schmittlotheim']['alter_stunden']} h alt)")
    print('Hann. Münden (Bonaforth + Letzter Heller), letzte Tage:', list(rest.items())[-3:])
    print('WSA:', out['wsa'])
