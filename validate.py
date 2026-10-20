"""Rückblick-Test der Wahrscheinlichkeiten: für jede Saison ab 2006 und sechs Starttermine ein Ensemble
ohne das Testjahr rechnen und mit dem Eingetretenen vergleichen. Ergebnis: ausgabe/bewertung.json.
  python3 validate.py            Spurenpool ab 2000 (Standard)
  python3 validate.py --pool 1980
Dauer: einige Minuten."""
import os, sys, json, random, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, last_season
from sim import simulate, D

LS = last_season(D)
first_pool = int(sys.argv[sys.argv.index('--pool') + 1]) if '--pool' in sys.argv else 2000
POOL = range(first_pool, LS)  # Spurjahr t: Okt. t bis Aug. t+1
REGATTA = 63  # Mio. m³ ≈ 228 m ü. NN (2026: am 11.07. bei 73,7 gesegelt, am 18.07. bei 52,2 abgesagt)


def at(r, d): return next((x[1] for x in r if x[0] == d), None)


def events(r, sy):
    full = any(x[1] >= 197 for x in r if dt.date(sy, 3, 1) <= x[0] <= dt.date(sy, 6, 1))
    return dict(voll=full, regatta=at(r, dt.date(sy, 7, 15)) >= REGATTA, unter125=at(r, dt.date(sy, 8, 1)) < 125)


def actual(sy):
    seg = {d: D[d]['V'] for d in D if dt.date(sy, 3, 1) <= d <= dt.date(sy, 6, 1)}
    return dict(voll=any(v >= 197 for v in seg.values()), regatta=D[dt.date(sy, 7, 15)]['V'] >= REGATTA, unter125=D[dt.date(sy, 8, 1)]['V'] < 125)


starts = [(10, 19), (12, 1), (2, 1), (3, 1), (4, 1), (5, 1)]
rows = []
for sy in range(2006, LS + 1):
    y = sy - 1
    for sm, sd in starts:
        s = dt.date(y if sm >= 10 else sy, sm, sd)
        days = (dt.date(sy, 8, 2) - s).days
        runs = [simulate(D[s]['V'], s, dt.date(t if sm >= 10 else t + 1, sm, sd), days, adapt=20) for t in POOL if t not in (y, sy)]
        runs = [r for r in runs if r and len(r) == days]
        ev = [events(r, sy) for r in runs]; a = actual(sy)
        for k in a:
            rows.append(dict(y=sy, start=f'{sd:02d}.{sm:02d}.', ev=k, p=round(sum(e[k] for e in ev) / len(ev), 3), ist=int(a[k]), n=len(ev)))
    print(sy, 'fertig', flush=True)

# Vergleichsmaßstab: Häufigkeit des Ereignisses in allen anderen Saisons des Pools (leave-one-out),
# dazu ein 80-%-Bereich per Bootstrap über die Saisons.
seasons = list(range(POOL.start + 1, LS + 1))
acts = {z: actual(z) for z in seasons}
skill = {}
for k in ('voll', 'regatta', 'unter125'):
    print('Ereignis', k)
    for sm, sd in starts:
        lab = f'{sd:02d}.{sm:02d}.'
        rr = [r for r in rows if r['ev'] == k and r['start'] == lab]
        cl = {r['y']: st.mean(acts[z][k] for z in seasons if z != r['y']) for r in rr}

        def ss(sample):
            bs = st.mean((r['p'] - r['ist']) ** 2 for r in sample); bc = st.mean((cl[r['y']] - r['ist']) ** 2 for r in sample)
            return 1 - bs / bc if bc > 0 else 0.0
        random.seed(1)
        boot = sorted(ss([random.choice(rr) for _ in rr]) for _ in range(1000))
        val, lo, hi = ss(rr), boot[100], boot[900]
        skill.setdefault(k, []).append([lab, round(val, 2), round(lo, 2), round(hi, 2)])
        print(f'  Start {lab}: Skill {val:+.2f}  (80 %-Bereich {lo:+.2f} bis {hi:+.2f}), Häufigkeit {st.mean(r["ist"] for r in rr):.2f}')
for k in ('voll', 'regatta', 'unter125'):
    rr = [r for r in rows if r['ev'] == k]
    print(f'Kalibrierung {k}: vorhergesagt {st.mean(r["p"] for r in rr):.2f}, eingetreten {st.mean(r["ist"] for r in rr):.2f}')

os.makedirs(OUT, exist_ok=True)
json.dump(dict(pool=[POOL.start, POOL.stop - 1], rows=rows, skill=skill), open(os.path.join(OUT, 'bewertung.json'), 'w'))
print('->', os.path.join(OUT, 'bewertung.json'))
