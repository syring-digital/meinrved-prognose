"""Rechenkern: Seebilanz mit aus den Daten abgeleiteten Abgaberegeln.
Gleiche Logik wie seite/model.js (die Seite rechnet im Browser). Änderungen immer in beiden Dateien machen
und danach check_js.py laufen lassen.

Direkt ausgeführt: Nachrechentest 2005–2024 mit echten Zuflüssen (Start 19.10.).
  python3 sim.py            Weser-Bedarf aus den echten Abgaben des Jahres
  python3 sim.py --tabelle  Weser-Bedarf nur aus festen Monatswerten
"""
import os, sys, math, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load, FULL, K

D = load()

# Leitlinie der Winterbewirtschaftung (Mio. m³), aus dem Abgabeverhalten 2005–2026 abgeleitet.
# Darüber gibt das WSA kräftig ab, um Hochwasserschutzraum frei zu halten. Außerhalb Nov.–Apr. gilt Vollstau.
UP = [((11, 1), 110), ((12, 1), 110), ((12, 15), 120), ((1, 1), 140), ((1, 15), 150), ((2, 1), 160), ((2, 15), 168), ((3, 1), 175), ((3, 15), 185), ((4, 1), 192), ((4, 15), 197), ((4, 30), FULL)]
BASE = {11: 5, 12: 4, 1: 4, 2: 4, 3: 6, 4: 10, 5: 12}   # Abgabe unter der Leitlinie (m³/s), wenn das Spurjahr nichts liefert
SUMMER = {6: 20, 7: 23, 8: 22, 9: 18, 10: 15}            # Weser-Stützung, Ersatzwerte (Median 2012–2026)
WINTER_MIN = (11, 12, 1, 2)  # seit 2018 gibt das WSA bei niedrigem See im Winter nur 3–4 m³/s ab
CAP = 120.0                   # größte Abgabe beim Absenken nach Hochwasser (2003, 2011, 2023/24: 110–140 m³/s)
TABLE_ONLY = False            # Test: Stützbedarf nur aus Monatstabelle statt aus dem Spurjahr


def upper(d):
    pts = []
    for (m, dd), v in UP:
        y = d.year if (m >= 11) == (d.month >= 11) else (d.year - 1 if d.month < 11 else d.year + 1)
        pts.append((dt.date(y, m, min(dd, 28 if m == 2 else dd)), v))
    if not (dt.date(pts[0][0].year, 11, 1) <= d <= pts[-1][0]): return FULL
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if a <= d <= b: return va + (vb - va) * (d - a).days / max(1, (b - a).days)
    return FULL


# Zufluss je Tag: Bilanzzufluss, sonst Spalte Zufluss + 0,35 (mittlere Differenz); Lücken bis 40 Tage linear füllen.
QIN = {}
for d in sorted(D):
    v = D[d]
    q = v['Ib'] if v['Ib'] is not None else (v['I'] + 0.35 if v['I'] is not None else None)
    if q is not None: QIN[d] = q
_known = sorted(QIN)
for a, b in zip(_known, _known[1:]):
    gap = (b - a).days
    if 1 < gap <= 40:
        for k in range(1, gap): QIN[a + dt.timedelta(k)] = QIN[a] + (QIN[b] - QIN[a]) * k / gap


def inflow(d): return QIN.get(d)


def free(td):
    """Abgabe eines Tages, wenn der See damals im freien Betrieb war (über 42 Mio., unter der Leitlinie), sonst None."""
    v = D.get(td)
    if v and v['O'] is not None and v['V'] is not None and 42 < v['V'] < upper(td) - 3: return v['O']
    return None


def demand(td, m):
    # Abgabe des Spurjahres im freien Betrieb. Winterhalbjahr nur aus Jahren mit heutiger Bewirtschaftung (ab 2003).
    summer = m in SUMMER
    o = free(td)
    if o is not None and (summer or td.year >= 2003):
        return min(max(o, 6 if summer else 4), 40)
    return SUMMER[m] if summer else BASE[m]


def release(V, d, trace_d, reduced=True):
    if reduced and V < 29: return 3.0                 # reduzierte Mindestabgabe (2026 mit dem RP Kassel)
    if V < 40: return 4.0 if d.month in WINTER_MIN else 6.0
    if TABLE_ONLY: return SUMMER.get(d.month, BASE.get(d.month))
    return demand(trace_d, d.month)


