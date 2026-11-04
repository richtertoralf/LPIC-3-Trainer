# AGENTS.md

## Projektgrundlage

- Projektziel, Zielgruppe und Funktionsumfang: [README.md](README.md)
- Die README ist die fachliche Referenz.
- Hier stehen ausschließlich technische Vorgaben und Entwicklungsregeln.

## Leitprinzipien

- Oberste Priorität: Einfachheit, digitale Souveränität und langfristige Wartbarkeit.
- Die Anwendung läuft vollständig auf eigener Infrastruktur.
- Keine Cloud-Dienste, keine externen APIs, keine proprietären Dienste.
- Ein einfaches, wartbares System hat Vorrang vor technischer Erweiterbarkeit.
- Keine unnötigen Dienste, Abhängigkeiten oder Entwicklungswerkzeuge.

## Sprache

- Dokumentation, Benutzeroberfläche, Lerninhalte und Kommunikation: Deutsch.
- Programmcode, Kommentare, technische Bezeichner und Commit-Nachrichten: Englisch.

## Zielsystem

- Betriebssystem: Linux
- Unterstützt: Ubuntu 24.04/26.04 LTS, Debian 12/13
- Architektur: x86_64 und ARM64
- Clients: Browser auf Linux, Windows und Android
- Bereitstellung: eigener Linux-Server oder lokale Installation
- Containerbetrieb: optional mit Docker Compose

## Technischer Stack

- Python ab 3.11 (Systempython von Debian 12 ist die Untergrenze)
- Backend: FastAPI, Uvicorn
- Templates: Jinja2, serverseitig gerendertes HTML
- Frontend: HTML5, CSS3, natives JavaScript
- Datenbank: SQLite mit WAL-Modus
- Datenbankzugriff: SQLAlchemy
- Migrationen: Alembic
- Passwort-Hashing: Argon2id
- PWA: Web App Manifest und Service Worker
- Abhängigkeiten und Metadaten: `pyproject.toml`
- Tests: pytest und Playwright
- Lint und Formatierung: ruff
- Keine Frontend-Frameworks, keine Build-Pipeline für das Frontend.
- Keine zusätzlichen Datenbanksysteme, keine Cache- oder Message-Server.

## Architektur

- Monolithische Webanwendung.
- Klare Trennung von Backend, Frontend und Lerninhalten.
- Seiten werden serverseitig gerendert. JSON-Endpunkte nur für dynamische Teile, zum Beispiel Lernfortschritt und Prüfungssimulation.
- Keine Microservices.
- Keine externe KI-Anbindung.
- Keine unnötigen Frameworks oder Abstraktionen.

## Repository-Struktur

```text
app/              # FastAPI-Anwendung (Python-Paket)
  templates/      # Jinja2-Templates
  static/         # CSS, JavaScript, Manifest, Service Worker
content/          # Lerninhalte: Fragen, Fachenglisch, Lab-Anleitungen
migrations/       # Alembic-Migrationen
tests/            # pytest-Tests
  e2e/            # Playwright-Browsertests
deploy/           # lpic3ctl, systemd-Unit, Docker Compose
pyproject.toml
README.md
AGENTS.md
CLAUDE.md
```

- Neue Verzeichnisse nur bei nachgewiesenem Bedarf.
- Lerninhalte liegen als Dateien unter `content/` und werden beim Import in die Datenbank übernommen.

## Offline-Verhalten

- Die App funktioniert auch ohne Verbindung zum Server.
- Der Service Worker hält statische Dateien und bereits aufgerufene Lerninhalte im Browser vor.
- Lernfortschritt wird nur bei bestehender Verbindung gespeichert.
- Keine verpflichtende Offline-Synchronisierung und keine Hintergrund-Synchronisierung.
- Konflikte zwischen Offline- und Serverstand werden nicht automatisch aufgelöst.

## Mehrbenutzerbetrieb

- Rollen: Administrator, Betreuer, Lernender.
- Rollenbasierte Rechteprüfung im Backend.
- Benutzerbezogene Daten durch Benutzer-IDs trennen.
- Lerngruppen über eigene Zuordnungstabellen abbilden.
- Anmeldung und Gruppenzugang konfigurierbar: offen oder mit Freigabe.
- Passwörter mit Argon2id hashen.
- Serverseitige Sitzungen in der Datenbank. Das Cookie enthält nur die Sitzungs-ID und ist HttpOnly, SameSite und bei HTTPS Secure.
- Keine unberechtigten Zugriffe auf fremde Lernstände.

