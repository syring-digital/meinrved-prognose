import sys, datetime as dt, statistics as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import simulate, D
def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)
for tau in (0, 15, 30, 60, 120):
    res = {}
    for sm, sd in ((10, 19), (12, 1), (3, 1), (6, 1)):
        for lead in (30, 60, 120):
            errs = []
            for y in range(2005, 2026):
                s = dt.date(y, sm, sd)
                if s + dt.timedelta(lead) > dt.date(2026, 10, 19): continue
                rs = [simulate(D[s]['V'], s, dt.date(t, sm, sd), lead + 1, adapt=tau) for t in range(2000, 2026) if t not in (y - 1, y, y + 1)]
                rs = [r for r in rs if r and len(r) == lead + 1]
                errs.append(abs(pct([r[lead][1] for r in rs], .5) - D[s + dt.timedelta(lead)]['V']))
            res[f'{sd:02d}.{sm:02d}+{lead}'] = st.mean(errs)
    print('tau', tau, ' '.join(f'{k}:{v:5.1f}' for k, v in res.items()), '| Summe', round(sum(res.values()), 1), flush=True)
