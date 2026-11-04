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
| `lpic3ctl import DATEI... [--source TEXT --exam-code NNN-300 --exam-version X.Y --source-url URL --rights STATUS]` | Inhalte importieren (Fragen bleiben unveröffentlicht) | nein* |
| `lpic3ctl validate DATEI...` | Inhalte prüfen | nein |
| `lpic3ctl content-sync` | mitgelieferte Inhalte importieren | nein* |
| `lpic3ctl migrate` | Migrationen ausführen | nein* |
| `lpic3ctl serve` | im Vordergrund starten (wird von systemd genutzt) | nein |

\* Benötigt Schreibrechte auf das Datenverzeichnis. Auf einer Standardinstallation als `root` oder `lpic3` ausführen, zum Beispiel `sudo lpic3ctl backup`.

Exit-Codes: `0` Erfolg, `1` Fehler, `2` Bedienfehler oder Abbruch, `3` fehlende Voraussetzung oder Objekt nicht gefunden.

## Benutzerverwaltung

Rollen:

- **Administrator**: alles, einschließlich Einstellungen, Rollen, Löschen und systemweiter Freigabe von Importen.
- **Betreuer**: Benutzer freigeben, eigene Gruppen anlegen und betreuen, Fragen importieren und die eigenen Importe für die eigenen Gruppen freigeben, Lernstand der Gruppenmitglieder sehen.
- **Lernender**: lernen, Gruppen beitreten. Kein Import, keine Freigabe, keine Änderung von Fragen.

Weboberfläche: *Verwaltung › Benutzer*. Administratoren legen dort neue Konten mit Rolle und Startpasswort an („Benutzer anlegen“), geben Registrierungen frei, ändern Rollen, deaktivieren, setzen Passwörter zurück (neues Passwort wird einmalig angezeigt) und löschen. Betreuer sehen nur Konten, die auf Freigabe warten, und die Mitglieder ihrer eigenen Lerngruppen; unter *Import* sehen sie nur ihre eigenen Importe.

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

## Fragenimport, Herkunft und Freigabe

Rollen und Rechte:

- Nur Administratoren und Betreuer (Lehrer, Tutoren) importieren Fragen. Lernende können Fragen weder importieren noch anlegen, ändern oder freigeben; alle Verwaltungsseiten antworten ihnen mit 403 (getestet).
- Jeder Import braucht eine nachvollziehbare **Quelle** (`source`, z. B. „ExamTopics 04.11.2026“ oder „Eigene Fragen Kurs A“) und eine **Prüfungsgeneration** (`exam_version`, z. B. `3.0`). Beide stehen im Dateikopf oder werden im Importformular beziehungsweise per CLI angegeben. Ohne diese Angaben wird die Datei abgelehnt. Dazu kommen die **Prüfungsnummer** (`exam_code`, z. B. `305-300`; ohne Angabe Modulnummer-300, muss zum Modul passen), optional die **Original-URL** (`source_url`) und ein Rechtestatus (`rights`: geklärt, unbekannt, nicht geklärt). Alle Angaben werden in der Importcharge gespeichert und in Freigabe- und Lernansicht angezeigt.
- Beim Import vergleicht die Anwendung jede Frage mit dem vorhandenen Bestand des Moduls und meldet mögliche Dubletten (ab 80 % Textähnlichkeit) im Ergebnis; die Fragen werden trotzdem importiert.
- Einzelne Fragen lassen sich in der Datei mit `"active": false` ausschließen, etwa bei fachlich unsicherer Lösung. Das Kennzeichen bleibt bei erneutem Import erhalten.
- Importierte Fragen bleiben **unveröffentlicht**. Sie sind nur für den Importierenden und für Administratoren sichtbar.
- **Betreuer** geben unter *Verwaltung › Freigaben* ihre eigenen Importe für ihre eigenen Lerngruppen frei und nehmen die Freigabe dort wieder zurück. Fremde Importe oder fremde Gruppen können sie nicht freigeben.
- **Administratoren** geben einen Import systemweit für alle Lernenden frei (Schaltfläche „Systemweit freigeben“) oder für beliebige Gruppen.
- **Lernende** sehen den freigegebenen Grundbestand (mitgelieferte Projektfragen und systemweit freigegebene Importe) sowie die Freigaben ihrer eigenen Lerngruppen. Freigegebene Importe sind bei jeder Frage als „Zusatzfrage“ mit Quelle, Prüfungsgeneration und Rechtestatus markiert.
- Die **mitgelieferten Projektfragen** (`content/questions/*.json`, Quelle „LPIC-3 Trainer Projekt“, Prüfungsgeneration 3.0, CC BY-SA 4.0) bilden den bereits freigegebenen Grundbestand. Dateien unter `content/questions/extra/` sind externe Quellen und werden beim `content-sync` zwar importiert, bleiben aber unveröffentlicht.
- Wer freigibt, verantwortet die Zulässigkeit der Nutzung, insbesondere bei Quellen mit Rechtestatus „nicht geklärt“.

Weboberfläche: *Verwaltung › Import* (JSON-Datei, max. 5 MB, Quelle, Prüfungsgeneration, Rechtestatus), *Verwaltung › Freigaben* (Liste der Importe mit Quelle, Prüfungsgeneration, Modul, Fragenzahl, Rechtestatus und Importierendem; Freigabe je Gruppe, systemweit nur für Administratoren), *Verwaltung › Fragen* (Filter, Deaktivieren) und *Verwaltung › Import › Löschen* (Importcharge mit allen Fragen entfernen).

Kommandozeile:

```bash
lpic3ctl validate fragen.json
sudo lpic3ctl import fragen.json --source "ExamTopics 04.11.2026" --exam-version 3.0 --rights unverified
```

Importe über die Kommandozeile sind ebenfalls unveröffentlicht und werden in der Weboberfläche freigegeben. Format und Regeln: `content/README.md`.

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

`restore` läuft kontrolliert ab:

1. Rückfrage (entfällt mit `--yes`).
2. Dienstzustand prüfen: Läuft der systemd-Dienst, wird er gestoppt und am Ende wieder gestartet. Läuft stattdessen ein nicht über systemd verwalteter Server (Docker, `lpic3ctl serve` im Vordergrund), bricht `restore` mit einer eindeutigen Fehlermeldung ab, denn ein laufender Server würde sonst unbemerkt in die ersetzte Datei weiterschreiben.
3. Die aktuelle Datenbank wird als `lpic3-trainer.before-restore-<Datum>.db` gesichert.
4. Das Archiv wird eingespielt, Migrationen laufen, `PRAGMA integrity_check` muss `ok` liefern, sonst bricht der Befehl ab (die Sicherheitskopie bleibt liegen).
5. War der Dienst aktiv, wird er gestartet und der Health-Endpunkt abgewartet.

Diese Abläufe sind durch Regressionstests abgedeckt (`tests/test_restore_regression.py`).

## Betrieb und Diagnose

```bash
lpic3ctl status          # Dienst, Datenbank, Schema, Health
lpic3ctl check           # Prüfliste mit [OK]/[!!]
sudo lpic3ctl logs -f    # Protokolle
curl http://127.0.0.1:8000/health
```

`/health` liefert JSON mit Status, Version, Schema-Version und Journal-Modus. Bei Datenbankfehlern antwortet es mit HTTP 503.

Protokolle gehen über Uvicorn nach journald. Passwörter und Sitzungs-IDs werden nicht protokolliert.
