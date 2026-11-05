# Pilotbetrieb: Bedienablauf, Prüfung und Plan für eine reale Lerngruppe

Stand: 5. November 2026, Arbeitspaket 4, Version 0.0.3.

**Einordnung:** Es standen keine externen Testpersonen zur Verfügung. Der hier beschriebene Durchlauf wurde mit Testkonten automatisiert im Browser ausgeführt (Playwright, `tests/e2e/test_pilot.py`), einmal gegen den Testserver der Testsuite und einmal gegen eine echte systemd-Installation in einem Ubuntu-26.04-Container mit den Produktionsgrößen (60 Fragen je Simulation). Das ist **keine reale Nutzerabnahme**. Abschnitt 4 beschreibt den reproduzierbaren Ablauf für die spätere Prüfung mit tatsächlichen Lernenden und einem Dozenten.

## 1. Durchlauf aus der Perspektive der drei Rollen

Szenario: Ein freiberuflicher Dozent bereitet im Auftrag eines Bildungsunternehmens eine Lerngruppe auf LPIC-3 305 vor. Der Administrator des Unternehmens betreibt den Trainer.

### 1.1 Administrator

| Schritt | Ergebnis im Durchlauf |
|---|---|
| Installation und Erstinbetriebnahme | `lpic3ctl install` auf vier Distributionen, siehe `docs/installationstest.md` |
| Erstadministrator anlegen | erstes registriertes Konto erhält Administratorrechte (im Browser geprüft); alternativ `lpic3ctl user create --role admin` |
| Anmeldung, Systemstatus | `/health` im Browser, *Verwaltung › Statistik*, `lpic3ctl status`/`check` |
| Benutzer und Betreuer verwalten | *Verwaltung › Benutzer › Benutzer anlegen*: Konto `dozent…` mit Rolle Betreuer und Startpasswort, ohne CLI |
| Lerngruppen einrichten | eigene Gruppe angelegt; der Dozent sieht sie nicht und erhält 403 |
| Zusatzfragen importieren und freigeben | mitgelieferte Zusatzpools erscheinen unter *Freigaben*, nicht freigegeben; Import und systemweite Freigabe sind durch die bestehenden Tests abgedeckt |
| Backup und Restore | CLI, geprüft in `docs/installationstest.md` |

### 1.2 Dozent (Betreuer)

| Schritt | Ergebnis im Durchlauf |
|---|---|
| Anmeldung | mit dem vom Administrator mitgeteilten Startpasswort |
| Eigene Lerngruppe anlegen | *Verwaltung › Gruppen*, Beitritt „offen“ |
| Lernende aufnehmen | Lernender tritt selbst bei (offen) oder wird hinzugefügt/freigegeben |
| Prüfungsmodul auswählen | Modul 305 |
| Fragen und LABs sichten | *Verwaltung › Fragen* (Filter Modul), LAB-Seite mit Abschnitt *Hinweise für Dozenten* |
| Zusatzfragen für die eigene Gruppe freigeben | *Verwaltung › Freigaben*: Ergänzungspool 305-300 für die Gruppe angehakt. **Befund:** Vor Arbeitspaket 4 konnten Betreuer nur eigene Importe freigeben; die mitgelieferten Pools brauchten den Administrator. Behoben (Betreuer dürfen mitgelieferte Zusatzpools für eigene Gruppen freigeben, systemweit weiterhin nur Administratoren). |
| LAB empfehlen und LAB-Fortschritte einsehen | Gruppenseite: Häkchen *Empfohlen*, Tabelle *LAB-Stände der Gruppe* zeigt den Lernenden nach Abschluss |
| Ergebnisse nach Prüfungszielen | *Auswertung je Prüfungsziel* zeigt Antworten aus Eingangstest, Übungen, Kapiteltest und Simulation |
| Fachliche Schwächen erkennen, Übungen auswählen | Einschätzung „vertiefen“/„sicher“ je Ziel, Liste häufig falscher Fragen, Link direkt in den Übungsmodus des Ziels |

### 1.3 Lernender

