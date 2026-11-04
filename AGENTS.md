# AGENTS.md

## Projektgrundlage

- Ziel und Funktionsumfang: [README.md](README.md)
- Die README ist die fachliche Referenz.

## Zielsystem

- Betriebssystem: Linux
- Unterstützt: Ubuntu 24.04/26.04 LTS, Debian 12/13
- Architektur: x86_64 und ARM64
- Nutzung: Browser auf Linux, Windows und Android
- Bereitstellung: lokal oder auf eigenem Server
- Containerbetrieb: optional mit Docker Compose

## Technischer Stack

- Backend: Python 3.12+, FastAPI
- Frontend: HTML5, CSS3, natives JavaScript
- Datenbank: SQLite
- Webserver: Uvicorn
- PWA: Service Worker und Web App Manifest
- Tests: pytest, Browser-End-to-End-Tests

## Datenhaltung

- SQLite für Fragen, Lernstände und Einstellungen.
- Kein separater Datenbankserver erforderlich.
- Lerninhalte und Benutzerdaten getrennt speichern.
- Datenbankmigrationen vorsehen.
- Backup und Wiederherstellung ermöglichen.
- Keine Datenbankdateien im Git-Repository.

## Architektur

- Monolithische Webanwendung.
- Klare Trennung von Backend, Frontend und Inhalten.
- REST-API nur für tatsächlich benötigte Funktionen.
- Keine Microservices.
- Keine verpflichtenden Cloud-Dienste.
- Keine externe KI-Anbindung.
- Keine unnötigen Frameworks oder Abstraktionen.

## Entwicklung

- Bestehenden Code vor Änderungen prüfen.
- Änderungen klein und nachvollziehbar halten.
- Keine parallelen Implementierungen derselben Funktion.
- Keine unnötigen Refactorings.
- Abhängigkeiten auf das Notwendige begrenzen.
- Konfiguration über Umgebungsvariablen.
- Keine Zugangsdaten im Repository.

## Sicherheit und Abgrenzung

- Keine administrative Shell-Ausführung über die Weboberfläche.
- Keine ungeprüfte Ausführung importierter Inhalte.
- Keine Änderungen an produktiven Linux-Systemen.
- Lab-Aufgaben werden in einer separaten Testumgebung ausgeführt.
- Keine öffentliche Bereitstellung ohne Zugriffsschutz.

## Qualität

- Automatisierte Tests für zentrale Funktionen.
- Import, Lernfortschritt und Datenmigrationen testen.
- Browserdarstellung auf Desktop und Android prüfen.
- Fehler vor Abschluss beheben.
- Dokumentation bei technischen Änderungen aktualisieren.

## Abschluss

- Änderungen und Testergebnisse dokumentieren.
- Offene Punkte und Einschränkungen benennen.
- Keine ungetesteten Funktionen als fertig melden.