## Datenhaltung

- SQLite mit WAL-Modus und kurzen Schreibtransaktionen.
- Datenbankzugriff über SQLAlchemy, keine datenbankspezifischen Erweiterungen.
- Gemeinsame Lerninhalte und persönliche Daten in getrennten Tabellen halten.
- Schemaänderungen ausschließlich über Alembic-Migrationen.
- Backups über die SQLite-Backup-API oder `VACUUM INTO`, kein einfaches Kopieren der Datenbankdatei im WAL-Betrieb.
- Keine Datenbankdateien im Git-Repository.

## Fragenimport

- Importformat: JSON mit dokumentiertem, versioniertem Schema.
- Jede Importdatei wird vor der Übernahme vollständig validiert. Fehlerhafte Dateien werden abgelehnt.
- Importierte Inhalte werden als Daten behandelt und nie ausgeführt oder ungeprüft als HTML gerendert.
- Import und Validierung sind automatisiert zu testen.

## Lab-Aufgaben

- Die App liefert Anleitungen und Selbstkontrollfragen.
- Keine automatische Ausführung von Lab-Aufgaben.
- Keine administrative Shell-Ausführung über den Browser.
- Lab-Aufgaben nur in separaten Testumgebungen der Lernenden.
- Keine Änderungen an produktiven Linux-Systemen.

## Konfiguration

- Konfiguration über Umgebungsvariablen mit Präfix `LPIC3_`.
- Beispielkonfiguration als `.env.example` im Repository, ohne Zugangsdaten.
- Standardbindung `127.0.0.1:8000`. Öffentliche Bereitstellung nur hinter einem Reverse Proxy mit HTTPS.
- Keine Zugangsdaten im Repository.

## Entwicklung

- Bestehenden Code vor Änderungen prüfen.
- Änderungen klein und nachvollziehbar halten.
- Bestehende Funktionen wiederverwenden.
- Keine unnötigen Refactorings.
- Abhängigkeiten begrenzen und begründen.
- Versionierung nach SemVer. Releases über Git-Tags im Format `vX.Y.Z`.

## Sicherheit

- Rechte und Datentrennung serverseitig durchsetzen.
- Keine ungeprüfte Ausführung oder Darstellung importierter Inhalte.
- Öffentliche Bereitstellung nur mit HTTPS.
- Keine Passwörter oder Sitzungsgeheimnisse protokollieren.

## Qualität

- Rollen und Zugriffsrechte automatisiert testen.
- Gleichzeitige Zugriffe mehrerer Nutzer testen.
- Datenmigrationen und Backups testen.
- Importfunktionen und Datenintegrität testen.
- Desktop- und Android-Browser prüfen.
- Dokumentation aktuell halten.

## Automatisierte Browsertests

- Playwright ist für End-to-End-Tests verpflichtend.
- Playwright gehört ausschließlich zur Entwicklungs- und Testumgebung.
- Die produktive Installation benötigt weder Playwright noch Browser-Testpakete.
- Tests müssen lokal und ohne externe Dienste ausführbar sein.
- Chromium ist der primäre Testbrowser.
- Zentrale Benutzerabläufe vollständig über die Browseroberfläche testen.
- Getestet werden Registrierung, Anmeldung, Rollen, Lernfortschritt, Prüfungen und Fragenimport.
- Darstellung auch mit mobilen Bildschirmgrößen prüfen.
- JavaScript-Fehler und fehlgeschlagene Netzwerkanfragen erfassen.
- Bei Fehlern Screenshots und nachvollziehbare Testberichte erstellen.
- Das vorgesehene Offline-Verhalten testen.
- Reproduzierbare Testdaten und eine getrennte Testdatenbank verwenden.
- Entwicklungsagenten führen nach relevanten Änderungen selbstständig die betroffenen Browsertests aus.
- Vor Abschluss eines größeren Arbeitspakets muss die vollständige Testsuite erfolgreich durchlaufen.
- Playwright dient der eigenständigen Qualitätskontrolle durch Entwicklungsagenten und erzeugt keine Abhängigkeit für den produktiven Betrieb.

