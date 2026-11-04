# Administration

## lpic3ctl

`lpic3ctl` ist das zentrale Werkzeug. Nach der Installation liegt es unter `/usr/local/bin/lpic3ctl`. Jeder Befehl hat `--help`.

| Befehl | Funktion | Root |
|--------|----------|------|
| `lpic3ctl install [--source DIR] [--force] [--no-start]` | installieren | ja |
| `lpic3ctl upgrade --source DIR` | aktualisieren mit Sicherung | ja |
| `lpic3ctl rollback` | vorherige Programmversion zurück | ja |
| `lpic3ctl version` | installierte und neueste Version (Git-Tags) | nein |
| `lpic3ctl status` | Dienst, Datenbank, Schema, Health-Check | nein |
| `lpic3ctl start` / `stop` / `restart` | Dienst steuern | ja |
| `lpic3ctl logs [-n N] [-f]` | journald-Protokolle | nein |
| `lpic3ctl backup [--to DIR] [--keep N]` | Sicherung erstellen | nein* |
| `lpic3ctl restore ARCHIV [--with-config] [--yes]` | Sicherung einspielen | ja |
| `lpic3ctl check` | Installation und Konfiguration prüfen | nein |
| `lpic3ctl uninstall` | entfernen, Daten behalten | ja |
| `lpic3ctl purge [--yes]` | alles entfernen | ja |
| `lpic3ctl user ...` | Benutzer verwalten | nein* |
| `lpic3ctl import DATEI... [--visibility public\|private] [--supplementary --source TEXT --rights STATUS]` | Inhalte importieren | nein* |
| `lpic3ctl validate DATEI...` | Inhalte prüfen | nein |
| `lpic3ctl content-sync` | mitgelieferte Inhalte importieren | nein* |
| `lpic3ctl migrate` | Migrationen ausführen | nein* |
| `lpic3ctl serve` | im Vordergrund starten (wird von systemd genutzt) | nein |

\* Benötigt Schreibrechte auf das Datenverzeichnis. Auf einer Standardinstallation als `root` oder `lpic3` ausführen, zum Beispiel `sudo lpic3ctl backup`.

Exit-Codes: `0` Erfolg, `1` Fehler, `2` Bedienfehler oder Abbruch, `3` fehlende Voraussetzung oder Objekt nicht gefunden.

## Benutzerverwaltung

Rollen:

- **Administrator**: alles, einschließlich Einstellungen, Rollen, Löschen, öffentliche Importe.
- **Betreuer**: Benutzer freigeben, eigene Gruppen anlegen und betreuen, Fragen importieren (privat, sichtbar für die eigenen Gruppen), Lernstand der Gruppenmitglieder sehen.
- **Lernender**: lernen, Gruppen beitreten.

Weboberfläche: *Verwaltung › Benutzer*. Dort Freigeben, Rolle ändern, Deaktivieren, Passwort zurücksetzen (neues Passwort wird einmalig angezeigt) und Löschen.

Kommandozeile:

```bash
sudo lpic3ctl user list
sudo lpic3ctl user create maria --role supervisor --display-name "Maria"
sudo lpic3ctl user set-role maria admin
sudo lpic3ctl user set-password maria
sudo lpic3ctl user disable maria
sudo lpic3ctl user activate maria
```

Registrierung: *Verwaltung › Einstellungen*. `offen` (sofort aktiv) oder `mit Freigabe` (Konto wartet, bis ein Betreuer oder Administrator es freigibt).

## Lerngruppen

*Verwaltung › Gruppen*: Gruppe anlegen mit Beitritt `offen` oder `mit Freigabe`. Wer eine Gruppe anlegt, ist ihr Betreuer. Auf der Gruppenseite: Beitrittsanfragen freigeben, Mitglieder hinzufügen oder entfernen, Lernstand je Mitglied und Modul (geübte Fragen, Trefferquote, Hilfequote, beste Simulation). Lernende treten unter *Gruppen* bei.

## Fragen bereitstellen

