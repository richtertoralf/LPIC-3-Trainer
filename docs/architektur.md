# Architektur

Technischer Aufbau des LPIC-3-Trainers und die wichtigsten Entscheidungen. Die verbindlichen Vorgaben stehen in [AGENTS.md](../AGENTS.md).

## Überblick

Der LPIC-3-Trainer ist eine monolithische Webanwendung in Python. Seiten werden serverseitig mit Jinja2 gerendert. JavaScript ergänzt nur dynamische Teile: Sprachhilfen, Prüfungstimer, Navigation auf dem Handy und den Service Worker.

```text
Browser ──HTTP──> Uvicorn ──> FastAPI (app/main.py)
                                 ├── Router (app/routers/)
                                 ├── Templates (app/templates/)
                                 ├── Lernlogik (app/services.py)
                                 ├── Import (app/content.py)
                                 └── SQLAlchemy ──> SQLite (WAL)
```

## Verzeichnisse

| Pfad | Inhalt |
|------|--------|
| `app/main.py` | Anwendungsfabrik, Middleware, Fehlerseiten, `/health` |
| `app/config.py` | Einstellungen aus `LPIC3_*`-Umgebungsvariablen |
| `app/db.py` | SQLite-Engine mit WAL, Sitzungen, kurze Transaktionen |
| `app/models.py` | ORM-Modelle |
| `app/security.py` | Argon2id-Hashing, serverseitige Sitzungen |
| `app/deps.py` | FastAPI-Abhängigkeiten: DB-Sitzung, aktueller Benutzer, Rollenprüfung |
| `app/services.py` | Sichtbarkeit von Fragen, Fortschritt, Fragenauswahl, Begriffserkennung |
| `app/content.py` | Validierung und Import der Inhaltsdateien |
| `app/migrate.py` | Programmatischer Alembic-Aufruf |
| `app/cli.py` | `lpic3ctl` |
| `app/routers/` | `auth`, `pages`, `learn`, `exam`, `vocab`, `labs`, `admin`, `api` |
| `app/templates/` | Jinja2-Templates, Layout in `base.html` |
| `app/static/` | `app.css`, `app.js`, `sw.js`, Manifest, Icons |
| `content/` | Lerninhalte als JSON, Format in `content/README.md` |
| `migrations/` | Alembic-Migrationen |
| `deploy/` | systemd-Unit, venv-Skript, Beispielkonfiguration, Dockerfile, Compose |
| `tests/` | pytest-Tests, `tests/e2e/` Playwright |

## Datenmodell

Gemeinsame Lerninhalte und persönliche Daten liegen in getrennten Tabellen.

Lerninhalte:

- `modules` → `topics` → `objectives`: Prüfungsziele mit Gewicht, deutscher Zusammenfassung und Werkzeugliste.
- `questions` → `choices`: englische Frage und Antworten, optional deutsche Übersetzung, deutsche Erklärung, Schwierigkeit, Sichtbarkeit (`public`/`private`), Ersteller, Importcharge.
- `terms`: Glossar Fachenglisch. `question_terms` verknüpft fragenbezogene Begriffe.
- `labs`: Laboraufgaben mit Lernziel, Aufgabenstellung (`task_de`), Werkzeugen (`tools_de`), Erfolgskriterien (`success_criteria_de`), Schritten als Hilfestellung (`steps`, JSON, optional `warning_de`), Selbstkontrollfragen (`checks`), typischen Fehlern (`pitfalls_de`) und Dozentenhinweisen (`instructor_notes_de`, nur Betreuer/Administratoren).
- `import_batches`: jede Importdatei mit Quelle (`source`), Prüfungsgeneration (`exam_version`), Rechtestatus (`rights`), Lizenz, Autor, Prüfsumme, Kennzeichnung als externe Quelle (`supplementary`) und systemweiter Freigabe (`released`).

Persönliche Daten:

- `users`, `sessions`, `app_settings`
- `groups`, `group_members` (Rolle `member`/`supervisor`, Status `active`/`pending`)
- `user_modules`: gewählte Module und Ergebnis des Eingangstests
- `attempts`: jede beantwortete Frage mit Modus (`practice`, `exam`, `entry`), Ergebnis und Kennzeichen „Sprachhilfe genutzt“
- `exams`: Prüfungssimulationen und Eingangstests mit Fragenliste und Antworten (JSON)
- `user_terms`: gemerkte Fachbegriffe (`learning`/`known`)
- `lab_progress`: LAB-Status je Lernendem (`status` started/completed, `started_at`, `completed_at`; keine Zeile = nicht begonnen)
- `group_labs`: von Betreuern für eine Gruppe empfohlene LABs
- `group_sources`: Importchargen, die ein Betreuer oder Administrator für eine Gruppe freigegeben hat

Alle Benutzerdaten tragen eine `user_id`. Beim Löschen eines Benutzers werden sie per `ON DELETE CASCADE` entfernt.

## Authentifizierung und Rechte

