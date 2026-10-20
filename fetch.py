"""Tageswerte (Pegel, Inhalt, Zufluss, Abfluss) von wasserstand.edersee.me laden, ein HTML je Monat nach daten/roh.
Vorhandene Monate werden übersprungen, der aktuelle und der vorige Monat immer neu geladen.
Hinweis: private Seite, vor einer Veröffentlichung der Daten Erlaubnis einholen."""
import os, sys, time, datetime as dt, urllib.request, urllib.parse, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW

today = dt.date.today()
fresh = {(today.year, today.month), ((today.replace(day=1) - dt.timedelta(1)).year, (today.replace(day=1) - dt.timedelta(1)).month)}


def get(ym):
    y, m = ym
    p = os.path.join(RAW, f'{y}-{m:02d}.html')
    if ym not in fresh and os.path.exists(p) and os.path.getsize(p) > 2000: return
    for _ in range(3):
        try:
            req = urllib.request.Request('https://wasserstand.edersee.me/monat.php', data=urllib.parse.urlencode({'monat': m, 'jahr': y}).encode(),
                                         headers={'User-Agent': 'MeinRVED-Prognose'})
            open(p, 'wb').write(urllib.request.urlopen(req, timeout=30).read()); time.sleep(0.2); return
        except Exception:
            time.sleep(2)
    print('nicht geladen:', y, m)


os.makedirs(RAW, exist_ok=True)
jobs = [(y, m) for y in range(1914, today.year + 1) for m in range(1, 13) if (y, m) <= (today.year, today.month)]
with cf.ThreadPoolExecutor(4) as ex: list(ex.map(get, jobs))
print('fertig,', len(os.listdir(RAW)), 'Monate in', RAW)
