import sys, statistics as st, datetime as dt, collections
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *
D = load()
e = [(D[d]['Ib'] - D[d]['I']) for d in D if d.year >= 2004 and D[d]['Ib'] is not None and D[d]['I'] is not None]
print('Bilanzzufluss - Spalte Zufluss (m3/s), ab 2004: mittel', round(st.mean(e), 2), 'median', round(st.median(e), 2))
# Rule exploration 2012-2026
cls = [(0,29),(29,40),(40,60),(60,100),(100,140),(140,180),(180,195),(195,999)]
tab = collections.defaultdict(list)
for d, v in D.items():
    if d.year < 2012 or v['O'] is None or v['V'] is None: continue
    c = next(i for i, (a, b) in enumerate(cls) if a <= v['V'] < b)
    tab[(d.month, c)].append(v['O'])
print('Median Abgabe m3/s 2012-2026 nach Monat (Zeilen) und Inhalt (Spalten)')
print('Mon ' + ' '.join(f'{a:>3}-{b if b<999 else "":<4}' for a, b in cls))
for m in range(1, 13):
    print(f'{m:>3} ' + ' '.join(f'{st.median(tab[(m,c)]):>5.1f}({len(tab[(m,c)]):>3})' if tab[(m,c)] else '   -      ' for c in range(len(cls))))
# max V by month 2012+
for m in range(1, 13):
    vs = [D[d]['V'] for d in D if d.year >= 2012 and d.month == m and D[d]['V']]
    print('Monat', m, 'max V', round(max(vs), 1), 'p95', round(sorted(vs)[int(len(vs)*.95)], 1))
