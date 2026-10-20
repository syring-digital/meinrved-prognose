"""Gemeinsame Grundlagen: Pfade, Höhen-Inhalt-Kurve und Laden der Tageswerte."""
import csv, os, sys, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
# Rohdaten: auf dem Mac außerhalb von iCloud (iCloud blockiert sonst gelegentlich das Schreiben), sonst im Ordner
DATA = os.environ.get('PROGNOSE_DATEN') or (os.path.expanduser('~/Library/Application Support/MeinRVED-Prognose/daten') if sys.platform == 'darwin' else os.path.join(HERE, 'daten'))
RAW = os.path.join(DATA, 'roh')
HIST = os.path.join(DATA, 'hist.csv')
OUT = os.path.join(HERE, 'ausgabe')
PAGE = os.path.join(HERE, 'seite')
MODEL = os.path.join(HERE, 'modell')  # kalibrierte Parameter (im Repository)

# Offizielle Höhen-Inhalt-Tabelle „Inhalt neu“ (Vermessung 2003), wie in Shared/WaterData.swift.
# (Pegel in m ü. NN, Inhalt in Mio. m³)
CURVE = [(206, 0.0), (207, 0.50), (208, 1.00), (209, 1.50), (210, 2.50), (211, 4.00), (212, 5.50), (213, 6.80), (214, 9.55), (215, 11.86), (216, 14.40), (217, 17.30), (218, 20.49), (219, 23.72), (220, 27.14), (221, 30.81), (222, 34.70), (223, 38.80), (224, 43.18), (225, 47.79), (226, 52.65), (227, 57.75), (228, 63.04), (229, 68.52), (230, 74.22), (231, 80.15), (232, 86.37), (233, 92.92), (234, 99.85), (235, 107.10), (236, 114.64), (237, 122.52), (238, 130.83), (239, 139.53), (240, 148.57), (241, 157.99), (242, 167.86), (243, 178.16), (244, 188.86), (244.97, 199.55), (245, 199.88), (246, 211.18), (247, 222.9)]
FULL = 199.55
K = 0.0864  # m³/s über einen Tag in Mio. m³


def vol(h):
    if h <= CURVE[0][0]: return 0.0
    for (a, va), (b, vb) in zip(CURVE, CURVE[1:]):
        if h <= b: return va + (vb - va) * (h - a) / (b - a)
    return CURVE[-1][1]


def level(v):
    for (a, va), (b, vb) in zip(CURVE, CURVE[1:]):
        if v <= vb: return a + (b - a) * (v - va) / (vb - va)
    return CURVE[-1][0]


def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def load(path=HIST):
    """Tageswerte laden. Inhalt V immer aus dem Pegel mit der neuen Kurve (edersee.me nutzt bis 2003 die alte).
    Ib = Bilanzzufluss (Abgabe + Inhaltsänderung bis zum nächsten Tag), enthält Regen auf den See und Verdunstung."""
    if not os.path.exists(path):
        raise SystemExit(f'{path} fehlt. Zuerst fetch.py und parse.py ausführen.')
    D = {}
    for x in csv.DictReader(open(path)):
        f = lambda k: float(x[k]) if x[k] != '' else None
        D[dt.date.fromisoformat(x['date'])] = dict(L=f('level'), Vr=f('volume'), I=f('inflow'), O=f('outflow'))
    for d, v in D.items(): v['V'] = vol(v['L']) if v['L'] else None
    for d, v in D.items():
        n = D.get(d + dt.timedelta(1))
        v['Ib'] = (v['O'] + (n['V'] - v['V']) / K) if (n and n['V'] is not None and v['V'] is not None and v['O'] is not None) else None
    return D


def last_season(D):
    """Letzte Saison (Jahr), für die Daten bis zum 1. August vorliegen."""
    last = max(d for d in D if D[d]['V'] is not None)
    return last.year if last >= dt.date(last.year, 8, 1) else last.year - 1


def fetch_url(url, data=None, timeout=60, tries=4):
    """HTTP-Abruf mit Wiederholungen (Server brechen gelegentlich ab)."""
    import time, urllib.request
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': 'MeinRVED-Prognose'})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception:
            if i == tries - 1: raise
            time.sleep(3 * (i + 1))
