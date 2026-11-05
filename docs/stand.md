# Entwicklungsstand

Stand: 5. November 2026, Entwicklungsstand nach v0.0.2 (keine stabile Produktionsversion). Behebungsstatus der Abnahmebefunde: `docs/abnahmebericht.md`. Installationstest: `docs/installationstest.md`.

## Zusammenfassung

Die Anwendung ist lauffähig, installierbar und in ihren Kernfunktionen getestet: Mehrbenutzerbetrieb mit Rollen, englische Prüfungsfragen mit deutschen Sprachhilfen, Prüfungssimulation, Eingangstest, Vokabeltraining, Laboraufgaben, Fragenimport, Lernfortschritt, Offline-Nutzung, `lpic3ctl` für Installation und Betrieb.

## Erledigt

### Grundstruktur

- FastAPI-Anwendung mit Jinja2-Templates, Uvicorn, SQLite im WAL-Modus, SQLAlchemy, Alembic (Migration `0001`).
- Konfiguration über `LPIC3_*`-Umgebungsvariablen, `.env.example`, `deploy/lpic3-trainer.env.example`.
- Health-Endpunkt `/health` mit Schema-Version.

### Mehrbenutzerbetrieb

- Registrierung (offen oder mit Freigabe), Anmeldung, Abmeldung, Passwortänderung.
- Argon2id, serverseitige Sitzungen, HttpOnly/SameSite-Cookie, Origin-Prüfung bei POST.
- Rollen Administrator, Betreuer, Lernender mit Prüfung im Backend.
- Benutzerverwaltung in der Weboberfläche und per `lpic3ctl user`.
- Lerngruppen mit Beitritt offen oder mit Freigabe, Betreuer sehen den Lernstand ihrer Mitglieder.
- Datentrennung: Lernstände sind nur für den eigenen Benutzer erreichbar (getestet).

### Lerninhalte

- Prüfungsziele aller vier Module (300, 303, 305, 306) in Version 3.0 mit Themen, Zielen, Gewichten, deutschen Zusammenfassungen und Werkzeuglisten. Quelle: offizielle LPI-Prüfungsziele; Zusammenfassungen sind eigene Formulierungen.
- 245 eigene Prüfungsfragen (300: 62, 303: 62, 305: 60, 306: 61) in zwei Dateien je Modul, jede mit deutscher Übersetzung von Frage und Antworten sowie deutscher Erklärung. Jedes Prüfungsziel hat mindestens eine Frage; die Verteilung folgt grob dem Gewicht der Ziele.
- Glossar mit 271 Fachbegriffen (Englisch, Deutsch, teils Erklärung). Jede mitgelieferte Frage trifft mindestens einen Glossarbegriff (getestet).
- 12 Laboraufgaben (3 je Modul) mit Umgebung, Schritten, Befehlen und Selbstkontrollfragen.
- Lizenz der Inhalte: CC BY-SA 4.0 (`content/LICENSE.md`), getrennt vom MIT-lizenzierten Code.

### Lernmodus

- Modulauswahl je Lernendem.
- Üben für ganzes Modul oder einzelnes Prüfungsziel; bevorzugt neue, dann falsch beantwortete Fragen.
- Sprachhilfen: Übersetzung ein-/ausblenden, Fachbegriffe markieren, Begriff antippen für Erklärung, Begriff merken. Nutzung wird gespeichert, Bewertung bleibt unabhängig.
- Ergebnisseite mit richtiger Lösung und deutscher Erklärung.
- Vokabelliste mit Wiederholung (Karten), Glossar mit Suche.
- Eingangstest je Modul mit Auswertung je Thema (sicher/üben).
- Prüfungssimulation für Modul (60 Fragen, 90 Minuten, nach Themengewicht verteilt) und Kapitel (15 Fragen), ohne Sprachhilfen, mit Timer und automatischer Abgabe, Ergebnis je Thema und Frage, Historie.
- Fortschrittsseite und JSON-Endpunkt `/api/progress`.

