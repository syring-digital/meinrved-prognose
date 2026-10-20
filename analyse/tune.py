import sys, datetime as dt, statistics as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sim
from sim import simulate, D
def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)
def vollstau(r, sy):
    a, b = dt.date(sy, 3, 1), dt.date(sy, 9, 30)
    return next((x[0] for x in r if a <= x[0] <= b and x[1] >= 197), None)
def at(r, d): return next((x[1] for x in r if x[0] == d), None)
def evaluate(pool, label, starts=((10, 19), (3, 1))):
    out = []
    for sm, sd in starts:
        crps = {5: [], 7: [], 9: []}; cov = {5: [], 7: [], 9: []}; br = []; bc = []
        for y in range(2005, 2025):
            s = dt.date(y if sm == 10 else y + 1, sm, sd); sy = y + 1
            runs = [simulate(D[s]['V'], s, dt.date(t, sm, sd), (dt.date(sy, 9, 30) - s).days + 1) for t in pool if t not in (y, y + 1)]
            runs = [r for r in runs if r]
            for m in (5, 7, 9):
                t = dt.date(sy, m, 1); xs = [at(r, t) for r in runs]; iv = D[t]['V']
                crps[m].append(abs(pct(xs, .5) - iv)); cov[m].append(pct(xs, .1) <= iv <= pct(xs, .9))
            full = [vollstau(r, sy) for r in runs]
            p = sum(1 for f in full if f and f <= dt.date(sy, 6, 1)) / len(full)
            fi = next((d for d in sorted(D) if dt.date(sy, 3, 1) <= d <= dt.date(sy, 6, 1) and D[d]['V'] >= 197), None)
            br.append((p - (1 if fi else 0)) ** 2)
        out.append(f"{sm:02d}/{sd:02d}: MAE Mai {st.mean(crps[5]):5.1f} Jul {st.mean(crps[7]):5.1f} Sep {st.mean(crps[9]):5.1f} | Band Mai {100*st.mean(cov[5]):3.0f}% Jul {100*st.mean(cov[7]):3.0f}% Sep {100*st.mean(cov[9]):3.0f}% | Brier {st.mean(br):.3f}")
    print(label); [print('   ', o) for o in out]
if __name__ == '__main__':
    for lo in (1936, 1970, 1980, 1990, 2000):
        evaluate(range(lo, 2025), f'Spuren {lo}-2024')
