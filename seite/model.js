// Rechenkern Edersee-Saisonprognose (Port von sim.py). Alle Mengen in Mio. m³, Abflüsse in m³/s.
const Model = (() => {
  const FULL = 199.55, DAY = 86400000, K = 0.0864;
  let S, d0, Q, O, UP, BASE, SUMMER, CURVE;
  function init(data) {
    S = data; d0 = Date.UTC(...data.series.d0.split('-').map((v, i) => i === 1 ? v - 1 : +v));
    Q = data.series.q; O = data.series.o; UP = data.up; BASE = data.base; SUMMER = data.summer; CURVE = data.curve;
  }
  const idx = t => Math.round((t - d0) / DAY);
  const ymd = t => { const d = new Date(t); return [d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()]; };
  const utc = (y, m, d) => Date.UTC(y, m - 1, d);
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
  function demand(td, m) {
    const o = O[idx(td)], summer = m in SUMMER;
    if (o !== undefined && o >= 0 && (summer || ymd(td)[0] >= 2003)) return Math.min(Math.max(o, summer ? 6 : 4), 40);
    return summer ? SUMMER[m] : BASE[m];
  }
  function ratio(start, ts) {
    const a = [], b = [];
    for (let k = 1; k < 15; k++) {
      const x = Q[idx(start - k * DAY)], y = Q[idx(ts - k * DAY)];
      if (x != null) a.push(x); if (y != null) b.push(y);
    }
    if (!a.length || !b.length) return 1;
    const ma = a.reduce((s, v) => s + v, 0) / a.length, mb = b.reduce((s, v) => s + v, 0) / b.length;
    return Math.min(Math.max(Math.max(ma, 0.3) / Math.max(mb, 0.3), 0.2), 5);
  }
  // Ein Lauf: Startinhalt V0 am Tag start, Wetter (Zufluss) und Weser-Bedarf aus dem Spurjahr ab ts.
  function simulate(V0, start, ts, days, opt = {}) {
    const reduced = opt.reduced !== false, adapt = opt.adapt ?? 20;
    const r = adapt ? ratio(start, ts) : 1;
    let V = V0; const vol = new Float32Array(days), qin = new Float32Array(days), qout = new Float32Array(days);
    for (let k = 0; k < days; k++) {
      const d = start + k * DAY; let td = ts + k * DAY;
      const [, tm, tdd] = ymd(td); if (tm === 2 && tdd === 29) td += DAY;
      let q = Q[idx(td)]; if (q == null) return null;
      if (adapt) q *= r + (1 - r) * (1 - Math.exp(-k / adapt));
      const m = ymd(d)[1];
      // unter 40 Mio.: Mindestabgabe, im Winter (Nov.–Feb.) seit 2018 nur 4 m³/s
      let o = reduced && V < 29 ? 3 : V < 40 ? (m >= 11 || m <= 2 ? 4 : 6) : demand(td, m);
      let Vn = V + (q - o) * K;
      const lim = upper(d + DAY);
      if (Vn > FULL) { o += (Vn - FULL) / K; Vn = FULL; }  // Hochwasserentlastung
      else if (Vn > lim) {
        // über der Leitlinie: bis zur Linie abgeben; liegt der See schon darüber, Überschuss in ~5 Tagen abbauen (max. 120 m³/s)
        const target = V > lim ? Math.max(lim, V - (V - lim) / 5) : lim;
        o = Math.max(o, Math.min(q + (V - target) / K, 120)); Vn = V + (q - o) * K;
        if (Vn > FULL) { o += (Vn - FULL) / K; Vn = FULL; }
      }
      Vn = Math.max(Vn, 0.5);
      vol[k] = V; qin[k] = q; qout[k] = o; V = Vn;
    }
    return { vol, qin, qout };
  }
  function pct(xs, p) {
    const s = [...xs].sort((a, b) => a - b), k = (s.length - 1) * p, f = Math.floor(k), c = Math.min(f + 1, s.length - 1);
    return s[f] + (s[c] - s[f]) * (k - f);
  }
  function ensemble(V0, startISO, days, pool, opt) {
    const [sy, sm, sd] = startISO.split('-').map(Number), start = utc(sy, sm, sd), runs = [];
    for (let t = pool[0]; t <= pool[1]; t++) {
      const ty = sm >= 10 ? t : t + 1;
      const r = simulate(V0, start, utc(ty, sm, sd), days, opt);
      if (r) { r.year = t; runs.push(r); }
    }
    return { start, runs };
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
  return { init, simulate, ensemble, pct, volume, level, utc, ymd, DAY, FULL };
})();