- *Verwaltung › Import*: JSON-Datei hochladen (max. 5 MB). Sichtbarkeit `privat` oder, nur für Administratoren, `öffentlich`. Fehlerhafte Dateien werden mit Fehlerliste abgelehnt.
- *Verwaltung › Fragen*: filtern nach Modul, Text oder Importcharge; Fragen deaktivieren oder aktivieren.
- *Verwaltung › Import › Löschen* entfernt eine Importcharge mit allen Fragen.
- Kommandozeile: `lpic3ctl validate datei.json`, `sudo lpic3ctl import datei.json --visibility private`.

Format und Regeln: `content/README.md`. Die Nutzungsrechte importierter Inhalte liegen beim Importierenden.

## Zusatzfragen

Zusatzfragen sind Fragen aus gesondert gekennzeichneten Quellen, zum Beispiel öffentlich im Internet kursierenden Fragensammlungen, deren Nutzungsrechte nicht geklärt sind. Sie werden getrennt vom regulären Bestand behandelt:

- Import mit der Option „Als Zusatzfragen importieren“ (Weboberfläche) oder `--supplementary` (CLI), immer mit Quellenbezeichnung (`source`, z. B. „ExamTopics 04.11.2026“) und Rechtestatus (`rights`: geklärt, unbekannt, nicht geklärt). Dateien unter `content/questions/extra/` werden bei `content-sync` automatisch als Zusatzquelle importiert.
- Für Lernende bleiben Zusatzfragen unsichtbar, bis ein Betreuer die Quelle unter *Verwaltung › Zusatzfragen* für eine seiner Lerngruppen freischaltet. Die Freischaltung lässt sich jederzeit zurücknehmen. Administratoren können jede Gruppe freischalten.
- Freigeschaltete Zusatzfragen erscheinen beim Üben und in Simulationen und sind bei jeder Frage als „Zusatzfrage“ mit Quelle und Rechtestatus markiert. In der Modulübersicht sieht der Lernende die freigeschalteten Quellen und kann wahlweise nur Zusatzfragen oder nur den regulären Bestand üben.
- Wer eine Quelle freischaltet, verantwortet die Zulässigkeit der Nutzung in seiner Gruppe. Importierende und Administratoren sehen Zusatzfragen immer.

Kommandozeile:

```bash
sudo lpic3ctl import fragen.json --supplementary --source "ExamTopics 04.11.2026" --rights unverified
```

## Backup und Restore

Sicherung (SQLite-Backup-API, kein Dateikopieren im WAL-Betrieb):

```bash
sudo lpic3ctl backup                      # nach /var/lib/lpic3-trainer/backups/
sudo lpic3ctl backup --to /mnt/backup --keep 14
```

Das Archiv `lpic3-trainer-backup-<Datum>.tar.gz` enthält die Datenbank, die Konfigurationsdatei und die Versionsnummer. Dateirechte `0600`.

Regelmäßige Sicherung, zum Beispiel täglich per cron:

```cron
30 3 * * * root /usr/local/bin/lpic3ctl backup --keep 14
```

Wiederherstellung:

```bash
sudo lpic3ctl restore /var/lib/lpic3-trainer/backups/lpic3-trainer-backup-20260101-033000.tar.gz
sudo lpic3ctl restore ARCHIV --with-config    # auch Konfiguration zurückspielen
```

`restore` fragt nach, stoppt den Dienst, sichert die aktuelle Datenbank als `lpic3-trainer.before-restore-<Datum>.db`, spielt das Archiv ein, führt Migrationen aus und startet den Dienst wieder.

## Betrieb und Diagnose

```bash
lpic3ctl status          # Dienst, Datenbank, Schema, Health
lpic3ctl check           # Prüfliste mit [OK]/[!!]
sudo lpic3ctl logs -f    # Protokolle
curl http://127.0.0.1:8000/health
```

`/health` liefert JSON mit Status, Version, Schema-Version und Journal-Modus. Bei Datenbankfehlern antwortet es mit HTTP 503.

Protokolle gehen über Uvicorn nach journald. Passwörter und Sitzungs-IDs werden nicht protokolliert.
