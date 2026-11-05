# Umsetzungs- und Abnahmebericht: Installation, LAB-Ausbau, Fragenqualität und Pilotbetrieb

Stand: 5. November 2026. Auftrag „LPIC-3-Trainer – Installation, LAB-Ausbau, Fragenqualität und Pilotbetrieb“, Ausgangsstand `main` Commit `bb822f1` (v0.0.2). Ergebnis: Version 0.0.3 (erste Testversion).

## 1. Bearbeitete Arbeitspakete, Commits und Pull Requests

| Arbeitspaket | Branch | Commit | Pull Request | Merge in `main` |
|---|---|---|---|---|
| AP1 Native Serverinstallation und Betrieb | `feat/ap1-install` | `a900edf` | #2 | `0780edc` |
| AP2 LAB-Umgebung und praktische Übungen | `feat/ap2-labs` | `5491b50` | #3 | `1e12420` |
| AP3 Prüfungsfragen und Prüfungssimulation | `feat/ap3-questions` | `a1b840b` | #4 | `a79967a` |
| AP4 Pilotbetrieb und vollständiger Bedienablauf | `feat/ap4-pilot` | siehe Git-Log | #5 | siehe Git-Log |

Alle Merges über GitHub (`gh pr merge --merge`), keine Schutzregeln umgangen. Jedes Arbeitspaket ist ein eigener, zurücknehmbarer Commit.

## 2. Technische Änderungen

### AP1 Installation und Betrieb (Details: `docs/installationstest.md`)

Echte Root-Installation mit systemd in LXD-Systemcontainern (Debian 12, Debian 13, Ubuntu 24.04, Ubuntu 26.04; Python 3.11.2 bis 3.14.4). Behobene Fehler:

- Installer v0.0.2 brach auf echten Systemen ab: Konfigurationsverzeichnis `root:root 0750`, Dienstbenutzer konnte die Umgebungsdatei nicht lesen (P1).
- Rollback nach Schemaänderung ließ den Dienst in einer Neustartschleife zurück (Alembic kennt Revision nicht). Jetzt Revisionsprüfung vor jeder Änderung und `lpic3ctl rollback --restore ARCHIV` (P1).
- `restore` unter Debian 12 abgebrochen (`TarFile.extract(filter=)` erst ab Python 3.11.4); Fallback mit eigener Prüfung (P1).
- Dienst im Zustand `activating` galt als inaktiv und wurde vor Restore nicht gestoppt (P1).
- Traceback ohne Root bei `status`/`check`/`install` (P2); Dateieigentümer nach Root-Befehlen (P2).
- Unit-Härtung: `systemd-analyze security` von 7.2 MEDIUM auf 1.3 bis 2.0 OK (P3); keine Ports unter 1024 mehr, Reverse Proxy zuständig.
- SPDX-Lizenzangabe in `pyproject.toml`; Alembic-Meldungen nur bei Migrationsbefehlen.

### AP2 LABs (Details: `docs/lab-konzept.md`, Abschnitt 2)

- `docs/lab-umgebung.md` und Seite `/labs/umgebung` (eigener Markdown-Renderer ohne Abhängigkeit, `app/markdown.py`).
- Schema v1 der LABs rückwärtskompatibel erweitert: `task_de`, `tools_de`, `success_criteria_de`, `pitfalls_de`, `instructor_notes_de`, `warning_de` je Schritt; alle zwölf LABs überarbeitet, Befehlsfolgen als eingeklappte Hilfestellung.
- Migration 0006: LAB-Status (`lab_progress.status`, `started_at`, `completed_at`), Tabelle `group_labs` (empfohlene LABs).
- Gruppenseite: LAB-Stände je Mitglied und je LAB, Empfehlungen; Dozentenhinweise nur für Betreuer/Administratoren; Link „Fragen zu diesem Prüfungsziel üben“.

### AP3 Fragen und Simulation (Details: `docs/zusatzfragen-bericht.md`, Abschnitt 6; `docs/stand.md`)

