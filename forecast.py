"""Saisonprognose ab dem letzten Tag in den Daten: Ensemble aus den Zuflussjahren ab 2000,
Kennzahlen je Spurjahr, Fächer (10/25/50/75/90 %) und das Fallbeispiel 2026. Ergebnis: ausgabe/prognose.json."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, pct
from sim import simulate, D

H = 365
start = max(d for d in D if D[d]['V'] is not None)
V0 = D[start]['V']
sy = start.year + 1 if start.month >= 8 else start.year  # Saison, auf die sich Vollstau und Sommer beziehen
runs = {t: simulate(V0, start, dt.date(t, start.month, start.day), H, adapt=20) for t in range(2000, start.year + 1)}
runs = {t: r for t, r in runs.items() if r and len(r) == H}
print('Start', start, 'Inhalt', round(V0, 2), 'Spuren', len(runs), f'({min(runs)}–{max(runs)})')


def first(r, cond, a=None, b=None):
    return next((x[0] for x in r if (a is None or x[0] >= a) and (b is None or x[0] <= b) and cond(x)), None)


iso = lambda d: d.isoformat() if d else None
summary = {}
for t, r in runs.items():
    tief = min(r[:200], key=lambda x: x[1])
    summary[t] = dict(
        tief=iso(tief[0]), tief_v=round(tief[1], 1),
        wende=next((r[k][0].isoformat() for k in range(len(r) - 7) if sum(x[2] - x[3] for x in r[k:k + 7]) > 0), None),
        ueber40=iso(first(r, lambda x: x[1] >= 40)), ueber125=iso(first(r, lambda x: x[1] >= 125)),
        voll=iso(first(r, lambda x: x[1] >= 197, dt.date(sy, 3, 1), dt.date(sy, 9, 30))),
        max=round(max(x[1] for x in r if dt.date(sy, 3, 1) <= x[0] <= dt.date(sy, 9, 30)), 1),
        unter125=iso(first(r, lambda x: x[1] < 125, dt.date(sy, 5, 1))),
        jul15=round(next(x[1] for x in r if x[0] == dt.date(sy, 7, 15)), 1),
        sep1=round(next(x[1] for x in r if x[0] == dt.date(sy, 9, 1)), 1))
for t in sorted(summary): print(f'Wetter wie {t}/{(t + 1) % 100:02d}', summary[t])

fan = [[round(pct([r[k][1] for r in runs.values()], p), 2) for p in (.1, .25, .5, .75, .9)] for k in range(H)]
n = len(runs)
print(f'Vollstau {sy}: {sum(s["voll"] is not None for s in summary.values()) / n:.0%}, '
      f'über 63 Mio. am 15.07.: {sum(s["jul15"] >= 63 for s in summary.values()) / n:.0%}')
for lab, d in (('1. Mai', dt.date(sy, 5, 1)), ('15. Juli', dt.date(sy, 7, 15)), ('1. Sept.', dt.date(sy, 9, 1))):
    print(f'Fächer {lab}:', fan[(d - start).days])

# Fallbeispiel 2026: Regatten am 11.07. (gesegelt) und 18.07. (abgesagt). Prognosen von verschiedenen Starttagen aus.
case = []
if dt.date(2026, 7, 18) in D:
    for s in (dt.date(2025, 10, 19), dt.date(2026, 3, 1), dt.date(2026, 5, 1), dt.date(2026, 6, 1)):
        days = (dt.date(2026, 7, 26) - s).days
        rs = [simulate(D[s]['V'], s, dt.date(t if s.month >= 10 else t + 1, s.month, s.day), days, adapt=20) for t in range(2000, 2025)]
        rs = [r for r in rs if r and len(r) == days]
        row = dict(start=s.isoformat(), V0=round(D[s]['V'], 1), n=len(rs))
        for k, d in (('jul11', dt.date(2026, 7, 11)), ('jul18', dt.date(2026, 7, 18))):
            xs = [next(x[1] for x in r if x[0] == d) for r in rs]
            row[k] = dict(p63=round(sum(x >= 63 for x in xs) / len(xs), 2), med=round(pct(xs, .5), 1), p10=round(pct(xs, .1), 1), p90=round(pct(xs, .9), 1), ist=round(D[d]['V'], 1))
        case.append(row); print('Fall 2026', row)

os.makedirs(OUT, exist_ok=True)
json.dump(dict(start=start.isoformat(), V0=round(V0, 2), level0=D[start]['L'], season=sy, summary=summary, fan=fan, case2026=case),
          open(os.path.join(OUT, 'prognose.json'), 'w'))
print('->', os.path.join(OUT, 'prognose.json'))
