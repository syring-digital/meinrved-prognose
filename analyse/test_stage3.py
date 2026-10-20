"""Nachrechentest Stufe 3 mit beobachtetem Wetter (obere Grenze der Wettervorhersage-Güte):
Start jeweils 19.10., Zufluss und Stützbedarf aus den Abflussmodellen, ohne echte Abgaben."""
import os, sys, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stage3 as s3
from stage3 import D
starts = [dt.date(y, 10, 19) for y in range(2005, 2025)]
_, sims = s3.states_at(starts + [dt.date(2026, 10, 18)])
errs = {5: [], 7: [], 9: []}; rel = []
print('Jahr  V0   | 1.Mai sim/ist | 1.Jul sim/ist | 1.Sep sim/ist | Abgabe Jun-Aug sim/ist')
for s in starts:
    days = [s + dt.timedelta(k) for k in range(330)]
    qin = [sims['eder'][d] for d in days]; rest = [sims['weser'][d] for d in days]
    r = s3.simulate3(D[s]['V'], s, qin, rest)
    row = f'{s.year} {D[s]["V"]:5.1f} '
    for m in errs:
        t = dt.date(s.year + 1, m, 1); sv = next(x[1] for x in r if x[0] == t); iv = D[t]['V']
        errs[m].append(sv - iv); row += f'| {sv:5.1f}/{iv:5.1f} '
    so = st.mean(x[3] for x in r if 6 <= x[0].month <= 8); io = st.mean(D[x[0]]['O'] for x in r if 6 <= x[0].month <= 8 and D[x[0]]['O'] is not None)
    rel.append(so - io); print(row + f'| {so:5.1f}/{io:5.1f}')
for m in errs: print('1.', m, ': Fehler mittel', round(st.mean(errs[m]), 1), 'MAE', round(st.mean(abs(e) for e in errs[m]), 1))
print('Abgabe Jun–Aug: Fehler mittel', round(st.mean(rel), 1), 'MAE', round(st.mean(abs(e) for e in rel), 1))
# Sommer 2026: Restabfluss und Stützbedarf
print('2026: Tag, Rest sim, Stützbedarf sim, Abgabe ist, V ist')
for d in [dt.date(2026, m, dd) for m in (5, 6, 7, 8) for dd in (1, 15)]:
    print(' ', d, round(sims['weser'][d], 1), round(max(0, 55 - sims['weser'][d]), 1), D[d]['O'], round(D[d]['V'], 1))
