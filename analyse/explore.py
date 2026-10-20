import csv, sys, statistics as st, datetime as dt, collections
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import HIST
r = list(csv.DictReader(open(HIST)))
D = {}
for x in r:
    d = dt.date.fromisoformat(x['date'])
    f = lambda k: float(x[k]) if x[k] != '' else None
    D[d] = dict(L=f('level'), V=f('volume'), I=f('inflow'), O=f('outflow'))
# Check balance consistency: dV vs (I-O)
err = []
for d, v in D.items():
    n = D.get(d + dt.timedelta(1))
    if n and v['V'] and n['V'] and v['I'] is not None and v['O'] is not None and d.year >= 2000:
        err.append((n['V'] - v['V']) - (v['I'] - v['O']) * 0.0864)
print('Bilanzfehler Mio m3/Tag: median', round(st.median(err), 4), 'mittel', round(st.mean(err), 4), 'p5/p95', round(sorted(err)[len(err)//20], 3), round(sorted(err)[-len(err)//20], 3))
# Per year: max volume, date of first >=197, min volume Jul-Dec, date
print('Jahr  max  erstVoll>=197  minJulDez  datumMin  mittl.Abgabe Jun-Sep  mittl.Zufluss Jun-Sep')
for y in range(1936, 2027):
    days = sorted(d for d in D if d.year == y and D[d]['V'] is not None)
    if not days: continue
    mx = max(D[d]['V'] for d in days)
    full = next((d for d in days if D[d]['V'] >= 197), None)
    sec = [d for d in days if d.month >= 7]
    mn = min(sec, key=lambda d: D[d]['V']) if sec else None
    so = [D[d]['O'] for d in days if 6 <= d.month <= 9 and D[d]['O'] is not None]
    si = [D[d]['I'] for d in days if 6 <= d.month <= 9 and D[d]['I'] is not None]
    print(y, round(mx, 1), full.strftime('%d.%m') if full else '-----', round(D[mn]['V'], 1) if mn else '', mn.strftime('%d.%m') if mn else '', round(st.mean(so), 1) if so else '', round(st.mean(si), 1) if si else '')
