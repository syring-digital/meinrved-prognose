"""Rückblick: Nutzen des WSA-Abgabeplans (echte Abgaben der ersten 5 Tage) zusätzlich zu Stufe 3, Start alle 2 Monate."""
import os, sys, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stage3 as s3
from common import pct
from stage3 import D
H = 29; LEADS = [5, 7, 14, 28]
res = {v: {L: [] for L in LEADS} for v in ('B', 'B+Plan', 'C+Plan')}
starts = [dt.date(y, m, 1) for y in range(2006, 2026) for m in range(1, 13, 2)]
for s in starts:
    pool = [t for t in range(2000, 2026) if t != s.year]
    plan = {k: D[s + dt.timedelta(k)]['O'] for k in range(5) if D[s + dt.timedelta(k)]['O'] is not None}
    perfect = {a: ([s3.clim(s + dt.timedelta(k), 'P_' + a) for k in range(7)], [s3.clim(s + dt.timedelta(k), 'T_' + a) for k in range(7)]) for a in ('eder', 'weser')}
    out = {'B': s3.ensemble3(D[s]['V'], s, H, pool), 'B+Plan': s3.ensemble3(D[s]['V'], s, H, pool, plan=plan),
           'C+Plan': s3.ensemble3(D[s]['V'], s, H, pool, first_weather=perfect, plan=plan)}
    for v, runs in out.items():
        for L in LEADS: res[v][L].append(abs(pct([r[L][1] for _, r in runs], .5) - D[s + dt.timedelta(L)]['V']))
for v in res: print(f'{v:8}', ' '.join(f'{L:>3} T: {st.mean(res[v][L]):5.2f}' for L in LEADS))
