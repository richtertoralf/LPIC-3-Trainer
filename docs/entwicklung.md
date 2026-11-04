# Entwicklung

## Umgebung

```bash
git clone https://github.com/richtertoralf/LPIC-3-Trainer.git
cd LPIC-3-Trainer
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/playwright install chromium
```

Anwendung starten (Datenbank unter `./data`, Migrationen und Inhalte werden beim Start übernommen):

```bash
LPIC3_DATA_DIR=./data .venv/bin/lpic3ctl serve
```

Alternativ mit Autoreload: `LPIC3_DATA_DIR=./data .venv/bin/uvicorn app.main:app --reload` (ohne Inhaltsimport; vorher einmal `lpic3ctl content-sync`).

Beispielkonfiguration: `.env.example`.

## Tests

```bash
.venv/bin/pytest                       # pytest ohne Browsertests (tests/e2e wird mitgesammelt, siehe unten)
.venv/bin/pytest tests --ignore=tests/e2e
.venv/bin/pytest tests/e2e --browser chromium --screenshot only-on-failure --output test-results
.venv/bin/ruff check app tests migrations
.venv/bin/ruff format --check app tests migrations
```

- Backendtests nutzen eine eigene Datenbank in einem temporären Verzeichnis (`tests/conftest.py`). Der Test-Client lädt die mitgelieferten Inhalte einmal pro Sitzung.
- `tests/test_cli_ops.py` ruft `lpic3ctl` als Unterprozess auf (Migration, Benutzer, Backup, Restore, Check).
- `tests/test_cli_install.py` prüft `install`, `upgrade`, `rollback`, `uninstall` und `purge` in einem temporären Verzeichnisbaum. Root und systemd werden durch `LPIC3_UNPRIVILEGED_TEST=1` sowie Stub-Befehle für `useradd`, `userdel` und `systemctl` ersetzt. Der Test erzeugt ein echtes venv und dauert etwa eine Minute.
- `tests/test_concurrency.py` lässt acht Benutzer parallel antworten.
- Browsertests (`tests/e2e/`) starten einen Uvicorn-Server mit eigener Datenbank, verkleinerten Prüfungsgrößen und prüfen Registrierung, Anmeldung, Rollen, Üben mit Sprachhilfe, Simulation, Eingangstest, Labs, Import, Gruppen, mobile Darstellung (390 px) und Offline-Verhalten. JavaScript-Fehler und fehlgeschlagene Anfragen lassen Tests fehlschlagen. Screenshots fehlgeschlagener Tests landen unter `test-results/`.

## Inhalte

- Format: `content/README.md`. Prüfen mit `lpic3ctl validate datei.json`.
- Mitgelieferte Inhalte stehen unter CC BY-SA 4.0 (`content/LICENSE.md`). Prüfungsfragen selbst formulieren, keine kopierten Exam-Dumps.
- Deutsche Zusammenfassungen der Prüfungsziele sind eigene Formulierungen. Quelle der Titel und Gewichte: LPI-Prüfungsziele (URL in der jeweiligen Datei).
- Bei Änderungen an mitgelieferten Dateien erkennt `content-sync` die Änderung über eine Prüfsumme und aktualisiert Fragen anhand ihrer `id`.

## Datenbank

- Schemaänderungen nur über Alembic:

```bash
LPIC3_DATA_DIR=./data .venv/bin/alembic revision --autogenerate -m "describe change"
LPIC3_DATA_DIR=./data .venv/bin/alembic upgrade head
```

- Migrationen in `migrations/versions/` mit sprechender Revision benennen. Vorhanden: `0001_initial_schema`, `0002_supplementary_questions`. SQLite-Änderungen an Spalten brauchen `batch_alter_table` (in `env.py` aktiviert).
- Die Anwendung führt beim Start `upgrade head` aus.

## Code

- Python ab 3.11, Formatierung und Lint mit ruff (Zeilenlänge 100).
- Programmcode, Kommentare, Bezeichner und Commits auf Englisch. Oberfläche und Dokumentation auf Deutsch.
- Router unter `app/routers/`, gemeinsame Logik in `app/services.py`. Templates erben von `base.html`. Fragen werden über `learn/_question_body.html` gerendert, Sprachhilfe über `learn/_help_panel.html`.
- JavaScript liegt in `app/static/app.js` ohne Framework. Der Service Worker `sw.js` hat eine Versionskonstante `VERSION`; bei Änderungen an statischen Dateien hochzählen.

## Release

1. Version in `pyproject.toml` und `app/__init__.py` erhöhen.
2. `docs/stand.md` aktualisieren.
3. Commit, Tag `vX.Y.Z`, Push, GitHub-Release mit deutschen Release Notes.