| Schritt | Ergebnis im Durchlauf |
|---|---|
| Registrierung | selbst registriert; keine Verwaltungslinks, `/admin/...` liefert 403 |
| Lerngruppe beitreten | *Gruppen › Beitreten* |
| Modul auswählen, Eingangstest | *Module*, Eingangstest mit allen Fragen beantwortet, Ergebnis je Thema |
| Englische Fragen mit deutscher Sprachhilfe | Übersetzung einblenden, Antwort prüfen, Erklärung |
| Gesperrte Zusatzfragen unsichtbar | vor der Freigabe liefert *Nur Zusatzfragen üben* keine Frage; nach der Freigabe erscheinen sie mit Kennzeichnung *Zusatzfrage* |
| LAB-Umgebung vorbereiten | Seite *LAB-Umgebung einrichten* |
| Fach-LAB starten, Fortschritt markieren | *LAB beginnen* → in Bearbeitung → *Als abgeschlossen markieren* |
| Fragen zum LAB-Prüfungsziel üben | Schaltfläche auf der LAB-Seite |
| Kapiteltest, Prüfungssimulation | Kapiteltest des ersten Themas, Simulation mit Timer (60 Fragen auf der echten Installation), Ergebnis mit Themenübersicht und Fragendetails |
| Eigene Ergebnisse | *Fortschritt*, *Alle Ergebnisse* |

## 2. Benutzerfreundlichkeit: Prüfpunkte und Befunde

| Prüfpunkt | Befund |
|---|---|
| Funktionen auffindbar | Hauptnavigation Start, Module, Labs, Vokabeln, Fortschritt, Gruppen, Verwaltung; LAB-Umgebung über die Labs-Seite; Auswertung über die Gruppenseite |
| Navigation und Bezeichnungen | durchgehend deutsch; Fachbegriffe (Prüfungsziel, Kapiteltest, Simulation, Zusatzfrage) werden auf den Seiten erklärt |
| Technische Hürden | Lernende und Dozenten brauchen keine CLI. CLI nur für Installation, Backup/Restore und Notfälle (Passwort des Administrators). |
| Dozent ohne Administrator | ja, nach der Änderung in Arbeitspaket 4 (Freigabe mitgelieferter Zusatzpools). Offen: Betreuer können keine Konten anlegen; Lernende registrieren sich selbst oder der Administrator legt Konten an. |
| Gesperrte Zusatzfragen unsichtbar | geprüft im Pilotlauf, in `tests/test_release.py` und in `tests/test_questions_ap3.py` |
| Rollen und Gruppenrechte serverseitig | 403 für Lernende auf Verwaltungsseiten, 403 für Betreuer auf fremden Gruppen (Gruppenseite, LAB-Empfehlung, Auswertung), geprüft |
| Desktop und Smartphone | 390 px: Module, Modulseite, Labs, LAB-Umgebung, LAB-Detail, Übungsfrage, Fortschritt, Gruppenseite und Auswertung ohne horizontales Scrollen |
| JavaScript-Fehler, fehlgeschlagene Anfragen | keine (Browsertests brechen sonst ab) |

Weitere Beobachtungen, nicht behoben (Empfehlungen):

1. Startpasswörter: Der Administrator muss das Startpasswort persönlich übermitteln; es gibt keine E-Mail. Für Kurse mit vielen Teilnehmern ist die Selbstregistrierung mit Freigabe (Einstellung *Registrierung mit Freigabe*) der einfachere Weg.
2. Die Prüfungssimulation lässt sich nach Schließen des Browsers nicht fortsetzen (bekannte Einschränkung).
3. Die Seite *LAB-Umgebung einrichten* ist nur angemeldet erreichbar; für Interessierte ohne Konto steht `docs/lab-umgebung.md` im Repository.
4. In der Gruppenauswertung erscheint ein Urteil erst ab fünf Antworten je Ziel; kleine Gruppen zu Kursbeginn sehen deshalb vor allem „zu wenig Antworten“. Das ist beabsichtigt, sollte dem Dozenten aber gesagt werden.
5. Der Footer zeigt die Programmversion; nach einem Upgrade erkennt man daran den Stand (0.0.3).

## 3. Automatisierter Durchlauf

```bash
# gegen den Testserver der Testsuite (verkleinerte Prüfungen)
.venv/bin/pytest tests/e2e/test_pilot.py --browser chromium

# gegen eine echte Installation (zum Beispiel Testserver oder Container), leer oder mit bekanntem Administrator
LPIC3_E2E_BASE=http://192.0.2.10:8080 .venv/bin/pytest tests/e2e/test_pilot.py --browser chromium
LPIC3_E2E_BASE=https://lpic3.example.org LPIC3_E2E_ADMIN_USER=admin LPIC3_E2E_ADMIN_PASS=… .venv/bin/pytest tests/e2e/test_pilot.py
```

Der Durchlauf legt Konten `dozent<Zahl>`, `lernender<Zahl>` und, falls kein Administrator übergeben wurde, `e2eadmin<Zahl>` sowie zwei Gruppen an. Er gehört nicht auf eine produktive Installation mit echten Daten; dort nur mit einer frisch wiederhergestellten Kopie arbeiten.

