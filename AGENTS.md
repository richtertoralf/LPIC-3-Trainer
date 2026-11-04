# AGENTS.md

## Projektgrundlage

- Projektziel und Funktionsumfang: [README.md](README.md)
- Die README ist die fachliche Referenz.
- Hier stehen ausschließlich technische Vorgaben und Entwicklungsregeln.

## Zielsystem

- Betriebssystem: Linux
- Unterstützt: Ubuntu 24.04/26.04 LTS, Debian 12/13
- Architektur: x86_64 und ARM64
- Clients: Browser auf Linux, Windows und Android
- Bereitstellung: eigener Linux-Server oder lokale Installation
- Containerbetrieb: optional mit Docker Compose

## Technischer Stack

- Backend: Python 3.12+, FastAPI
- Frontend: HTML5, CSS3, natives JavaScript
- Datenbank: SQLite mit WAL-Modus
- Datenbankzugriff: SQLAlchemy
- Migrationen: Alembic
- Webserver: Uvicorn
- PWA: Service Worker und Web App Manifest
- Tests: pytest und Browser-End-to-End-Tests

## Architektur

- Monolithische Webanwendung.
- Klare Trennung von Backend, Frontend und Lerninhalten.
- REST-API nur bei Bedarf.
- Keine Microservices.
- Keine verpflichtenden Cloud-Dienste.
- Keine externe KI-Anbindung.
- Keine unnötigen Frameworks oder Abstraktionen.

## Mehrbenutzerbetrieb

- Rollen: Administrator, Betreuer, Lernender.
- Rollenbasierte Rechteprüfung im Backend.
- Benutzerbezogene Daten durch Benutzer-IDs trennen.
- Lerngruppen über eigene Zuordnungstabellen abbilden.
- Anmeldung und Gruppenzugang konfigurierbar gestalten.
- Passwörter sicher hashen.
- Sitzungen sicher verwalten.
- Keine unberechtigten Zugriffe auf fremde Lernstände.

## Datenhaltung

- SQLite mit WAL-Modus und kurzen Schreibtransaktionen.
- Datenbankzugriff für späteren PostgreSQL-Wechsel vorbereiten.
- Gemeinsame Lerninhalte und persönliche Daten getrennt halten.
- Datenbankmigrationen vorsehen.
- Backup und Wiederherstellung ermöglichen.
- Keine Datenbankdateien im Git-Repository.

## Entwicklung

- Bestehenden Code vor Änderungen prüfen.
- Änderungen klein und nachvollziehbar halten.
- Bestehende Funktionen wiederverwenden.
- Keine unnötigen Refactorings.
- Abhängigkeiten begrenzen.
- Konfiguration über Umgebungsvariablen.
- Keine Zugangsdaten im Repository.

## Sicherheit und Abgrenzung

- Keine administrative Shell-Ausführung über den Browser.
- Keine ungeprüfte Ausführung importierter Inhalte.
- Lab-Aufgaben nur in separaten Testumgebungen.
- Keine Änderungen an produktiven Linux-Systemen.
- Öffentliche Bereitstellung nur mit HTTPS.
- Rechte und Datentrennung serverseitig durchsetzen.

## Qualität

- Rollen und Zugriffsrechte automatisiert testen.
- Gleichzeitige Zugriffe mehrerer Nutzer testen.
- Datenmigrationen und Backups testen.
- Importfunktionen und Datenintegrität testen.
- Desktop- und Android-Browser prüfen.
- Dokumentation aktuell halten.

## Abschluss

- Änderungen und Testergebnisse dokumentieren.
- Offene Punkte und Einschränkungen benennen.
- Keine ungetesteten Funktionen als fertig melden.

Installation, Betrieb und Administration

Einheitliches CLI-Werkzeug lpic3ctl bereitstellen.

Installation und Administration ohne manuelle Quellcodeänderungen ermöglichen.

Systemd-Dienst für den regulären Linux-Betrieb bereitstellen.

Standardinstallation unter /opt/lpic3-trainer.

Konfiguration unter /etc/lpic3-trainer.

Persistente Daten unter /var/lib/lpic3-trainer.

Logs über journald.

Installations- und Upgradeverfahren müssen wiederholbar sein.

CLI-Befehle

Befehl

Funktion

lpic3ctl install

Anwendung installieren

lpic3ctl upgrade

Anwendung aktualisieren

lpic3ctl version

Installierte und verfügbare Version anzeigen

lpic3ctl status

Dienststatus und Systemzustand anzeigen

lpic3ctl start

Dienst starten

lpic3ctl stop

Dienst stoppen

lpic3ctl restart

Dienst neu starten

lpic3ctl logs

Dienstprotokolle anzeigen

lpic3ctl backup

Daten und Konfiguration sichern

lpic3ctl restore

Datensicherung wiederherstellen

lpic3ctl check

Installation und Konfiguration prüfen

lpic3ctl uninstall

Anwendung entfernen, Benutzerdaten erhalten

lpic3ctl purge

Anwendung einschließlich aller Daten entfernen

Installationsregeln

Abhängigkeiten automatisch prüfen.

Fehlende Voraussetzungen verständlich melden.

Eigenen Systembenutzer ohne Login-Shell verwenden.

Dateirechte und Verzeichnisse sicher anlegen.

Keine unnötigen Root-Rechte für den laufenden Dienst.

Bestehende Installationen erkennen.

Konfiguration bei erneuter Installation erhalten.

Keine vorhandenen Dienste oder Ports ungefragt überschreiben.

Upgrade-Regeln

Installierte Version vor dem Upgrade prüfen.

Datenbank und Konfiguration vorher sichern.

Datenbankmigrationen automatisch ausführen.

Benutzerdaten, Fragen und Lernstände erhalten.

Fehler beim Upgrade erkennen und verständlich melden.

Wiederherstellung der vorherigen Version vorsehen.

Keine ungeprüfte Überschreibung lokaler Konfiguration.

Versionsinformationen aus Git-Tags beziehungsweise Releases ableiten.

Deinstallation

uninstall entfernt Dienst und Programmdateien.

Konfiguration und Benutzerdaten bleiben erhalten.

purge entfernt zusätzlich Konfiguration und gespeicherte Daten.

Vor purge ausdrückliche Bestätigung verlangen.

Nichtinteraktive Löschung nur mit expliziter Freigabeoption.

Keine fremden Verzeichnisse oder gemeinsam genutzten Dienste löschen.

Betrieb und Diagnose

Health-Endpunkt für die Anwendung bereitstellen.

Datenbankstatus und Schema-Version prüfen.

Fehler über strukturierte Logs nachvollziehbar machen.

Keine Passwörter oder Sitzungsgeheimnisse protokollieren.

CLI-Befehle mit sinnvollen Exit-Codes versehen.

Administrative Befehle mit --help dokumentieren.

Installations-, Upgrade- und Deinstallationsabläufe automatisiert testen.

Docker-Compose-Betrieb und native Installation müssen dieselben persistenten Datenstrukturen verwenden.