- Befund: richtige Antwort in 471 von 486 Dateien an erster Stelle, Oberfläche mischte nicht. Jetzt deterministische Mischung je Lernendem (`services.display_choices`), Frage- und Ergebnisseite gleich, Simulation je Prüfung.
- Mehrfachauswahl: Anzahl richtiger Antworten genannt, nur vollständige Auswahl zählt, Teilantworten erklärt. Keine künstlichen Umformulierungen.
- Neuer Fragetyp `text` (Lückentext), belegt durch LPI („60 multiple-choice and fill-in-the-blank questions“, LPIC-3-Übersichtsseiten, 5. November 2026): Liste akzeptierter Antworten, wörtlicher Vergleich nach Leerzeichen-Normalisierung, `case_sensitive` (Migration 0007), Auswertung in Üben und Simulation, vier Beispielfragen (eine je Modul).
- Fachliche Nachprüfung gegen Herstellerdokumentation: zwei Ergänzungsfragen zusätzlich deaktiviert (Samba-Papierkorb: Quelle 404; DFS mit smbclient: versionsabhängig), drei bestätigt mit Referenz-URL; die zwei ExamTopics-Fragen bleiben inaktiv. Aktiv: 482 von 486 Fragen.
- Gruppenauswertung je Prüfungsziel (`/admin/groups/<id>/auswertung`) aus Übungs-, Prüfungs- und Eingangstestdaten; nur eigene Gruppen.

### AP4 Pilotbetrieb (Details: `docs/pilotbetrieb.md`)

- Automatisierter Pilotlauf `tests/e2e/test_pilot.py` (Administrator, Dozent, Lernender, Smartphone), auch gegen eine bestehende Installation (`LPIC3_E2E_BASE`).
- Befund und Behebung: Betreuer konnten die mitgelieferten Zusatzpools nicht für ihre Gruppe freigeben (nur eigene Importe) und brauchten dafür den Administrator. Jetzt dürfen Betreuer eigene Importe und mitgelieferte Zusatzpools für eigene Gruppen freigeben; systemweit weiterhin nur Administratoren (Test ergänzt).
- Version 0.0.3.

## 3. Geänderte Lernfunktionen (Sicht der Nutzer)

- Lernende: LAB-Umgebung als eigener Lernbereich; LABs mit Aufgabe, Werkzeugen, Erfolgskriterien, Hilfestellung, typischen Fehlern; LAB-Status in drei Stufen; Link zu den Fragen des Prüfungsziels; gemischte Antwortreihenfolge; Lückentextfragen; Rückmeldung zu Teilantworten bei Mehrfachauswahl; Kennzeichnung empfohlener LABs.
- Dozenten: Dozentenhinweise je LAB, LAB-Stände und Empfehlungen je Gruppe, Auswertung je Prüfungsziel, Freigabe mitgelieferter Zusatzpools für eigene Gruppen.
- Administratoren: robustere Installation, `rollback --restore`, gehärtete Unit, verständliche Meldungen ohne Root.

## 4. Testergebnisse (5. November 2026)

| Suite | Ergebnis |
|---|---|
| pytest Backend (`tests/`, ohne e2e) | 115 bestanden (neu: `test_cli_permissions.py`, `test_labs.py`, `test_questions_ap3.py`, Rollback-Test, Migrationen 0006/0007, Freigabe mitgelieferter Pools durch Betreuer) |
| Playwright Chromium (`tests/e2e/`) | 19 bestanden (12 bestehende, angepasst an eingeklappte LAB-Hilfestellung, Statuswechsel, zwei Tabellen auf der Gruppenseite und Lückentextfragen; 7 Schritte Pilotlauf) |
| Pilotlauf gegen echte Installation | 7 bestanden gegen `lpic3-ubu26` (Ubuntu 26.04, systemd, Produktionsgrößen), Dienstjournal ohne Fehler |
| ruff check / format | ohne Befunde |

## 5. Tatsächlich ausgeführte Installationstests

