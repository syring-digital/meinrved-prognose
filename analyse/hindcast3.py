"""Rückblick: Stufe 2 gegen Stufe 3 (mit/ohne perfektes Wetter der ersten Woche), Start an jedem Monatsersten 2006–2025.
Fehler des Medians beim Seeinhalt und beim aufsummierten Zufluss nach 7, 14, 28, 60 und 120 Tagen."""
import os, sys, json, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stage3 as s3, sim
from common import pct, OUT
from stage3 import D
LEADS = [7, 14, 28, 60, 120]; H = 121
res = {v: {L: [] for L in LEADS} for v in 'ABC'}; qres = {v: {L: [] for L in (7, 14, 28)} for v in 'ABC'}
summer = {v: [] for v in 'ABC'}
starts = [dt.date(y, m, 1) for y in range(2006, 2026) for m in range(1, 13) if dt.date(y, m, 1) + dt.timedelta(H) < dt.date(2026, 10, 18)]
for n, s in enumerate(starts):
    pool = [t for t in range(2000, 2026) if t != s.year and dt.date(t, s.month, 1) + dt.timedelta(H) <= dt.date(2026, 10, 18)]
    V0 = D[s]['V']; out = {}
    out['A'] = [r for r in (sim.simulate(V0, s, dt.date(t, s.month, 1), H, adapt=20) for t in pool) if r]
    out['B'] = [r for _, r in s3.ensemble3(V0, s, H, pool)]
    perfect = {a: ([s3.clim(s + dt.timedelta(k), 'P_' + a) for k in range(7)], [s3.clim(s + dt.timedelta(k), 'T_' + a) for k in range(7)]) for a in ('eder', 'weser')}
    out['C'] = [r for _, r in s3.ensemble3(V0, s, H, pool, first_weather=perfect)]
    for v, runs in out.items():
        for L in LEADS:
            res[v][L].append(abs(pct([r[L][1] for r in runs], .5) - D[s + dt.timedelta(L)]['V']))
        for L in (7, 14, 28):
            qres[v][L].append(abs(pct([sum(x[2] for x in r[:L]) for r in runs], .5) - sum(sim.inflow(s + dt.timedelta(k)) for k in range(L))) * 0.0864)
        if s.month in (6, 7, 8):
            act = st.mean(D[s + dt.timedelta(k)]['O'] for k in range(30) if D[s + dt.timedelta(k)]['O'] is not None)
            summer[v].append(abs(pct([st.mean(x[3] for x in r[:30]) for r in runs], .5) - act))
    if n % 24 == 0: print(s, flush=True)
print('Mittlerer Fehler des Medians, Seeinhalt (Mio. m³), n =', len(starts))
for v, lab in (('A', 'Stufe 2'), ('B', 'Stufe 3 ohne Prognose'), ('C', 'Stufe 3 + perfekte Woche 1')):
    print(f'  {lab:28}', ' '.join(f'{L:>3} T: {st.mean(res[v][L]):5.2f}' for L in LEADS))
print('Aufsummierter Zufluss (Mio. m³)')
for v in 'ABC': print(f'  {v}', ' '.join(f'{L:>3} T: {st.mean(qres[v][L]):5.2f}' for L in (7, 14, 28)))
print('Mittlere Abgabe der ersten 30 Tage bei Start Juni–August (m³/s)')
for v in 'ABC': print(f'  {v}: {st.mean(summer[v]):5.2f}')
json.dump(dict(leads=LEADS, V={v: {L: round(st.mean(res[v][L]), 2) for L in LEADS} for v in res}, Q={v: {L: round(st.mean(qres[v][L]), 2) for L in (7, 14, 28)} for v in qres},
               summer={v: round(st.mean(summer[v]), 2) for v in summer}, n=len(starts)), open(os.path.join(OUT, 'hindcast3.json'), 'w'))
