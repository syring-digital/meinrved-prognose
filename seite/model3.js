// Seebilanz Stufe 3 im Browser (Port von stage3.simulate3). Zufluss und Weser-Restabfluss je Lauf kommen
// vorberechnet aus forecast3.py; hier wirken nur die Abgaberegeln, damit alle Schalter sofort rechnen.
const Model3 = (() => {
  const FULL = 199.55, K = 0.0864, DAY = 86400000;
  let UP, CURVE, BASE3, TARGET, CAP;
  const utc = (y, m, d) => Date.UTC(y, m - 1, d);
  const ymd = t => { const d = new Date(t); return [d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()]; };
  function init(data) { UP = data.up; CURVE = data.curve; BASE3 = data.base3; TARGET = data.target; CAP = data.cap; }
  // Winter-Leitlinie (Nov.–Apr.), sonst Vollstau
  function upper(t) {
    const [y, m] = ymd(t);
    const pts = UP.map(([pm, pd, v]) => {
      const py = (pm >= 11) === (m >= 11) ? y : (m < 11 ? y - 1 : y + 1);
      return [utc(py, pm, pm === 2 ? Math.min(pd, 28) : pd), v];
    });
    if (!(t >= utc(ymd(pts[0][0])[0], 11, 1) && t <= pts[pts.length - 1][0])) return FULL;
    for (let i = 1; i < pts.length; i++) {
      const [a, va] = pts[i - 1], [b, vb] = pts[i];
      if (t >= a && t <= b) return va + (vb - va) * Math.round((t - a) / DAY) / Math.max(1, Math.round((b - a) / DAY));
    }
    return FULL;
  }
  // opt: reduced (3 m³/s unter 29 Mio.), target (Stützungsziel Hann. Münden), plan {Tag: Abgabe},
  //      h125: {limit, spar, from, to} Haltelinie: unter limit zwischen Monat from und to höchstens spar m³/s
  function simulate(V0, start, qin, rest, opt = {}) {
    const reduced = opt.reduced !== false, tg = opt.target ?? TARGET, n = qin.length;
    const vol = new Float32Array(n), out = new Float32Array(n);
    let V = V0;
    for (let k = 0; k < n; k++) {
      const t = start + k * DAY, m = ymd(t)[1], q = qin[k];
      let o;
      if (opt.plan && opt.plan[k] != null) o = opt.plan[k];
      else {
        if (reduced && V < 29) o = 3;
        else if (V < 40) o = (m >= 11 || m <= 2) ? 4 : 6;
        else {
          o = BASE3[m];
          if (m >= 5 && m <= 10 && rest) o = Math.max(o, Math.min(tg - rest[k], 40));
        }
        const h = opt.h125;
        if (h && V < h.limit && m >= h.from && m <= h.to) o = Math.min(o, h.spar);
      }
      let Vn = V + (q - o) * K;
      const lim = upper(t + DAY);
      if (Vn > FULL) { o += (Vn - FULL) / K; Vn = FULL; }
      else if (Vn > lim) {
        const target = V > lim ? Math.max(lim, V - (V - lim) / 5) : lim;
        o = Math.max(o, Math.min(q + (V - target) / K, CAP)); Vn = V + (q - o) * K;
        if (Vn > FULL) { o += (Vn - FULL) / K; Vn = FULL; }
      }
      Vn = Math.max(Vn, 0.5);
      vol[k] = V; out[k] = o; V = Vn;
    }
    return { vol, out };
  }
  function pct(xs, p) {
    const s = Array.from(xs).sort((a, b) => a - b), k = (s.length - 1) * p, f = Math.floor(k), c = Math.min(f + 1, s.length - 1);
    return s[f] + (s[c] - s[f]) * (k - f);
  }
  function volume(h) {
    if (h <= CURVE[0][0]) return 0;
    for (let i = 1; i < CURVE.length; i++) if (h <= CURVE[i][0]) { const [a, va] = CURVE[i - 1], [b, vb] = CURVE[i]; return va + (vb - va) * (h - a) / (b - a); }
    return CURVE[CURVE.length - 1][1];
  }
  function level(v) {
    for (let i = 1; i < CURVE.length; i++) if (v <= CURVE[i][1]) { const [a, va] = CURVE[i - 1], [b, vb] = CURVE[i]; return a + (b - a) * (v - va) / (vb - va); }
    return CURVE[CURVE.length - 1][0];
  }
  return { init, simulate, upper, pct, volume, level, utc, ymd, DAY, FULL, K };
})();
