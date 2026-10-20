import sys, datetime as dt, statistics as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import simulate, D
def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)
for da in (0, 20, 45, 90):
    res = {}
    for sm, sd in ((5, 1), (6, 1), (7, 1)):
        for lead in (30, 60):
            errs = []; cov = []
            for y in range(2005, 2027):
                s = dt.date(y, sm, sd)
                if s + dt.timedelta(lead) > dt.date(2026, 10, 19): continue
                rs = [simulate(D[s]['V'], s, dt.date(t, sm, sd), lead + 1, adapt=20, dadapt=da) for t in range(2000, 2026) if t != y]
                rs = [r for r in rs if r and len(r) == lead + 1]
                xs = [r[lead][1] for r in rs]; iv = D[s + dt.timedelta(lead)]['V']
                errs.append(abs(pct(xs, .5) - iv)); cov.append(pct(xs, .1) <= iv <= pct(xs, .9))
            res[f'{sd:02d}.{sm:02d}+{lead}'] = (st.mean(errs), st.mean(cov))
    s = dt.date(2026, 6, 1)
    rs = [simulate(D[s]['V'], s, dt.date(t, 6, 1), 48, adapt=20, dadapt=da) for t in range(2000, 2026)]
    xs = [r[47][1] for r in rs if r and len(r) == 48]
    print('dadapt', da, ' '.join(f'{k}:{v[0]:5.1f}/{v[1]*100:3.0f}%' for k, v in res.items()), f'| 18.07.26 ab 1.6.: med {pct(xs,.5):.0f} p10 {pct(xs,.1):.0f} (ist 52)', flush=True)
