import sys, datetime as dt
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *
D = load()
for per in [(1990, 2011), (2012, 2025)]:
    print('Hüllkurve max V je Halbmonat', per)
    out = []
    for m in [11, 12, 1, 2, 3, 4]:
        for h in (0, 1):
            vs = [D[d]['V'] for d in D if per[0] <= d.year <= per[1] and d.month == m and (d.day > 15) == h and D[d]['V']]
            vs.sort(); out.append(f'{m:02d}{"b" if h else "a"}:{vs[-1]:.0f}/{vs[int(len(vs)*.98)]:.0f}')
    print('  '.join(out))