### Labs

- Anleitungen mit Schritten, Befehlen (nur Anzeige) und Selbstkontrolle; als erledigt markierbar.

### Fragenimport und Verwaltung

- JSON-Format Schema Version 1 (`content/README.md`), vollständige Validierung vor dem Import, Ablehnung mit Fehlerliste.
- Import über Weboberfläche (max. 5 MB) und `lpic3ctl import`, Sichtbarkeit privat/öffentlich, Importchargen mit Lizenz und Autor, Löschen von Chargen, Deaktivieren einzelner Fragen.
- Private Fragen sind für Importierende, Administratoren und Mitglieder betreuter Gruppen sichtbar.
- Importierte Texte werden immer escaped (getestet).
- Rollen und Freigabe: Nur Administratoren und Betreuer importieren Fragen; Lernende können nichts importieren, anlegen, ändern oder freigeben. Jeder Import braucht Quelle und Prüfungsgeneration (`source`, `exam_version`) sowie einen Rechtestatus und bleibt unveröffentlicht. Betreuer geben eigene Importe unter *Verwaltung › Freigaben* für eigene Gruppen frei, Administratoren systemweit oder für beliebige Gruppen. Lernende sehen den freigegebenen Grundbestand und die Freigaben ihrer Gruppen; freigegebene Importe sind bei jeder Frage als Zusatzfrage mit Quelle, Prüfungsgeneration und Rechtestatus markiert, mit Pool-Filter beim Üben. Die mitgelieferten Projektfragen bilden den bereits freigegebenen Grundbestand. Migrationen `0002` und `0003`.
- Ergänzungspools unter `content/questions/extra/<modul>-ergaenzung-2026-11.json`: 221 eigene Zusatzfragen (300: 51, 303: 60, 305: 50, 306: 60) mit Referenz je Frage, unveröffentlicht bis zur Freigabe; Bericht in `docs/zusatzfragen-bericht.md`. Damit je Modul mindestens 60 Zusatzfragen.
- Mitgelieferte Zusatzquellen unter `content/questions/extra/`: je zehn Fragen aus den öffentlich abrufbaren ExamTopics-Dumps zu den Prüfungen 305-300 und 300-300, bereitgestellt vom Auftraggeber mit deutscher Sprachhilfe (Herkunft per Websuche geprüft, Nutzungsrechte nicht geklärt, Fundstellen in `content/questions/extra/README.md`). Diese Dateien sind von der CC-BY-SA-Lizenz der übrigen Inhalte ausgenommen.

### Offline

- Web App Manifest, Service Worker: statische Dateien und besuchte Seiten bleiben verfügbar, Offline-Seite als Rückfall, Banner ohne Verbindung.

### Installation und Betrieb

- Arbeitspaket 1 (5. November 2026): Echte Root-Installation mit systemd in LXD-Containern (Debian 12/13, Ubuntu 24.04/26.04) einschließlich Neustart, Upgrade von v0.0.2, Backup, Restore, Rollback, Deinstallation und Reverse Proxy. Behoben: Konfigurationsverzeichnis für den Dienstbenutzer nicht lesbar (Installation v0.0.2 brach ab), Rollback nach Schemaänderung ließ den Dienst nicht mehr starten (jetzt Prüfung und `rollback --restore`), `restore` unter Debian 12 (Python 3.11.2) abgebrochen, Traceback ohne Root, Dienst in Neustartschleife galt als inaktiv, Eigentümer nach Root-Befehlen, Unit-Härtung (systemd-analyze 1.3 bis 2.0 OK), SPDX-Lizenzangabe, Alembic-Meldungen nur bei Migrationsbefehlen.
- Nach 0.0.2: Schreibtransaktionen beginnen mit BEGIN IMMEDIATE, Busy-Timeout 15 s, Begriffsmuster werden gecacht (Nebenläufigkeitstest war mit größerem Fragenbestand instabil); Ergänzungspools mit 221 Zusatzfragen, Migration 0005 (Feld `reference`).
- Version 0.0.2: Restore verweigert die Ausführung bei laufendem, nicht über systemd verwaltetem Server, sichert vorher, prüft danach die Integrität und wartet auf den Health-Check; CLI legt das Datenverzeichnis selbst an; Administratoren legen Benutzer in der Weboberfläche an; Betreuer sehen nur eigene Mitglieder und Importe; Importchargen tragen Prüfungsnummer und Original-URL; Dublettenwarnung beim Import; `active: false` je Frage; SQLite-Fremdschlüssel sind während Migrationen aus (Migration 0004, Upgrade-Test mit Bestandsdaten).

