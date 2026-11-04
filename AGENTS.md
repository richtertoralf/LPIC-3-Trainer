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
