"""Was-wäre-wenn: echte Jahre mit veränderten Regeln nachspielen (echter Zufluss, echte Abgaben als Ausgangspunkt).
Haltelinie 125 nach RVED-Konzept: fällt der See zwischen 1. Mai und 31. August unter die Grenze, wird höchstens die
Sparabgabe abgegeben. Ab September gilt wieder die echte Abgabe, das gesparte Wasser bleibt zunächst im See.
Ergebnis je Jahr: Inhalt am 15.07., 01.09. und 31.10. mit/ohne Regel, gespartes Wasser, Tage mit weniger Weser-Stützung.
  python3 whatif.py [--grenze 125] [--spar 6]"""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, FULL, K
import sim
from sim import D


def replay(year, limit=125.0, spar=6.0, months=(5, 6, 7, 8)):
    s = dt.date(year, 5, 1); e = min(dt.date(year, 10, 31), max(D) - dt.timedelta(1))
    V = D[s]['V']; d = s; rows = []; saved = 0.0; less_days = 0; max_cut = 0.0; o = q = None
    while d <= e:
        q = sim.inflow(d) if sim.inflow(d) is not None else q          # einzelne Lücken: Vortageswert
        o = D[d]['O'] if D[d]['O'] is not None else o
        if q is None or o is None: return None
        o2 = o
        if V < limit and d.month in months and o > spar:
            o2 = spar; less_days += 1; max_cut = max(max_cut, o - spar); saved += (o - spar) * K
        Vn = min(V + (q - o2) * K, FULL)
        rows.append((d, V, D[d]['V'])); V = max(Vn, 0.5); d += dt.timedelta(1)
    at = lambda m, dd: next((r for r in rows if r[0] == dt.date(year, m, dd)), rows[-1])
    return dict(jahr=year, v_mai=round(D[s]['V'], 1),
                jul15=[round(at(7, 15)[2], 1), round(at(7, 15)[1], 1)], sep1=[round(at(9, 1)[2], 1), round(at(9, 1)[1], 1)],
                okt31=[round(at(10, 31)[2], 1), round(at(10, 31)[1], 1)], gespart=round(saved, 1), tage=less_days, max_weniger=round(max_cut, 1))


if __name__ == '__main__':
    limit = float(sys.argv[sys.argv.index('--grenze') + 1]) if '--grenze' in sys.argv else 125.0
    spar = float(sys.argv[sys.argv.index('--spar') + 1]) if '--spar' in sys.argv else 6.0
    out = [r for r in (replay(y, limit, spar) for y in range(2003, 2027)) if r]
    print(f'Haltelinie {limit:.0f} Mio. m³, Sparabgabe {spar:.0f} m³/s (Mio. m³: echt / mit Regel)')
    print('Jahr  1.Mai |   15.07.     |   01.09.     |   31.10.     | gespart | Tage | Weser bis zu')
    for r in out:
        print(f"{r['jahr']} {r['v_mai']:6.1f} | {r['jul15'][0]:5.1f} {r['jul15'][1]:6.1f} | {r['sep1'][0]:5.1f} {r['sep1'][1]:6.1f} | {r['okt31'][0]:5.1f} {r['okt31'][1]:6.1f} | {r['gespart']:7.1f} | {r['tage']:4} | {r['max_weniger']:5.1f} m³/s")
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, 'whatif.json'), 'w'))
