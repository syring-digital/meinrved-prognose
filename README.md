# Edersee-Prognosemodell (Konzept, Stufe 1–4)

Rechenkern und Auswertung für die Wasserstandsprognose. Gehört nicht zur App und wird von Xcode nicht gebaut.
Konzeptseite (privat): https://claude.ai/artifact/T9mqoLaNTVtshVvmCEHezY

## Ablauf

Alle Befehle aus diesem Ordner, Python 3 ohne Zusatzpakete:

```
python3 fetch.py       # Tageswerte von wasserstand.edersee.me nach daten/roh (beim ersten Mal ~10 Min.)
python3 parse.py       # -> daten/hist.csv
python3 sim.py         # Nachrechentest 2005–2024 mit echten Zuflüssen (--tabelle: ohne echte Abgaben)
python3 validate.py    # Rückblick-Test der Wahrscheinlichkeiten -> ausgabe/bewertung.json (einige Minuten)
python3 forecast.py    # Saisonprognose ab dem letzten Datentag -> ausgabe/prognose.json
python3 export.py      # -> seite/data.json
python3 build_page.py  # -> seite/edersee-prognose.html
python3 check_js.py    # seite/model.js gegen sim.py prüfen
```

`daten/`, `ausgabe/`, `seite/data.json` und die gebaute Seite sind per `.gitignore` ausgeschlossen. Die Tageswerte stammen von einer privaten Seite; vor einer Veröffentlichung braucht es die Erlaubnis des Betreibers.

## Stufe 3 und 4 (aktuelle Seite)

```
python3 climate.py      # DWD-Tageswerte (Niederschlag, Temperatur) laden -> daten/klima.csv
python3 calib_rr.py     # Abflussmodelle kalibrieren -> modell/rr_parameter.json (einige Minuten)
python3 validate3.py    # Rückblick-Test Stufe 3 -> ausgabe/bewertung3.json (einige Minuten)
python3 analyse/hindcast3.py   # Stufe 2 gegen Stufe 3 je Vorlaufzeit -> ausgabe/hindcast3.json
python3 dwd_forecast.py # DWD ICON-EPS, 40 Läufe -> ausgabe/dwd_eps.json
python3 live.py         # Pegelonline + WSA-Abgabeplan aus dem PDF -> ausgabe/live.json
python3 forecast3.py    # Ensemble ab heute -> ausgabe/prognose3.json
python3 export3.py      # -> seite/data3.json
python3 build_page3.py  # -> seite/edersee-prognose.html
python3 check_js3.py    # seite/model3.js gegen stage3.py prüfen
python3 whatif.py       # Haltelinie in echten Jahren (Konsole)
```

Täglich nötig sind nur `climate.py`, `dwd_forecast.py`, `live.py`, `forecast3.py`, `export3.py`, `build_page3.py`. Die Kalibrierung und die Rückblick-Tests nur nach Modelländerungen.

- **Eder-Modell** (`rr.py`, GR4J + Schnee + Verdunstung nach Oudin): 12 DWD-Niederschlags- und 3 Klimastationen, Tages-NSE 0,85 (Kalibrierung 1991–2010 und Prüfung 2011–2026), Monats-NSE 0,94.
- **Weser-Restgebiet** (Fulda, Werra ohne Edersee, 18 + 4 Stationen): kalibriert an BfG-Tageswerten Hann. Münden 2013–2015 (`daten/bfg/hmue_q_2013_2015.csv`, per Texterkennung aus den Jahrbuch-PDFs, alle Monatsmittel geprüft), an Stütztagen (Rest = 55 − Abgabe) und an Pegelonline Bonaforth + Letzter Heller. NSE 0,81.
- **Stützbedarf** = 55 m³/s − Restabfluss (Mai–Oktober, höchstens 40). Belegt durch 2015: Hann. Münden wochenlang 53–57 m³/s.
- **Ensemble** (`stage3.py`): Zufluss = gemessener Zufluss im Wetterjahr × Modell(heutiger Zustand) / Modell(damaliger Zustand), am Start angeglichen; erste Woche DWD ICON-EPS; Restabfluss mit Monatsfaktoren und am Start an Pegelonline angeglichen; WSA-Plan für die ersten Tage.
- **Ergebnis Rückblick:** Fehler des Medians nach 7/14/28/60 Tagen 5,4/8,7/12,9/20,5 (Stufe 2) → 4,8/8,1/12,2/20,0 (Stufe 3) → 3,9/6,7/11,2/18,6 mit perfekter Woche 1; nach 120 Tagen alle gleich (Stufe 3 mit 26,0 leicht hinter Stufe 2 mit 25,3); mit WSA-Plan nach 7 Tagen rund 3. Regatta-Skill ab Oktober leicht, ab Februar deutlich über der Statistik.
- **Grenze:** Extremsommer wie 2026 werden unterschätzt (Weser-Modell zu hoch bei extremem Niedrigwasser).
- `seite/template3.html` + `seite/model3.js` sind die aktuelle Seite; `template.html`/`model.js` die alte Fassung (Stufe 1+2).

