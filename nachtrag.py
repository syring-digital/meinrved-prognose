"""Ergänzt daten/hist.csv (eingefrorener Verlauf, siehe fetch.py) um die Tage danach.
Quelle ist tageswerte.json der zentralen Datensammlung (Repository meinrved-pegel): Pegel Edertalsperre und Zufluss Schmittlotheim
(WSV PEGELONLINE, Wert um 07:00 Uhr) und die geplante Abgabe (WSA Weser). Es gibt dafür genau einen Abruf, nichts wird hier doppelt geholt.
Der Inhalt wird aus dem Pegel mit der Höhen-Inhalt-Kurve gerechnet. Fehlt die Abgabe eines Tages, gilt der letzte bekannte Wert.
Lizenz der Pegeldaten: DL-DE->Zero-2.0."""
import os, sys, csv, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import HIST, vol, fetch_url

SRC = os.environ.get('PEGEL_TAGESWERTE') or 'https://syring-digital.github.io/meinrved-pegel/tageswerte.json'


def reihe(r):
    """{Tag: Wert} aus {start, werte}."""
    if not r: return {}
    s = dt.date.fromisoformat(r['start'])
    return {s + dt.timedelta(i): v for i, v in enumerate(r['werte']) if v is not None}


def main():
    d = json.loads(fetch_url(SRC, timeout=30))
    lvl, q, ab = reihe(d.get('level')), reihe(d.get('inflow')), reihe(d.get('outflow'))
    rows = {r['date']: r for r in csv.DictReader(open(HIST))}
    last = dt.date.fromisoformat(max(k for k, r in rows.items() if r['level']))
    out_prev = next((float(rows[k]['outflow']) for k in sorted(rows, reverse=True) if rows[k]['outflow']), None)
    n = 0
    for day in sorted(x for x in lvl if x > last):
        o = ab.get(day, out_prev)
        out_prev = o if o is not None else out_prev
        rows[day.isoformat()] = dict(date=day.isoformat(), level=round(lvl[day], 2), volume=round(vol(lvl[day]), 2),
                                     inflow=q.get(day, ''), outflow='' if o is None else o)
        n += 1
    with open(HIST, 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['date', 'level', 'volume', 'inflow', 'outflow'])
        for k in sorted(rows): w.writerow([rows[k][c] for c in ('date', 'level', 'volume', 'inflow', 'outflow')])
    print(f'{n} Tage nach {last} aus der Datensammlung ergänzt, Verlauf bis {max(rows)}')


if __name__ == '__main__':
    main()