Siehe `docs/installationstest.md`. Ausgeführt als Root mit systemd in LXD-Containern: Installation (v0.0.2 mit Workaround, korrigierter Stand ohne), Dienststart und Neustart des Containers, `status`/`check`/`version`/`logs`, Start/Stop/Restart, Passwort zurücksetzen, Bindeadresse und Port, Reverse Proxy mit HTTPS und Origin-Prüfung, fehlende Voraussetzungen, Upgrade v0.0.2 auf den neuen Stand mit Datenerhalt (Schema 0004 auf 0005 bzw. 0007), Backup im WAL-Betrieb, Restore mit und ohne laufenden Dienst, Restore-Verweigerung bei fremdem Server, Rollback ohne und mit Sicherung, fehlgeschlagenes Upgrade mit automatischem Rückfall, Deinstallation und erneute Installation. Nicht ausgeführt: blankes Metall oder VM mit eigenem Kernel, ARM64, Docker.

## 6. Offene Probleme und Einschränkungen

1. Keine Installation auf blankem Metall/VM und kein ARM64-Test; Docker Compose weiterhin ungetestet. Testplan in `docs/installationstest.md`, Abschnitt 5.
2. Die LABs wurden fachlich gegen Manpages und Herstellerdokumentation geprüft, aber nicht in einer Testumgebung ausgeführt. Versionsabhängige Punkte (DRBD 8.4 im Debian-12-Kernel gegenüber DRBD 9, OpenSSL 3, cgroup v2) stehen als typische Fehler in den LABs.
3. Vier Fragen inaktiv und prüfbedürftig (`300-examtopics-screenshot-08`, `305-examtopics-screenshot-03`, `300-erg-301.4-05`, `300-erg-303.3-02`). Die DRBD-Fencing-Frage ist nur über eine Seitenzusammenfassung bestätigt.
4. Lückentextfragen: nur vier Beispiele; weitere nur nach fachlicher Prüfung. Keine unscharfe Auswertung (beabsichtigt).
5. Keine reale Nutzerabnahme; der Pilotlauf ist automatisiert. Plan in `docs/pilotbetrieb.md`, Abschnitt 4.
6. Kein E-Mail-Versand (Startpasswörter persönlich übergeben), keine Fortsetzung einer unterbrochenen Simulation, Antworten ohne Verbindung gehen verloren (bekannte Einschränkungen aus `docs/stand.md`).
7. GitHub-Releases konnte der Entwicklungsagent nicht anlegen (Freigabefilter); Tag `v0.0.3` ist gesetzt, Release-Notizen liegen bereit.
8. Testinfrastruktur: Auf dem Entwicklungsrechner wurde LXD initialisiert (Storage-Pool `default`, Bridge `lxdbr0` 10.200.77.0/24) und fünf Container `lpic3-*` angelegt. Sie sind gestoppt und können mit `lxc delete lpic3-deb12 lpic3-deb13 lpic3-ubu24 lpic3-ubu26 lpic3-min` entfernt werden.

## 7. Empfehlungen für einen ersten Pilotbetrieb mit einer realen Lerngruppe

1. Version 0.0.3 auf einem eigenen Server oder einer VM nach `docs/installation.md` installieren, hinter HTTPS-Reverse-Proxy, mit täglichem `lpic3ctl backup`; vorher den Testplan aus `docs/installationstest.md`, Abschnitt 5, einmal durchspielen (deckt blankes Metall ab).
2. Pilotlauf `tests/e2e/test_pilot.py` einmal gegen die frische Installation laufen lassen, danach die Testkonten löschen oder die Datenbank aus der Sicherung vor dem Lauf wiederherstellen.
3. Eine Gruppe (ein Dozent, drei bis acht Lernende, ein Modul, zwei bis vier Wochen) nach `docs/pilotbetrieb.md`, Abschnitt 4, begleiten; Protokollbögen aus Abschnitt 4.4 verwenden.
4. Zusatzpools nur nach Entscheidung des Dozenten freigeben; ExamTopics-Pools wegen ungeklärter Rechte zurückhaltend.
5. Fachliche Einwände der Lernenden zu einzelnen Fragen über die Fragen-ID sammeln und in einer zweiten Expertenprüfung bearbeiten; die vier inaktiven Fragen dabei mitprüfen.
6. Nach dem Pilot entscheiden: LAB-Ausführung in einer realen Testumgebung durch den Dozenten, weitere Lückentextfragen, Firefox/WebKit-Browsertests, Docker-Test.