- `lpic3ctl` mit allen in AGENTS.md vorgesehenen Befehlen plus `rollback`, `serve`, `migrate`, `content-sync`, `import`, `validate`, `user`.
- Native Installation mit Systembenutzer, venv (`deploy/create-venv.sh`), gehärteter systemd-Unit, Konfiguration unter `/etc/lpic3-trainer`, Daten unter `/var/lib/lpic3-trainer`.
- Upgrade mit automatischer Sicherung, Erhalt der Konfiguration, automatischer Rückfall bei Fehler; `rollback`.
- Backup über SQLite-Backup-API als tar.gz mit Konfiguration, Rotation mit `--keep`; Restore mit Rückfrage und Sicherheitskopie.
- `check`, `status`, `version` (Git-Tags), `logs`.
- Dockerfile und Docker Compose mit gleicher Datenstruktur.

### Dokumentation

- `docs/architektur.md`, `docs/installation.md`, `docs/administration.md`, `docs/bedienung.md`, `docs/entwicklung.md`, `content/README.md`.

## Testergebnisse (4. November 2026, nach Erweiterung des Fragenbestands erneut ausgeführt)

| Suite | Umfang | Ergebnis |
|-------|--------|----------|
| pytest Backend (`tests/`, ohne e2e) | 99 Tests (Stand 5. November 2026, Arbeitspaket 1: dazu Eigentümer des Konfigurationsverzeichnisses, tar-Fallback für Python 3.11.2, Dienstzustand `activating`, unlesbare Konfiguration, Revisionsprüfung, Rollback-Verweigerung und `--restore`): Registrierung, Rollen, Sitzungen, Datentrennung, Importvalidierung und Import, Üben, Sprachhilfe, Vokabeln, Labs, Simulation, Eingangstest, Gruppen, Verwaltung, 8 parallele Benutzer, `lpic3ctl` (Migration, Benutzer, Backup, Restore, Check, Install/Upgrade/Rollback/Uninstall/Purge mit Stub-Systembefehlen), Import- und Freigaberechte (Lernende 403, Pflichtfelder Quelle und Prüfungsgeneration, Import unveröffentlicht, Freigabe durch Betreuer nur für eigene Importe und Gruppen, systemweite Freigabe nur Administrator, Grundbestand freigegeben, externe Quellen nicht), Restore-Regression (laufender Server, Neustart, defektes Archiv), Migrationen mit Bestandsdaten, Benutzeranlage, Betreuer-Sichtbarkeit, Dubletten, Inaktiv-Kennzeichen, Herkunftsfelder | 94 bestanden |
| Playwright (`tests/e2e/`, Chromium) | 12 Tests: Registrierung/Anmeldung/Abmeldung, Üben mit Übersetzung, Begriffsmarkierung, Popover und Merken, Simulation ohne Hilfen mit Timer, Eingangstest und Fortschritt, Labs, Import über Oberfläche mit gültiger und ungültiger Datei, Rollenprüfung (403), Gruppenfreigabe, Handy-Darstellung 390 px ohne horizontales Scrollen, Offline-Verhalten über Service Worker, Import und Freigabe durch Betreuer mit Kennzeichnung beim Lernenden, Lernender ohne Zugriff auf Verwaltungsseiten, Rückfrage bei unbeantworteten Prüfungsfragen, Benutzeranlage durch Administrator | 12 bestanden |
| ruff check / ruff format | `app`, `tests`, `migrations` | ohne Befunde |

