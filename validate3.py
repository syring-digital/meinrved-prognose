"""Rückblick-Test der Wahrscheinlichkeiten für Stufe 3 (wie validate.py, aber Ensemble mit Abflussmodellen und
Stützbedarf aus dem Weser-Restgebiet). Ohne Wetterprognose, weil für die Vergangenheit keine DWD-Ensembleprognosen
vorliegen. Hinweis: Das Eder-Modell ist an 1991–2010 kalibriert, das Weser-Modell an 2003–2026 und 2013–2015;
die Bewertung ist für diese Jahre etwas zu günstig. -> ausgabe/bewertung3.json"""
import os, sys, json, random, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, last_season
import stage3 as s3
from stage3 import D

LS = last_season(D)
POOL = range(2000, LS)
REGATTA = 63


def at(r, d): return next((x[1] for x in r if x[0] == d), None)


def events(r, sy):
    return dict(voll=any(x[1] >= 197 for x in r if dt.date(sy, 3, 1) <= x[0] <= dt.date(sy, 6, 1)),
                regatta=at(r, dt.date(sy, 7, 15)) >= REGATTA, unter125=at(r, dt.date(sy, 8, 1)) < 125)


def actual(sy):
    return dict(voll=any(D[d]['V'] >= 197 for d in D if dt.date(sy, 3, 1) <= d <= dt.date(sy, 6, 1)),
                regatta=D[dt.date(sy, 7, 15)]['V'] >= REGATTA, unter125=D[dt.date(sy, 8, 1)]['V'] < 125)


starts = [(10, 19), (12, 1), (2, 1), (3, 1), (4, 1), (5, 1)]
rows = []
for sy in range(2006, LS + 1):
    y = sy - 1
    for sm, sd in starts:
        s = dt.date(y if sm >= 10 else sy, sm, sd)
        H = (dt.date(sy, 8, 2) - s).days
        pool = [t if sm >= 10 else t + 1 for t in POOL if t not in (y, sy)]
        runs = [r for _, r in s3.ensemble3(D[s]['V'], s, H, pool)]
        ev = [events(r, sy) for r in runs]; a = actual(sy)
        for k in a:
            rows.append(dict(y=sy, start=f'{sd:02d}.{sm:02d}.', ev=k, p=round(sum(e[k] for e in ev) / len(ev), 3), ist=int(a[k]), n=len(ev)))
    print(sy, 'fertig', flush=True)

seasons = list(range(POOL.start + 1, LS + 1))
acts = {z: actual(z) for z in seasons}
skill = {}
for k in ('voll', 'regatta', 'unter125'):
    print('Ereignis', k)
    for sm, sd in starts:
        lab = f'{sd:02d}.{sm:02d}.'
        rr_ = [r for r in rows if r['ev'] == k and r['start'] == lab]
        cl = {r['y']: st.mean(acts[z][k] for z in seasons if z != r['y']) for r in rr_}

        def ss(sample):
            bs = st.mean((r['p'] - r['ist']) ** 2 for r in sample); bc = st.mean((cl[r['y']] - r['ist']) ** 2 for r in sample)
            return 1 - bs / bc if bc > 0 else 0.0
        random.seed(1)
        boot = sorted(ss([random.choice(rr_) for _ in rr_]) for _ in range(1000))
        val, lo, hi = ss(rr_), boot[100], boot[900]
        skill.setdefault(k, []).append([lab, round(val, 2), round(lo, 2), round(hi, 2)])
        print(f'  Start {lab}: Skill {val:+.2f}  (80 %-Bereich {lo:+.2f} bis {hi:+.2f})')
for k in ('voll', 'regatta', 'unter125'):
    rr_ = [r for r in rows if r['ev'] == k]
    print(f'Kalibrierung {k}: vorhergesagt {st.mean(r["p"] for r in rr_):.2f}, eingetreten {st.mean(r["ist"] for r in rr_):.2f}')
json.dump(dict(rows=rows, skill=skill), open(os.path.join(OUT, 'bewertung3.json'), 'w'))