## Modell (Stufe 2)

Seebilanz pro Tag: Inhalt morgen = Inhalt heute + (Zufluss − Abgabe) × 0,0864 (Mio. m³).

- **Inhalt** immer aus dem Pegel mit der Kurve „Inhalt neu“ (edersee.me rechnet bis Anfang 2004 mit der alten Kurve).
- **Zufluss** als Bilanzzufluss (Abgabe + Inhaltsänderung). Er passt zur Kurve, ist aber einzeln verrauscht, weil 1 cm Pegel bei vollem See ~12 m³/s entspricht.
- **Ensemble (Stufe 2):** Zuflüsse der Jahre ab 2000 ab dem heutigen Kalendertag, in den ersten ~20 Tagen an den heutigen Zufluss angeglichen. Der Weser-Bedarf im Sommer stammt aus den Abgaben desselben Jahres.
- **Abgaberegeln** (`sim.py`, abgeleitet aus 2005–2026):
  - unter 29 Mio. m³: 3 m³/s (2026 mit dem RP Kassel)
  - unter 40 Mio. m³: 6 m³/s, im Winter (Nov.–Feb.) 4 m³/s wie seit 2018
  - Winter-Leitlinie (1.12. 110, 1.1. 140, 1.2. 160, 1.3. 175, 1.4. 192, Ende April Vollstau): darüber bis zur Linie abgeben, höchstens 120 m³/s
  - Juni–Oktober: Abgabe des Spurjahres, 6–40 m³/s
  - über Vollstau: Hochwasserentlastung

`seite/model.js` ist eine Kopie des Rechenkerns für den Browser. Änderungen immer in `sim.py` und `model.js` machen, danach `check_js.py` laufen lassen.

## Stand der Bewertung (20.10.2026)

- Nachrechnen mit echten Zuflüssen: mittlerer Fehler 3,6 Mio. m³ am 1. Mai, 7,7 am 1. Juli, 6,6 am 1. September. Mit festen Monatswerten statt der echten Abgaben: 3,9 / 18 / 34. Der Sommer hängt also am Weser-Bedarf.
- Wahrscheinlichkeiten: Vom Oktober aus nicht besser als die reine Statistik. Klar besser sind nur Vollstau ab einem Start im Mai und Regatten im Juli ab einem Start im Februar.
- Kalibrierung: Vollstau stimmt (62 % vorhergesagt, 67 % eingetreten). Regatten sind zu optimistisch (97 % gegen 90 %), Ausfälle 2017 und 2026.
- Offene Baustelle für Stufe 3: Weser-Stützbedarf aus den Pegeln in Hann. Münden, Fulda und Werra plus DWD-Prognose. Juli 2026 gab das WSA 30–39 m³/s ab, mehr als in fast allen Spurjahren.

## Hinweise

- Der Seepegel schwankt im Tagesverlauf um etwa 5 cm (vermutlich Pumpspeicher Waldeck). Trends nur aus Werten zur gleichen Uhrzeit (07:00) oder aus Tagesmitteln berechnen.
- Pegelonline Schmittlotheim liefert bei Trockenheit fast genau den Seezufluss, hängt aber gelegentlich stundenlang.
- Das WSA-PDF (`https://pss.wsv.de/wsahmue/VorhersageOberweser.pdf`) enthält auf Seite 13 die Tabelle „Abgabenplanung Edertalsperre“ für 5 Tage.
- `seite/template.html` ist ein Stand vom 19.10.2026: Stufe-1-Kennzahlen, Starttag und Regattatermine 2027 stehen dort fest.
- `analyse/` enthält die Explorationsskripte, mit denen Regeln, Leitlinie und Spurenpool bestimmt wurden (`rules.py`, `env.py`, `explore.py`, `tune.py`, `tau.py`, `dtest.py`).