JavaScript-Fehler und fehlgeschlagene Netzwerkanfragen werden in den Browsertests erfasst; keine aufgetreten.

## Bekannte Einschränkungen

- **Native systemd-Installation nur in Containern geprüft.** Die Installation lief als Root mit echtem systemd in LXD-Systemcontainern (Debian 12/13, Ubuntu 24.04/26.04, x86_64), nicht auf blankem Metall oder in einer VM mit eigenem Kernel und nicht auf ARM64. Testplan für einen echten Server in `docs/installationstest.md`, Abschnitt 5. Der Installer von v0.0.2 ist auf echten Systemen defekt (siehe dort); Neuinstallationen brauchen den aktuellen Stand.
- **Docker nicht getestet.** Auf dem Entwicklungssystem war kein Docker verfügbar. Dockerfile und Compose-Datei sind ungetestet.
- **Fragenanzahl.** Mit 60 bis 62 Fragen je Modul zieht eine Modulsimulation nahezu den gesamten Bestand; wiederholte Simulationen enthalten daher weitgehend dieselben Fragen. Kapiteltests mit 15 Fragen sind bei kleinen Themen entsprechend kürzer. Nur 3 von 245 Projektfragen sind Mehrfachauswahl (Abnahmebefund P2-7, offen).
- **Zwei ExamTopics-Fragen inaktiv.** `300-examtopics-screenshot-08` und `305-examtopics-screenshot-03` sind fachlich unsicher und mit `active: false` ausgeschlossen (P2-8).
- **Sprachhilfe erkennt Begriffe wörtlich.** Flexionen (z. B. „revoked“ zu „revoke“) werden nur erkannt, wenn der Begriff so im Glossar steht oder der Frage zugeordnet ist.
- **Prüfungssimulation ohne Fortsetzung nach Browserschließen.** Die Antworten werden erst bei Abgabe gespeichert; die Zeit läuft serverseitig weiter.
- **Keine E-Mail.** Passwort zurücksetzen erfolgt durch Administratoren (neues Passwort wird angezeigt).
- **Offline.** Antworten ohne Verbindung gehen verloren; es gibt keine Warteschlange.
- **Zusatzfragen mit ungeklärten Rechten.** Die mitgelieferten ExamTopics-Dateien verstoßen möglicherweise gegen Rechte des LPI oder Dritter. AGENTS.md untersagt das Veröffentlichen unberechtigt kopierter Exam-Dumps im Repository; die Aufnahme erfolgte auf ausdrückliche Anweisung des Auftraggebers mit Kennzeichnung und Freischaltungspflicht. Die Verantwortung für die Nutzung liegt beim freischaltenden Betreuer.
- Prüfungsziele Version 3.0 vom Stand November 2026; LPI kündigt für 303 Änderungen an („Future Change Considerations“).

## Offene Aufgaben und nächste Schritte

Didaktische Festlegungen zu den Laboraufgaben und der Abgleich mit dem Stand stehen in `docs/lab-konzept.md` (nächste LAB-Überarbeitung: Einrichtungsanleitung, Erfolgskriterien, Dozentenhinweise, LAB-Status je Gruppe).

1. Installation nach dem Testplan in `docs/installationstest.md` auf einem echten Server oder einer VM nachvollziehen (blankes Metall, ARM64).
2. Docker-Image bauen und Compose-Betrieb prüfen.
3. Fragenbestand weiter ausbauen (Ziel: mindestens 120 je Modul, damit Simulationen variieren), weitere Labs.
4. Begriffserkennung um einfache Wortformen erweitern.
5. Browsertests auch mit Firefox/WebKit laufen lassen.
6. Migration `0002` ist die erste Schemaänderung; Upgrade- und Downgrade-Pfad wurden lokal mit Alembic geprüft, aber noch nicht auf einer produktiven Installation.