- Passwörter werden mit Argon2id gehasht (`argon2-cffi`).
- Sitzungen liegen in der Tabelle `sessions`. Das Cookie `lpic3_session` enthält nur die Sitzungs-ID und ist `HttpOnly`, `SameSite=Lax` und bei `LPIC3_SECURE_COOKIES=true` `Secure`.
- Zustandsändernde Anfragen werden zusätzlich über den `Origin`-Header gegen den `Host` geprüft (Schutz vor Cross-Site-Requests).
- Rollen: `admin`, `supervisor`, `learner`. Die Prüfung erfolgt im Backend über die Abhängigkeiten `require_admin` und `require_supervisor`.
- Das erste registrierte Konto wird Administrator.
- Sichtbarkeit von Fragen (`services.visible_questions`): Lernende sehen aktive Fragen mit `visibility = public` (mitgelieferter Grundbestand und systemweit freigegebene Importe) sowie Fragen aus Importchargen, die über `group_sources` für eine ihrer aktiven Gruppen freigegeben sind. Importierende sehen ihre eigenen Importe, Administratoren alles. `questions.visibility` wird bei Import und Freigabe aus `import_batches.released` abgeleitet.
- Import und Freigabe: nur Administratoren und Betreuer importieren (`require_supervisor`). Jeder Import ist eine externe Charge (`supplementary`), bleibt unveröffentlicht und braucht Quelle und Prüfungsgeneration. Betreuer geben eigene Chargen für eigene Gruppen frei, Administratoren systemweit (`set_batch_release`) oder für beliebige Gruppen.

## Lernlogik

- Übungsmodus (`/learn/{modul}`): Es wird bevorzugt eine noch nie beantwortete Frage gezeigt, danach zuletzt falsch beantwortete, sonst zufällig. Optional auf ein Prüfungsziel eingegrenzt.
- Sprachhilfe: Übersetzung ein- und ausblendbar, Fachbegriffe werden im Browser markiert. Beides setzt das Formularfeld `used_help`, das mit der Antwort gespeichert wird. Die Bewertung ist davon unabhängig.
- Fachbegriffe einer Frage: explizit verknüpfte Begriffe plus alle Glossarbegriffe, die wörtlich im Fragetext oder in den Antworten vorkommen (`services.terms_for_question`).
- Prüfungssimulation (`/exam/{modul}/start`): Fragen werden zufällig und nach Themengewicht verteilt gezogen, keine Sprachhilfen, Timer im Browser, Abgabe serverseitig bewertet. Mehrfachauswahl zählt nur bei vollständig richtiger Auswahl.
- Kapiteltest: `?topic=` begrenzt auf ein Thema mit weniger Fragen.
- Eingangstest (`/entry/{modul}/start`): kurzer Test ohne Timer, Ergebnis je Thema wird am Modul gespeichert und zeigt „sicher“ oder „üben“.
- Fortschritt: letzter Versuch je Frage zählt, dazu Hilfequote, Labs und beste Simulation. Keine weitergehende Lernanalyse.

## Inhalte und Import

- Format: JSON mit `schema_version` und `kind` (`objectives`, `terms`, `questions`, `labs`). Beschreibung in `content/README.md`.
- Jede Datei wird vollständig validiert, bevor etwas geschrieben wird. Fehlerhafte Dateien werden mit allen Fehlern abgelehnt.
- Importierte Texte werden ausschließlich als Daten behandelt und beim Rendern durch Jinja2 escaped. Zeilenumbrüche in Erklärungen werden über den Filter `nl2p` in Absätze umgesetzt, ebenfalls escaped.
- Mitgelieferte Projektfragen tragen `source`, `exam_version` und `rights: cleared` und werden als freigegebener Grundbestand importiert. Externe Quellen unter `content/questions/extra/` (`supplementary: true`) werden mitimportiert, bleiben aber unveröffentlicht (Migrationen `0002`, `0003`).
- Mitgelieferte Inhalte werden bei `install`, `upgrade` und `serve` synchronisiert. Eine Prüfsumme je Datei verhindert unnötige Wiederholungen. Erneuter Import aktualisiert Fragen anhand ihrer `id`, Lernstände bleiben erhalten.

## Offline-Verhalten

- `sw.js` wird unter `/sw.js` ausgeliefert. Statische Dateien werden cache-first bedient, Seiten network-first mit Cache als Rückfall. Unbekannte Seiten zeigen `/offline`.
- `POST`-Anfragen, `/api/`, `/admin` und `/health` werden nicht gecacht.
- Ohne Verbindung zeigt ein Banner, dass Lernfortschritt nicht gespeichert wird. Es gibt keine Hintergrund-Synchronisierung.

## Konfiguration

Alle Einstellungen kommen aus Umgebungsvariablen mit Präfix `LPIC3_` (siehe `docs/installation.md`). `lpic3ctl` lädt zusätzlich `/etc/lpic3-trainer/lpic3-trainer.env`, ohne vorhandene Variablen zu überschreiben.

## Entscheidungen

- **Serverseitiges Rendering statt Frontend-Framework**: einfacher, wartbar, funktioniert ohne Build-Pipeline.
- **SQLite mit WAL**: ein Prozess, kurze Schreibtransaktionen, `busy_timeout` 15 s. Zustandsändernde Anfragen (POST) und `session_scope` beginnen mit `BEGIN IMMEDIATE`, damit gleichzeitige Schreiber am Busy-Timeout warten, statt beim Aufstufen einer gelesenen Transaktion sofort mit „database is locked“ zu scheitern; die Antwortauswertung gibt die Schreibsperre vor dem Rendern frei. Für Lerngruppen ausreichend. Backups über die SQLite-Backup-API.
- **Editierbare Installation** (`pip install -e`): Programmdateien bleiben unter `/opt/lpic3-trainer/app`, dadurch findet die Anwendung `content/`, `migrations/` und `alembic.ini`.
- **Sprachhilfe im Browser**: Markierung und Übersetzung passieren im Browser aus mitgelieferten Daten. Es gibt keine externe Übersetzung und keine KI.
- **Keine Lernanalyse**: nur Zähler je Ziel, Hilfequote und Ergebnisse.
