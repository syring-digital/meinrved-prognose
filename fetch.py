"""Verlauf der Tageswerte (Pegel, Inhalt, Zufluss, Abgabe) bis Anfang November 2026: eingefrorener Stand von wasserstand.edersee.me
in daten/roh (ein HTML je Monat, im GitHub-Zwischenspeicher bzw. lokal). Dort wird nichts mehr abgerufen; neue Tage ergänzt nachtrag.py
aus PEGELONLINE und dem WSA-Abgabeplan. Der eingefrorene Stand liegt (nicht öffentlich) im Archiv des App-Projekts:
Archiv/Edersee-Historie/hist.csv (dieselbe Tabelle wie daten/hist.csv; zum Wiederherstellen dorthin kopieren und parse.py weglassen)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, HIST

if os.path.isdir(RAW) and os.listdir(RAW):
    print(len(os.listdir(RAW)), 'Monate in', RAW, '(nichts abgerufen)')
elif os.path.exists(HIST):
    print('Keine Monats-HTML, aber', HIST, 'ist vorhanden.')
else:
    raise SystemExit(f'Weder {RAW} noch {HIST} vorhanden: Archiv/Edersee-Historie/hist.csv nach {HIST} kopieren.')