def ratio(start, trace_start):
    # Verhältnis heutiger Zufluss / Zufluss im Spurjahr (je 14-Tage-Mittel vor dem Start)
    a = [x for x in (QIN.get(start - dt.timedelta(k)) for k in range(1, 15)) if x is not None]
    b = [x for x in (QIN.get(trace_start - dt.timedelta(k)) for k in range(1, 15)) if x is not None]
    if not a or not b: return 1.0
    return min(max(max(sum(a) / len(a), 0.3) / max(sum(b) / len(b), 0.3), 0.2), 5.0)


def dratio(start, trace_start):
    # Getestet und verworfen (dadapt): heutige Abgabe / Abgabe im Spurjahr, half 2026, schadete im Mittel.
    a = [D[start - dt.timedelta(k)]['O'] for k in range(1, 15) if D.get(start - dt.timedelta(k)) and D[start - dt.timedelta(k)]['O'] is not None]
    b = [demand(trace_start - dt.timedelta(k), (trace_start - dt.timedelta(k)).month) for k in range(1, 15)]
    if not a or not b or D[start]['V'] is None or D[start]['V'] < 42: return 1.0
    return min(max(sum(a) / len(a) / max(sum(b) / len(b), 3), 0.5), 2.5)


def simulate(V0, start, trace_start, days, reduced=True, rule125=False, adapt=0, r=None, dadapt=0):
    """Ein Lauf ab Inhalt V0 am Tag start, mit Zufluss und Weser-Bedarf des Spurjahres ab trace_start.
    adapt: Tage, über die der Zufluss vom heutigen Niveau ins Spurjahr übergeht (Standard 20).
    Rückgabe: Liste (Datum, Inhalt zu Tagesbeginn, Zufluss, Abgabe) oder None bei Datenlücke."""
    if adapt and r is None: r = ratio(start, trace_start)
    rd = dratio(start, trace_start) if dadapt else 1.0
    V = V0; out = []
    for k in range(days):
        d = start + dt.timedelta(k); td = trace_start + dt.timedelta(k)
        if td.month == 2 and td.day == 29: td = td + dt.timedelta(1)
        q = inflow(td)
        if q is None: return None
        if adapt: q = q * (r + (1 - r) * (1 - math.exp(-k / adapt)))
        o = release(V, d, td, reduced)
        if dadapt and V >= 40: o = o * (rd + (1 - rd) * (1 - math.exp(-k / dadapt)))
        if rule125 and V < 125 and 5 <= d.month <= 8: o = min(o, 6.0)  # Haltelinie 125 (Stufe 4, noch ungenutzt)
        Vn = V + (q - o) * K
        lim = upper(d + dt.timedelta(1))
        if Vn > FULL:
            o += (Vn - FULL) / K; Vn = FULL  # Hochwasserentlastung
        elif Vn > lim:
            # über der Leitlinie: bis zur Linie abgeben; liegt der See schon darüber, den Überschuss in ~5 Tagen abbauen
            target = max(lim, V - (V - lim) / 5.0) if V > lim else lim
            o = max(o, min(q + (V - target) / K, CAP)); Vn = V + (q - o) * K
            if Vn > FULL: o += (Vn - FULL) / K; Vn = FULL
        Vn = max(Vn, 0.5)
        out.append((d, V, q, o)); V = Vn
    return out


if __name__ == '__main__':
    TABLE_ONLY = '--tabelle' in sys.argv
    print('Weser-Bedarf:', 'feste Monatswerte' if TABLE_ONLY else 'echte Abgaben des Jahres')
    print('Jahr  V0   | 1.Mai sim/ist | 1.Jul sim/ist | 1.Sep sim/ist')
    errs = {5: [], 7: [], 9: []}
    for y in range(2005, 2025):
        s = dt.date(y, 10, 19)
        r = simulate(D[s]['V'], s, s, 330)
        if not r: continue
        row = [f'{y} {D[s]["V"]:5.1f} ']
        for m in (5, 7, 9):
            t = dt.date(y + 1, m, 1); sv = next(x[1] for x in r if x[0] == t); iv = D[t]['V']
            errs[m].append(sv - iv); row.append(f'| {sv:5.1f}/{iv:5.1f} ')
        print(''.join(row))
    for m in errs: print('1.', m, ': Fehler mittel', round(st.mean(errs[m]), 1), 'MAE', round(st.mean(abs(e) for e in errs[m]), 1))
