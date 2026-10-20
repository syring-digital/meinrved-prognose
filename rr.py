"""Niederschlag-Abfluss-Modell GR4J (Perrin et al. 2003) mit Gradtag-Schneemodul und Verdunstung nach Oudin.
Reines Python ohne Zusatzpakete. Eingabe Tageswerte Niederschlag P (mm) und Temperatur T (°C), Ausgabe Abfluss (mm/Tag).

Parameter (Liste): x1 Produktionsspeicher (mm), x2 Austausch (mm/Tag), x3 Routingspeicher (mm), x4 Laufzeit (Tage),
                   cp Niederschlagsfaktor, ddf Schmelzfaktor (mm/°C/Tag), tsn Schneegrenze (°C)
"""
import math, datetime as dt

LAT = math.radians(51.1)


def pet_oudin(day, T):
    """Potenzielle Verdunstung (mm/Tag) nach Oudin et al. 2005 aus Temperatur und Breitengrad."""
    j = day.timetuple().tm_yday
    dr = 1 + 0.033 * math.cos(2 * math.pi * j / 365)
    de = 0.409 * math.sin(2 * math.pi * j / 365 - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(LAT) * math.tan(de))))
    re = 24 * 60 / math.pi * 0.0820 * dr * (ws * math.sin(LAT) * math.sin(de) + math.cos(LAT) * math.cos(de) * math.sin(ws))  # MJ/m²/Tag
    return max(0.0, re / (2.45 * 1000) * (T + 5) / 100 * 1000) if T + 5 > 0 else 0.0


def _uh(x4):
    def ss1(t): return 0.0 if t <= 0 else (1.0 if t >= x4 else (t / x4) ** 2.5)
    def ss2(t):
        if t <= 0: return 0.0
        if t < x4: return 0.5 * (t / x4) ** 2.5
        if t < 2 * x4: return 1 - 0.5 * (2 - t / x4) ** 2.5
        return 1.0
    n1, n2 = int(math.ceil(x4)), int(math.ceil(2 * x4))
    return [ss1(i) - ss1(i - 1) for i in range(1, n1 + 1)], [ss2(i) - ss2(i - 1) for i in range(1, n2 + 1)]


def init_state(par):
    x1, x2, x3, x4 = par[:4]
    uh1, uh2 = _uh(x4)
    return dict(S=0.5 * x1, R=0.5 * x3, snow=0.0, h1=[0.0] * len(uh1), h2=[0.0] * len(uh2))


def run(par, P, T, days, state=None):
    """Simuliert ab state (oder Standardzustand). P, T, days: gleich lange Listen. Gibt (Abfluss mm/Tag, Endzustand) zurück."""
    x1, x2, x3, x4, cp, ddf, tsn = par
    uh1, uh2 = _uh(x4)
    st = state or init_state(par)
    S, R, snow = st['S'], st['R'], st['snow']
    h1, h2 = list(st['h1']), list(st['h2'])
    if len(h1) != len(uh1): h1 = (h1 + [0.0] * len(uh1))[:len(uh1)]
    if len(h2) != len(uh2): h2 = (h2 + [0.0] * len(uh2))[:len(uh2)]
    out = []
    for p, t, d in zip(P, T, days):
        p = (p or 0.0) * cp
        t = 5.0 if t is None else t
        # Schnee
        if t < tsn: snow += p; p = 0.0
        if snow > 0 and t > 0:
            m = min(snow, ddf * t); snow -= m; p += m
        e = pet_oudin(d, t)
        # Produktionsspeicher
        if p >= e:
            pn, en = p - e, 0.0
            ps = x1 * (1 - (S / x1) ** 2) * math.tanh(pn / x1) / (1 + S / x1 * math.tanh(pn / x1))
            es = 0.0
        else:
            pn, en = 0.0, e - p
            es = S * (2 - S / x1) * math.tanh(en / x1) / (1 + (1 - S / x1) * math.tanh(en / x1))
            ps = 0.0
        S = S - es + ps
        perc = S * (1 - (1 + (4.0 / 9.0 * S / x1) ** 4) ** -0.25)
        S -= perc
        pr = perc + (pn - ps)
        # Einheitsganglinien
        for i in range(len(h1) - 1): h1[i] = h1[i + 1] + uh1[i] * pr * 0.9
        h1[-1] = uh1[-1] * pr * 0.9
        for i in range(len(h2) - 1): h2[i] = h2[i + 1] + uh2[i] * pr * 0.1
        h2[-1] = uh2[-1] * pr * 0.1
        q9, q1 = h1[0], h2[0]
        h1 = h1[1:] + [0.0]; h2 = h2[1:] + [0.0]
        F = x2 * (R / x3) ** 3.5
        R = max(0.0, R + q9 + F)
        qr = R * (1 - (1 + (R / x3) ** 4) ** -0.25)
        R -= qr
        qd = max(0.0, q1 + F)
        out.append(qr + qd)
    return out, dict(S=S, R=R, snow=snow, h1=h1, h2=h2)


def nelder_mead(f, x0, step, iters=400, tol=1e-6):
    """Einfaches Nelder-Mead-Verfahren (Minimierung)."""
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (step[j] if j == i else 0) for j in range(n)] for i in range(n)]
    vals = [f(p) for p in pts]
    for it in range(iters):
        order = sorted(range(n + 1), key=lambda i: vals[i]); pts = [pts[i] for i in order]; vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol: break
        c = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        xr = [c[j] + (c[j] - pts[-1][j]) for j in range(n)]; fr = f(xr)
        if fr < vals[0]:
            xe = [c[j] + 2 * (c[j] - pts[-1][j]) for j in range(n)]; fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = [c[j] + 0.5 * (pts[-1][j] - c[j]) for j in range(n)]; fc = f(xc)
            if fc < vals[-1]: pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0]] + [[pts[0][j] + 0.5 * (p[j] - pts[0][j]) for j in range(n)] for p in pts[1:]]
                vals = [vals[0]] + [f(p) for p in pts[1:]]
    i = min(range(n + 1), key=lambda i: vals[i])
    return pts[i], vals[i]


# Parameter werden in transformierter Form optimiert (positiv über log, Grenzen über Klemmen)
def to_par(z):
    return [math.exp(z[0]), z[1], math.exp(z[2]), 0.5 + math.exp(z[3]), math.exp(z[4]), math.exp(z[5]), z[6]]


def from_par(p):
    return [math.log(p[0]), p[1], math.log(p[2]), math.log(p[3] - 0.5), math.log(p[4]), math.log(p[5]), p[6]]


def nse(sim, obs):
    m = sum(obs) / len(obs)
    return 1 - sum((s - o) ** 2 for s, o in zip(sim, obs)) / sum((o - m) ** 2 for o in obs)


def kge(sim, obs):
    ms, mo = sum(sim) / len(sim), sum(obs) / len(obs)
    ss = math.sqrt(sum((s - ms) ** 2 for s in sim) / len(sim)); so = math.sqrt(sum((o - mo) ** 2 for o in obs) / len(obs))
    r = sum((s - ms) * (o - mo) for s, o in zip(sim, obs)) / len(sim) / (ss * so)
    return 1 - math.sqrt((r - 1) ** 2 + (ss / so - 1) ** 2 + (ms / mo - 1) ** 2)
