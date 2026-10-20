"""Daten für die Konzeptseite zusammenstellen: Zufluss- und Abgabereihen für den Rechenkern im Browser,
Regeln, Bewertung und Prognose. Liest ausgabe/bewertung.json und ausgabe/prognose.json, schreibt seite/data.json."""
import os, sys, json, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, PAGE, CURVE, last_season
from sim import D, QIN, UP, BASE, SUMMER, free

P = json.load(open(os.path.join(OUT, 'prognose.json')))
B = json.load(open(os.path.join(OUT, 'bewertung.json')))
end = dt.date.fromisoformat(P['start'])
out = {}

# Zufluss und „freie“ Abgabe je Tag ab Oktober 1979 (reicht für den Spurenpool ab 1980)
d0 = dt.date(1979, 10, 1); q, o = [], []
d = d0
while d <= end:
    q.append(round(QIN[d], 2) if d in QIN else None)
    f = free(d); o.append(round(f, 1) if f is not None else -1)
    d += dt.timedelta(1)
out['series'] = dict(d0=d0.isoformat(), q=q, o=o)
out['up'] = [[m, dd, v] for (m, dd), v in UP]; out['base'] = BASE; out['summer'] = SUMMER; out['curve'] = CURVE

out['recent'] = [[x.isoformat(), round(D[x]['V'], 2)] for x in sorted(D) if end - dt.timedelta(366) < x <= end and D[x]['V'] is not None]
out['drawdown'] = [[y, round(D[dt.date(y, 6, 1)]['V'] - D[dt.date(y, 8, 1)]['V'], 1)] for y in range(1980, last_season(D) + 1)]
out['inflow_decade'] = [[dec, round(st.mean(QIN[x] for x in QIN if dec <= x.year < dec + 10), 1)] for dec in range(1950, end.year + 1, 10)]

out['skill'] = B['skill']
rows = B['rows']
out['calib'] = {k: [round(st.mean(r['p'] for r in rows if r['ev'] == k), 2), round(st.mean(r['ist'] for r in rows if r['ev'] == k), 2)] for k in ('voll', 'regatta', 'unter125')}
out['case2026'] = P['case2026']; out['V0'] = P['V0']; out['level0'] = P['level0']; out['start'] = P['start']

os.makedirs(PAGE, exist_ok=True)
json.dump(out, open(os.path.join(PAGE, 'data.json'), 'w'), separators=(',', ':'))
print('->', os.path.join(PAGE, 'data.json'), f'({len(q)} Tage)')