## Installation, Betrieb und Administration

- Einheitliches CLI-Werkzeug `lpic3ctl` bereitstellen.
- `lpic3ctl` ist ein Python-Modul der Anwendung. Nur das Anlegen des venv bei `install` erfolgt über ein kleines Shellskript unter `deploy/`.
- Installation und Administration ohne manuelle Quellcodeänderungen.
- Native Installation mit venv und systemd-Dienst.
- Standardinstallation unter `/opt/lpic3-trainer`.
- Konfiguration unter `/etc/lpic3-trainer`.
- Persistente Daten unter `/var/lib/lpic3-trainer`.
- Logs über journald.
- Installations- und Upgradeverfahren müssen wiederholbar sein.
- Docker-Compose-Betrieb und native Installation verwenden dieselben persistenten Datenstrukturen.

### CLI-Befehle

| Befehl               | Funktion                                        |
|----------------------|-------------------------------------------------|
| `lpic3ctl install`   | Anwendung installieren                          |
| `lpic3ctl upgrade`   | Anwendung aktualisieren                         |
| `lpic3ctl version`   | Installierte und verfügbare Version anzeigen    |
| `lpic3ctl status`    | Dienststatus und Systemzustand anzeigen         |
| `lpic3ctl start`     | Dienst starten                                  |
| `lpic3ctl stop`      | Dienst stoppen                                  |
| `lpic3ctl restart`   | Dienst neu starten                              |
| `lpic3ctl logs`      | Dienstprotokolle anzeigen                       |
| `lpic3ctl backup`    | Daten und Konfiguration sichern                 |
| `lpic3ctl restore`   | Datensicherung wiederherstellen                 |
| `lpic3ctl check`     | Installation und Konfiguration prüfen           |
| `lpic3ctl uninstall` | Anwendung entfernen, Benutzerdaten erhalten     |
| `lpic3ctl purge`     | Anwendung einschließlich aller Daten entfernen  |

### Installationsregeln

- Abhängigkeiten automatisch prüfen.
- Fehlende Voraussetzungen verständlich melden.
- Eigenen Systembenutzer ohne Login-Shell verwenden.
- Dateirechte und Verzeichnisse sicher anlegen.
- Keine unnötigen Root-Rechte für den laufenden Dienst.
- Bestehende Installationen erkennen.
- Konfiguration bei erneuter Installation erhalten.
- Keine vorhandenen Dienste oder Ports ungefragt überschreiben.

### Upgrade-Regeln

- Installierte Version vor dem Upgrade prüfen.
- Datenbank und Konfiguration vorher sichern.
- Datenbankmigrationen automatisch ausführen.
- Benutzerdaten, Fragen und Lernstände erhalten.
- Fehler beim Upgrade erkennen und verständlich melden.
- Wiederherstellung der vorherigen Version vorsehen.
- Keine ungeprüfte Überschreibung lokaler Konfiguration.
- Versionsinformationen aus Git-Tags beziehungsweise Releases ableiten.

### Deinstallation

- `uninstall` entfernt Dienst und Programmdateien. Konfiguration und Benutzerdaten bleiben erhalten.
- `purge` entfernt zusätzlich Konfiguration und gespeicherte Daten.
- Vor `purge` ausdrückliche Bestätigung verlangen.
- Nichtinteraktive Löschung nur mit expliziter Freigabeoption.
- Keine fremden Verzeichnisse oder gemeinsam genutzten Dienste löschen.

### Betrieb und Diagnose

- Health-Endpunkt für die Anwendung bereitstellen.
- Datenbankstatus und Schema-Version prüfen.
- Fehler über strukturierte Logs nachvollziehbar machen.
- CLI-Befehle mit sinnvollen Exit-Codes versehen.
- Administrative Befehle mit `--help` dokumentieren.
- Installations-, Upgrade- und Deinstallationsabläufe automatisiert testen.

## Abschluss

- Änderungen und Testergebnisse dokumentieren.
- Offene Punkte und Einschränkungen benennen.
- Keine ungetesteten Funktionen als fertig melden.
