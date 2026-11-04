# Lerninhalte

Dieses Verzeichnis enthält die mitgelieferten Lerninhalte als JSON-Dateien. Sie werden mit `lpic3ctl content-sync` (automatisch bei `install`, `upgrade` und `serve`) in die Datenbank übernommen.

Die Inhalte stehen unter CC BY-SA 4.0, siehe [LICENSE.md](LICENSE.md). Der Programmcode der Anwendung ist davon getrennt unter MIT lizenziert.

## Verzeichnisse

| Verzeichnis   | Inhalt                                       | kind         |
|---------------|----------------------------------------------|--------------|
| `objectives/` | Prüfungsziele je Modul (Themen, Ziele, Gewicht) | `objectives` |
| `vocabulary/` | Glossar Fachenglisch (Begriff, Übersetzung, Erklärung) | `terms` |
| `questions/`  | Prüfungsfragen je Modul                      | `questions`  |
| `questions/extra/` | Zusatzfragen aus gesondert gekennzeichneten Quellen, siehe [questions/extra/README.md](questions/extra/README.md) | `questions` mit `supplementary: true` |
| `labs/`       | Laboraufgaben je Modul                       | `labs`       |

Die Importreihenfolge ist fest: Prüfungsziele, Glossar, Fragen, Zusatzfragen, Labs.

## Schema Version 1

Alle Dateien haben denselben Rahmen:

```json
{"schema_version": 1, "kind": "questions", ...}
```

Jede Datei wird vor dem Import vollständig geprüft. Bei einem Fehler wird nichts übernommen. Texte werden immer als Daten behandelt und beim Anzeigen HTML-escaped.

### Fragen (`kind: questions`)

```json
{
  "schema_version": 1,
  "kind": "questions",
  "module": "303",
  "source": "LPIC-3 Trainer Projekt",
  "source_url": "https://github.com/richtertoralf/LPIC-3-Trainer",
  "exam_code": "303-300",
  "exam_version": "3.0",
  "rights": "cleared",
  "license": "CC BY-SA 4.0",
  "author": "Name",
  "questions": [
    {
      "id": "303-331.1-01",
      "objective": "331.1",
      "type": "single",
      "difficulty": 2,
      "question": "English question text",
      "question_de": "Deutsche Übersetzung (optional)",
      "choices": [
        {"text": "English choice", "text_de": "Deutsche Übersetzung", "correct": true},
        {"text": "...", "correct": false}
      ],
      "explanation_de": "Deutsche Erklärung der richtigen Antwort",
      "explanation_en": "Optional English explanation",
      "terms": [{"term": "revoke", "de": "widerrufen", "explanation_de": "optional"}]
    }
  ]
}
```

Regeln:

- `module`: dreistelliger Modulcode. Das Modul muss durch eine Objectives-Datei bekannt sein.
- `id`: eindeutig, 2 bis 64 Zeichen aus Buchstaben, Ziffern, Punkt, Minus, Unterstrich. Beim erneuten Import wird eine Frage mit gleicher `id` aktualisiert; Lernstände bleiben erhalten.
- `objective`: optional, Format `301.1`. Muss existieren.
- `type`: `single` (genau eine richtige Antwort) oder `multiple` (mindestens zwei richtige und mindestens eine falsche).
- `difficulty`: 1 bis 3, Standard 2.
- `choices`: 2 bis 6 Einträge.
- `source` (Pflicht): nachvollziehbare Quelle der Fragen, max. 160 Zeichen. Wird bei importierten Fragen angezeigt.
- `exam_version` (Pflicht): Prüfungsgeneration, auf die sich die Fragen beziehen, z. B. `3.0`.
- `exam_code`: vollständige Prüfungsnummer, z. B. `305-300`; muss mit der Modulnummer beginnen. Ohne Angabe wird Modulnummer-300 gesetzt.
- `source_url`: Original-URL der Quelle (http/https, optional).
- je Frage `active`: `false` nimmt die Frage aus Üben und Prüfungen heraus (z. B. unsichere Lösung); das Kennzeichen bleibt bei erneutem Import erhalten.
- `rights`: `cleared` (Lizenz bekannt), `unknown` (Standard) oder `unverified` (Herkunft bekannt, Nutzungsrechte nicht geklärt).
- `terms`: fragenbezogene Fachbegriffe. Sie landen zusätzlich im Glossar.
- `supplementary`: nur für mitgelieferte Dateien relevant. `true` kennzeichnet eine mitgelieferte Datei als externe Quelle, die unveröffentlicht bleibt. Alle Importe über Weboberfläche oder CLI sind automatisch externe Quellen.

### Glossar (`kind: terms`)

```json
{"schema_version": 1, "kind": "terms", "terms": [{"term": "quorum", "de": "Quorum", "explanation_de": "..."}]}
```

Begriffe werden kleingeschrieben und sind eindeutig. Vorkommen im Fragetext werden beim Üben automatisch markiert.

### Prüfungsziele (`kind: objectives`)

Siehe `objectives/300.json` als Beispiel. Enthält `module` (code, title, title_de, description_de, version, source_url, position) und `topics` mit `objectives` (code, title, title_de, weight, summary_de, tools).

Die Titel und Gewichte folgen den offiziellen Prüfungszielen des LPI (Quelle in `source_url`). Die deutschen Zusammenfassungen sind eigene Formulierungen.

### Labs (`kind: labs`)

```json
{
  "schema_version": 1, "kind": "labs", "module": "306", "license": "CC BY-SA 4.0",
  "labs": [{
    "id": "lab-306-01", "objective": "361.3", "title": "Titel",
    "goal_de": "Lernziel", "environment_de": "Benötigte Testumgebung", "duration_minutes": 45,
    "steps": [{"title": "Schritt", "text_de": "Anleitung", "commands": ["befehl 1", "befehl 2"]}],
    "checks": [{"question_de": "Kontrollfrage", "answer_de": "Antwort"}]
  }]
}
```

Befehle werden nur angezeigt, nie ausgeführt.

## Eigene Inhalte

- Prüfen: `lpic3ctl validate datei.json`
- Importieren: `lpic3ctl import datei.json --source "Quelle Datum" --exam-version 3.0 --rights unverified` oder über die Weboberfläche unter Verwaltung › Import (nur Administratoren und Betreuer). Angaben beim Import überschreiben die Felder im Dateikopf.
- Importierte Fragen sind unveröffentlicht, bis ein Betreuer sie für seine Lerngruppen oder ein Administrator sie systemweit freigibt (Verwaltung › Freigaben).
- Nutzungsrechte importierter Inhalte sind vom Importierenden zu beachten. Unerlaubt kopierte Prüfungsfragen dürfen nicht in dieses Repository aufgenommen werden.