Ergebnis am 5. November 2026: 7 Schritte bestanden gegen den Testserver (34 s) und gegen die systemd-Installation im Container `lpic3-ubu26` (Ubuntu 26.04, Python 3.14, 27 s); Journal des Dienstes ohne Fehler.

## 4. Plan für den Pilotbetrieb mit einer realen Lerngruppe

Ziel: Ein Dozent und drei bis acht Lernende arbeiten zwei bis vier Wochen mit dem Trainer an einem Modul. Erfolgskriterium ist nicht die Prüfungsleistung, sondern ob alle Beteiligten ihre Aufgaben ohne Hilfe durch den Administrator erledigen können und welche Hürden auftreten.

### 4.1 Vorbereitung (Administrator, 1 Stunde)

1. Installation nach `docs/installation.md` auf einem Server oder einer VM mit HTTPS-Reverse-Proxy; `lpic3ctl check` ohne Befund; Backup-Cronjob eingerichtet.
2. Erstes Konto registrieren (Administrator), Registrierung auf „mit Freigabe“ stellen (*Verwaltung › Einstellungen*), falls die Teilnehmer sich selbst registrieren sollen.
3. Konto für den Dozenten anlegen (Rolle Betreuer), Startpasswort persönlich übergeben.
4. Dem Dozenten `docs/bedienung.md` (Abschnitt *Für Betreuer*) und `docs/lab-umgebung.md` geben.

### 4.2 Kursstart (Dozent, 1 Unterrichtseinheit)

1. Dozent legt die Gruppe an (Beitritt mit Freigabe oder offen), wählt das Modul und sichtet Prüfungsziele, Fragen (*Verwaltung › Fragen*) und LABs mit Dozentenhinweisen.
2. Dozent entscheidet, ob Zusatzpools freigegeben werden (Rechtestatus beachten: Ergänzungspool „cleared“, ExamTopics „unverified“).
3. Teilnehmer registrieren sich oder erhalten Konten, treten der Gruppe bei, wählen das Modul und absolvieren den Eingangstest (10 Fragen).
4. Dozent öffnet *Auswertung je Prüfungsziel* und bespricht, mit welchen Themen begonnen wird.
5. Teilnehmer richten bis zur nächsten Einheit ihre LAB-Umgebung nach `docs/lab-umgebung.md` ein (Funktionsprüfung Abschnitt 11).

### 4.3 Laufender Betrieb (2 bis 4 Wochen)

- Lernende üben eigenständig (Fragen mit Sprachhilfe, Vokabeln), bearbeiten die vom Dozenten empfohlenen LABs und setzen den LAB-Status.
- Dozent prüft wöchentlich LAB-Stände und Auswertung, wählt Übungen und bespricht häufig falsch beantwortete Fragen.
- Zum Abschluss eine Prüfungssimulation (60 Fragen, 90 Minuten) je Teilnehmer; Ergebnisse unter *Alle Ergebnisse* und in der Auswertung.

### 4.4 Beobachten und festhalten

Je Rolle ein kurzes Protokoll (Freitext oder Tabelle):

| Frage | Administrator | Dozent | Lernende |
|---|---|---|---|
| Welche Schritte waren ohne Anleitung klar? | | | |
| Wo wurde Hilfe gebraucht (von wem)? | | | |
| Welche Bezeichnungen waren unverständlich? | | | |
| Welche Funktion fehlte? | | | |
| Fehler, Abbrüche, langsame Seiten (mit Uhrzeit, für `lpic3ctl logs`)? | | | |
| Smartphone-Nutzung: welche Seiten? Probleme? | | | |
| LAB-Umgebung: Zeit bis zur Funktionsprüfung, verwendete Virtualisierung | | | |
| Fachliche Einwände zu Fragen (ID aus der Ergebnisseite) | | | |

Abschluss: Protokolle zusammen mit `lpic3ctl status`, der Zahl der Antworten (*Verwaltung › Statistik*) und einer Sicherung (`lpic3ctl backup`) auswerten; fachliche Einwände zu Fragen über die Fragen-ID nachprüfen und gegebenenfalls deaktivieren.

### 4.5 Abbruchkriterien

Pilot unterbrechen und melden, wenn: Daten verloren gehen (Lernstände fehlen nach Neustart), eine Rolle fremde Daten sieht, der Dienst nach einem Neustart nicht startet oder eine Simulation nicht auswertbar ist. Vorher immer `lpic3ctl backup`.
