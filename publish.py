"""Datei für die App: ausgabe/app/prognose.json (Schema-Version 1, Stufe 1 und die nächsten 4 Wochen).
Liest ausgabe/prognose3.json (forecast3.py) und rechnet die Seebilanz mit den Standardregeln und dem WSA-Plan.
Alle Mengen in Mio. m³, Abflüsse in m³/s, Pegel in m ü. NN, Regen in mm (Gebietsmittel Eder)."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, pct, level, vol
import stage3 as s3

P = json.load(open(os.path.join(OUT, 'prognose3.json')))
start = dt.date.fromisoformat(P['start'])
plan = {(dt.date.fromisoformat(d) - start).days: v for d, v in P['plan'].get('plan', []) if dt.date.fromisoformat(d) >= start}
runs = P['runs']
sims = [s3.simulate3(P['V0'], start, r['qin'], r['rest'], plan=plan) for r in runs]
N = 29
q5 = lambda xs: [round(pct(xs, p), 2) for p in (.1, .25, .5, .75, .9)]
rain = P['eps']['rain']['eder']

tage = []
for k in range(7):
    d = start + dt.timedelta(k)
    v = pct([s[k][1] for s in sims], .5)
    tage.append(dict(datum=d.isoformat(), regen=rain[k] if k < len(rain) else None,
                     zufluss=round(pct([r['qin'][k] for r in runs], .5), 2), abgabe=round(pct([s[k][3] for s in sims], .5), 1),
                     ausPlan=k in plan, inhalt=round(v, 2), pegel=round(level(v), 2)))

wochen = []
for w in range(4):
    qs = [sum(r['qin'][w * 7:w * 7 + 7]) / 7 for r in runs]
    wochen.append(dict(ab=(start + dt.timedelta(w * 7)).isoformat(), zufluss=[round(pct(qs, p), 2) for p in (.1, .5, .9)],
                       inhaltEnde=round(pct([s[w * 7 + 7][1] for s in sims], .5), 1)))


def wende(s, r):
    for k in range(len(s) - 7):
        if sum(r['qin'][j] - s[j][3] for j in range(k, k + 7)) > 0: return k
    return None


wk = [wende(s, r) for s, r in zip(sims, runs)]
u40 = [next((k for k in range(len(s)) if s[k][1] >= 40), None) for s in sims] if P['V0'] < 40 else []
got = sorted(k for k in u40 if k is not None)
ueber40 = None
if got:
    q = lambda p: (start + dt.timedelta(got[round((len(got) - 1) * p)])).isoformat()
    ueber40 = dict(median=q(.5), frueh=q(.1), spaet=q(.9), anteil=round(len(got) / len(sims), 2))


# Saison (0.17.0): Fächer bis zum Ende des Ensembles, Kennzahlen und je Tag die Chance auf segelbaren Wasserstand
GRENZE_PEGEL = 228.0                     # aus 2026 abgeleitet: bei 229,9 m gesegelt, bei 225,9 m abgesagt
GRENZE = vol(GRENZE_PEGEL)
simsH = [s3.simulate3(P['V0'], start, r['qin'], r['rest'], plan=plan, rule125=True) for r in runs]
H = len(sims[0])
sy = start.year + 1 if start.month >= 8 else start.year
kday = lambda d: (d - start).days
n = len(sims)


def first_day(s, cond, a=0, b=None):
    for k in range(a, (H if b is None else min(b + 1, H))):
        if cond(s[k][1]): return k
    return None


def date_stats(ks):
    got = sorted(k for k in ks if k is not None)
    if not got: return None
    q = lambda p: (start + dt.timedelta(got[round((len(got) - 1) * p)])).isoformat()
    return dict(median=q(.5), frueh=q(.1), spaet=q(.9), anteil=round(len(got) / n, 2))


km, ka = kday(dt.date(sy, 5, 1)), kday(dt.date(sy, 8, 1))
# Was die Haltelinie 125 kosten und bringen würde (je Szenario: Tage mit weniger Abgabe, größte Kürzung)
cut_days = [sum(1 for k in range(H) if s[k][3] - sh[k][3] > 0.5) for s, sh in zip(sims, simsH)]
cut_max = [max(s[k][3] - sh[k][3] for k in range(H)) for s, sh in zip(sims, simsH)]
ks1 = kday(dt.date(sy, 9, 1))
haltelinie = dict(
    anteilBetroffen=round(sum(d > 0 for d in cut_days) / n, 2),
    tageWeniger=round(pct([d for d in cut_days if d > 0] or [0], .5)),
    maxWeniger=round(pct([m for m, d in zip(cut_max, cut_days) if d > 0] or [0], .5), 1),
    september1=[round(pct([s[ks1][1] for s in sims], .5), 1), round(pct([s[ks1][1] for s in simsH], .5), 1)] if ks1 < H else None)
voll = date_stats([first_day(s, lambda v: v >= 197, kday(dt.date(sy, 3, 1)), kday(dt.date(sy, 9, 30))) for s in sims])
saison = dict(
    start=start.isoformat(), jahr=sy,
    inhalt=[[round(pct([s[k][1] for s in sims], p), 1) for p in (.1, .25, .5, .75, .9)] for k in range(H)],
    segelbar=[round(sum(s[k][1] >= GRENZE for s in sims) / n, 2) for k in range(H)],
    segelbarHaltelinie=[round(sum(s[k][1] >= GRENZE for s in simsH) / n, 2) for k in range(H)],
    inhaltHaltelinie=[[round(pct([s[k][1] for s in simsH], p), 1) for p in (.1, .25, .5, .75, .9)] for k in range(H)],
    haltelinie=haltelinie,
    grenze=dict(pegel=GRENZE_PEGEL, inhalt=round(GRENZE, 1)),
    gemessen=[[d.isoformat(), round(s3.D[d]['V'], 1)] for d in sorted(s3.D) if start - dt.timedelta(366) < d <= start and s3.D[d]['V'] is not None],
    kennzahlen=dict(
        tiefster=round(min(min(s[k][1] for k in range(min(120, H))) for s in sims), 1),
        ueber125=date_stats([first_day(s, lambda v: v >= 125) for s in sims]) if P['V0'] < 125 else None,
        vollstau=voll if voll else dict(median=None, frueh=None, spaet=None, anteil=0.0),
        unter125Ab=date_stats([first_day(s, lambda v: v < 125, km) for s in sims]),
        unter125VorAugust=round(sum(first_day(s, lambda v: v < 125, km, ka - 1) is not None for s in sims) / n, 2),
        juli15Median=round(pct([s[kday(dt.date(sy, 7, 15))][1] for s in sims], .5), 1) if kday(dt.date(sy, 7, 15)) < H else None),
    guete=dict(regattaAbFebruar=0.33, vollstauAbApril=0.40, kalibrierungRegatta=[0.93, 0.90],
               text='Brier-Skill gegenüber reiner Statistik im Rückblick 2006–2026; Regatta-Wahrscheinlichkeiten waren im Mittel etwas zu hoch.'))

live = P['live']
out = dict(
    version=1, erstellt=dt.datetime.now().astimezone().isoformat(timespec='seconds'),
    tageswert=dict(datum=start.isoformat(), inhalt=P['V0'], pegel=P['level0']),
    live=dict(see=dict(zeit=live['see'][0], pegel=live['see'][1]),
              schmittlotheim=dict(zeit=live['schmitt'][0], abfluss=live['schmitt'][1]),
              hannMuenden=dict(datum=live['hmue'][0], abfluss=round(live['hmue'][1], 1))),
    wsa=dict(stand=P['plan'].get('stand'), plan=P['plan'].get('plan', []), text=P['plan'].get('text'), mittel=P['plan'].get('mittel')),
    dwd=dict(abgerufen=P['eps']['abgerufen'], laeufe=40, modell='ICON-EPS'),
    tage=tage,
    vierWochen=dict(start=start.isoformat(), inhalt=[q5([s[k][1] for s in sims]) for k in range(N)],
                    regen=rain[:N], wochen=wochen),
    wendepunkt=dict(in7Tagen=round(sum(1 for k in wk if k is not None and k <= 7) / len(wk), 2),
                    in28Tagen=round(sum(1 for k in wk if k is not None and k <= 28) / len(wk), 2)),
    ueber40=ueber40,
    guete=dict(fehler7=4.8, fehler14=8.1, fehler28=12.2, vergleichStufe2=[5.4, 8.7, 12.9], startTermine=240,
               text='Mittlerer Fehler des Medians beim Seeinhalt im Rückblick 2006–2025 (Mio. m³).'),
    laeufe=len(sims),
    saison=saison,
    quellen=['Deutscher Wetterdienst (ICON-EPS, Stationsdaten), CC BY 4.0', 'WSV Pegelonline', 'WSA Weser: Wasserstandsvorhersage Oberweser',
             'wasserstand.edersee.me', 'BfG Gewässerkundliches Jahrbuch'])
os.makedirs(os.path.join(OUT, 'app'), exist_ok=True)
p = os.path.join(OUT, 'app', 'prognose.json')
json.dump(out, open(p, 'w'), ensure_ascii=False, separators=(',', ':'))
print('->', p, os.path.getsize(p), 'Bytes |', 'über 40:', ueber40, '| Wendepunkt', out['wendepunkt'])
print('Saison', sy, '| Vollstau', saison['kennzahlen']['vollstau'], '| 15.07. segelbar', saison['segelbar'][kday(dt.date(sy, 7, 15))], 'mit Haltelinie', saison['segelbarHaltelinie'][kday(dt.date(sy, 7, 15))])
