# Administration

## lpic3ctl

`lpic3ctl` ist das zentrale Werkzeug. Nach der Installation liegt es unter `/usr/local/bin/lpic3ctl`. Jeder Befehl hat `--help`.

Verwaltung nach dem einheitlichen Standard der RICHTER.PROJECTS-Anwendungen (Langoptionen; die Unterbefehle darunter bleiben als Aliase gültig):

| Aufruf | Bedeutung | Exit |
|---|---|---|
| `lpic3ctl --help` | Kurzhilfe mit allen Befehlen | 0 |
| `lpic3ctl --version` | eine Zeile: `LPIC-3 Trainer <Version> (commit <7 Zeichen>[, dirty], release <Tag> oder branch <Name>, installiert <Zeit>)`, aus `/opt/lpic3-trainer/app/BUILD`, ohne Netz, venv oder laufenden Dienst; unbekannte Werte heißen `unbekannt` | 0 |
| `lpic3ctl --status` | rein lesend: Version, Konfigurationsdatei, Dienst, Autostart, Datenbank, Schema, Health-Check, Hinweis „Neustart nötig“ bei abweichender laufender Version, Zugriffsadressen (`http://127.0.0.1:PORT/`, bei Bindung an alle Schnittstellen auch die LAN-Adressen ohne Docker-, libvirt- und LXD-Bridges) | 0 kein technischer Fehler (auch gestoppter Dienst), 1 Unit `failed`, aktiv ohne Antwort oder nicht installiert, 2 ungültige Konfiguration |
| `sudo lpic3ctl --upgrade` | neuestes stabiles Release `vX.Y.Z` von GitHub installieren; „Bereits aktuell“ ohne Änderung und Neustart; kein Downgrade, keine Vorabversionen, nie `main` | 0 Erfolg oder bereits aktuell, 1 Fehler oder kein Netz (Installation unverändert oder wiederhergestellt), 2 Konfiguration passt nicht zur neuen Version |
| `sudo lpic3ctl --upgrade --source PFAD` | aus einem lokalen Checkout installieren (Branch, Arbeitsstand, offline, ältere Version) | wie oben |
| `sudo lpic3ctl --uninstall` | Dienst, Programmdateien und Kommando entfernen; Konfiguration, Daten und Dienstkonto bleiben | 0 |
| `sudo lpic3ctl --uninstall --purge [--yes]` | zusätzlich Konfiguration, Daten und Dienstkonto `lpic3` entfernen, mit Rückfrage | 0, 2 bei Abbruch |

Zusätzlich, nicht Teil des Standards: `lpic3ctl --check` (Prüfliste) und `sudo lpic3ctl --restart`.

Vollständige Befehlsliste:

| Befehl | Funktion | Root |
|--------|----------|------|
| `lpic3ctl install [--source DIR] [--force] [--no-start]` | installieren | ja |
| `lpic3ctl upgrade [--source DIR]` | aktualisieren mit Prüfung vor dem Stopp, Sicherung und Rückfall | ja |
| `lpic3ctl rollback [--restore ARCHIV]` | vorherige Programmversion zurück, bei Schemaänderung zusammen mit der Sicherung | ja |
| `lpic3ctl version [--remote]` | installierte Version und Herkunft; `--remote` fragt zusätzlich das neueste Release ab | nein |
| `lpic3ctl status` | Betriebszustand mit Zugriffsadressen | nein |
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

\* Benötigt Schreibrechte auf das Datenverzeichnis. Auf einer Standardinstallation als `root` oder `lpic3` ausführen, zum Beispiel `sudo lpic3ctl backup`. Nach einem als Root ausgeführten Befehl setzt `lpic3ctl` die Eigentümer im Daten- und Konfigurationsverzeichnis wieder auf den Dienstbenutzer, damit keine root-eigenen `-wal`/`-shm`-Dateien den Dienst blockieren. Ohne Root ist die Konfiguration (`0640 root:lpic3`) nicht lesbar; `status` und `check` melden das und arbeiten mit Standardwerten.

Exit-Codes nach dem RICHTER.PROJECTS-Standard: `0` Erfolg (auch „bereits aktuell“, „nichts zu entfernen“ oder bewusst gestoppter Dienst), `1` technischer Fehler (auch nicht installiert, Objekt nicht gefunden, kein Netz), `2` ungültige Parameter, ungültige Konfiguration oder Abbruch durch den Benutzer. Der frühere Code `3` wird nicht mehr verwendet.

## Benutzerverwaltung

Rollen:

- **Administrator**: alles, einschließlich Einstellungen, Rollen, Löschen und systemweiter Freigabe von Importen.
- **Betreuer**: Benutzer freigeben, eigene Gruppen anlegen und betreuen, Fragen importieren und die eigenen Importe sowie die mitgelieferten Zusatzpools für die eigenen Gruppen freigeben, Lernstand der Gruppenmitglieder sehen.
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

### Passwortrichtlinie

Die Richtlinie besteht nur aus Längenvorgaben und wird in `/etc/lpic3-trainer/lpic3-trainer.env` gesetzt, nicht in der Weboberfläche oder Datenbank:

| Variable | Standard | Zulässig |
|----------|----------|----------|
| `LPIC3_PASSWORD_MIN_LENGTH` | `8` | ganze Zahl 1 bis 1024 |
| `LPIC3_PASSWORD_MAX_LENGTH` | `128` | ganze Zahl von der Mindestlänge bis 1024 |

Beispiel für eine Lerngruppe mit einfachen Startpasswörtern:

```ini
LPIC3_PASSWORD_MIN_LENGTH=6
LPIC3_PASSWORD_MAX_LENGTH=24
```

Nach der Änderung `sudo lpic3ctl restart`; `sudo lpic3ctl check` zeigt die wirksame Richtlinie („Passwortrichtlinie: 6 bis 24 Zeichen“).

Wirkung:

- Dieselbe Prüfung an allen Stellen, die ein Passwort setzen: Registrierung, *Konto › Passwort ändern*, *Verwaltung › Benutzer › Benutzer anlegen*, `lpic3ctl user create` und `lpic3ctl user set-password`. Das vom Administrator erzeugte Startpasswort („Passwort zurücksetzen“) hält die Richtlinie ebenfalls ein (mindestens 12 Zeichen, sofern die Höchstlänge das erlaubt).
- Meldung bei Verstoß: „Das Passwort muss mindestens N Zeichen lang sein.“ beziehungsweise „Das Passwort darf höchstens N Zeichen lang sein.“ Die Formulare übergeben die Grenzen zusätzlich als `minlength`/`maxlength` an den Browser.
- Gezählt werden Zeichen, nicht Bytes; Leerzeichen zählen mit. Es gibt keine Komplexitätsregeln (Ziffern, Sonderzeichen) und keinen erzwungenen Passwortwechsel.
- Bestehende Konten bleiben unverändert gültig: Gespeichert ist nur der Argon2id-Hash, eine strengere Richtlinie greift erst beim nächsten Setzen eines Passworts. Ohne die Variablen gelten die Werte früherer Versionen (mindestens 8 Zeichen), Updates verhalten sich also unverändert.
- Ungültige Werte verhindern den Start des Dienstes mit einer klaren Meldung im Journal (`sudo lpic3ctl logs`), zum Beispiel „LPIC3_PASSWORD_MAX_LENGTH muss zwischen LPIC3_PASSWORD_MIN_LENGTH (8) und 1024 liegen, nicht 6.“; `lpic3ctl check` meldet dasselbe unter *Konfigurationswerte*.

## Lerngruppen

*Verwaltung › Gruppen*: Gruppe anlegen mit Beitritt `offen` oder `mit Freigabe`. Wer eine Gruppe anlegt, ist ihr Betreuer. Auf der Gruppenseite: Beitrittsanfragen freigeben, Mitglieder hinzufügen oder entfernen, Lernstand je Mitglied und Modul (geübte Fragen, Trefferquote, Hilfequote, beste Simulation) sowie je Mitglied die Zahl der abgeschlossenen, begonnenen und nicht begonnenen LABs. Lernende treten unter *Gruppen* bei.

**LAB-Stände und Empfehlungen.** Der Abschnitt *LAB-Stände der Gruppe* zeigt je Fach-LAB, welche aktiven Mitglieder es abgeschlossen haben, bearbeiten oder noch nicht begonnen haben. Betreuer sehen ausschließlich Mitglieder ihrer eigenen Gruppen (serverseitig geprüft, fremde Gruppen liefern 403). Mit den Häkchen *Empfohlen* wählt der Dozent die LABs für den Unterricht aus; die Mitglieder sehen die Empfehlung in ihrer LAB-Liste. Es gibt keinen Kursplan und keine Benotung.

**Auswertung je Prüfungsziel.** Die Schaltfläche *Auswertung je Prüfungsziel* auf der Gruppenseite fasst alle Antworten der aktiven Mitglieder (Übungen, Kapiteltests, Simulationen, Eingangstests) je Modul und Prüfungsziel zusammen: Zahl der Antworten, Trefferquote, Anteil der Übungsantworten mit Sprachhilfe, Zahl der antwortenden Mitglieder. Ab fünf Antworten je Ziel erscheint eine Einschätzung: unter 60 % richtig „vertiefen“, mindestens 50 % Sprachhilfe „Fachenglisch üben“, sonst „sicher“. Darunter stehen Fragen, die mindestens zweimal und in mindestens der Hälfte der Fälle falsch beantwortet wurden. Keine Rangliste, keine Benotung; Betreuer sehen nur eigene Gruppen.

**Dozentenhinweise.** Auf jeder LAB-Seite sehen Betreuer und Administratoren zusätzlich den Abschnitt *Hinweise für Dozenten* (Lernschwierigkeiten, alternative Lösungswege, Erfolgskontrolle, passende Prüfungsziele). Lernenden wird er nicht ausgeliefert.

## Fragenimport, Herkunft und Freigabe

Rollen und Rechte:

- Nur Administratoren und Betreuer (Lehrer, Tutoren) importieren Fragen. Lernende können Fragen weder importieren noch anlegen, ändern oder freigeben; alle Verwaltungsseiten antworten ihnen mit 403 (getestet).
- Jeder Import braucht eine nachvollziehbare **Quelle** (`source`, z. B. „ExamTopics 04.11.2026“ oder „Eigene Fragen Kurs A“) und eine **Prüfungsgeneration** (`exam_version`, z. B. `3.0`). Beide stehen im Dateikopf oder werden im Importformular beziehungsweise per CLI angegeben. Ohne diese Angaben wird die Datei abgelehnt. Dazu kommen die **Prüfungsnummer** (`exam_code`, z. B. `305-300`; ohne Angabe Modulnummer-300, muss zum Modul passen), optional die **Original-URL** (`source_url`) und ein Rechtestatus (`rights`: geklärt, unbekannt, nicht geklärt). Alle Angaben werden in der Importcharge gespeichert und in Freigabe- und Lernansicht angezeigt.
- Beim Import vergleicht die Anwendung jede Frage mit dem vorhandenen Bestand des Moduls und meldet mögliche Dubletten (ab 80 % Textähnlichkeit) im Ergebnis; die Fragen werden trotzdem importiert.
- Einzelne Fragen lassen sich in der Datei mit `"active": false` ausschließen, etwa bei fachlich unsicherer Lösung. Das Kennzeichen bleibt bei erneutem Import erhalten.
- Importierte Fragen bleiben **unveröffentlicht**. Sie sind nur für den Importierenden und für Administratoren sichtbar.
- **Betreuer** geben unter *Verwaltung › Freigaben* ihre eigenen Importe und die mit dem Trainer mitgelieferten Zusatzpools (`content/questions/extra`, Rechtestatus wird angezeigt) für ihre eigenen Lerngruppen frei und nehmen die Freigabe dort wieder zurück. Fremde Importe oder fremde Gruppen können sie nicht freigeben, systemweit freigeben nur Administratoren. (Seit Arbeitspaket 4; vorher nur eigene Importe, womit ein Dozent für die mitgelieferten Pools den Administrator brauchte.)
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
2. Dienstzustand prüfen: Läuft der systemd-Dienst (auch im Zustand `activating`, also in einer Neustartschleife), wird er gestoppt und am Ende wieder gestartet. Läuft stattdessen ein nicht über systemd verwalteter Server (Docker, `lpic3ctl serve` im Vordergrund), bricht `restore` mit einer eindeutigen Fehlermeldung ab, denn ein laufender Server würde sonst unbemerkt in die ersetzte Datei weiterschreiben.
3. Die aktuelle Datenbank wird als `lpic3-trainer.before-restore-<Datum>.db` gesichert.
4. Das Archiv wird eingespielt, Migrationen laufen, `PRAGMA integrity_check` muss `ok` liefern, sonst bricht der Befehl ab (die Sicherheitskopie bleibt liegen).
5. War der Dienst aktiv, wird er gestartet und der Health-Endpunkt abgewartet.

Diese Abläufe sind durch Regressionstests abgedeckt (`tests/test_restore_regression.py`, `tests/test_cli_permissions.py`) und wurden am 5. November 2026 auf Debian 12/13 und Ubuntu 24.04/26.04 in Containern tatsächlich ausgeführt (`docs/installationstest.md`).

## Upgrade und Rollback

`sudo lpic3ctl --upgrade` holt das neueste stabile Release (höchstes Tag `vX.Y.Z`, keine Vorabversionen, nie `main`) in ein temporäres Verzeichnis; `--upgrade --source DIR` nimmt stattdessen ein lokales Checkout. Ist das Release bereits installiert, endet der Befehl mit „Bereits aktuell“ ohne Änderung und Neustart; ein neuerer installierter Stand wird nicht zurückgestuft. Dann: neue Version nach `/opt/lpic3-trainer/app.new` kopieren und mit einem eigenen Prüf-venv (`venv.new`, wird danach gelöscht) Abhängigkeiten, Import und die vorhandene Konfiguration prüfen, solange der Dienst noch läuft; sichern (Archiv in `backups/`); den Dienst nur stoppen, wenn er lief; alte Version nach `app.previous`, neue nach `app`, venv erneuern, Datenbank migrieren, mitgelieferte Inhalte importieren, Unit aktualisieren; einen vorher laufenden Dienst neu starten, einen gestoppten gestoppt lassen. Scheitert die Prüfung, bleibt alles unverändert (Exit 2 bei unpassender Konfiguration, sonst 1); scheitert ein Schritt nach dem Tausch, wird die vorherige Version automatisch zurückgespielt und ein vorher laufender Dienst wieder gestartet. Jede Installation schreibt `app/BUILD` (Version, Commit, Branch, Release, `dirty`, Quelle, Zeitpunkt).

`lpic3ctl rollback` tauscht die Programmdateien zurück. Vorher prüft der Befehl, ob die vorherige Version das aktuelle Datenbankschema kennt (Vergleich der Alembic-Revision mit den Migrationsdateien in `app.previous`). Kennt sie es nicht, verweigert er die Ausführung und nennt das Archiv von vor dem Upgrade. `lpic3ctl rollback --restore ARCHIV` setzt dann Programmdateien und Datenbank gemeinsam zurück: Dienst stoppen, Programmdateien tauschen, venv neu bauen, Datenbank mit Sicherheitskopie ersetzen, `PRAGMA integrity_check`, Revision der Sicherung gegen die alte Version prüfen, Dienst starten, Health abwarten. Es laufen dabei keine Migrationen; die alte Version findet beim Start ihr eigenes Schema vor.

## Betrieb und Diagnose

```bash
lpic3ctl --version       # installierte Version und Herkunft (offline)
lpic3ctl --status        # Dienst, Autostart, Datenbank, Schema, Health, Adressen; Exit 0/1/2
lpic3ctl check           # Prüfliste mit [OK]/[!!]
sudo lpic3ctl logs -f    # Protokolle
curl http://127.0.0.1:8000/health
```

`/health` liefert JSON mit Status, Version, Schema-Version und Journal-Modus. Bei Datenbankfehlern antwortet es mit HTTP 503.

Protokolle gehen über Uvicorn nach journald. Passwörter und Sitzungs-IDs werden nicht protokolliert. Alembic-Meldungen erscheinen nur bei `serve`, `migrate`, `install`, `upgrade`, `content-sync` und `import`.

Die Unit ist gehärtet (`UMask=0027`, `PrivateDevices`, `ProtectProc=invisible`, `SystemCallFilter=@system-service`, leere `CapabilityBoundingSet`, `RestrictNamespaces`, dazu die bisherigen Optionen). `systemd-analyze security lpic3-trainer` meldet 1.3 bis 2.0 (OK). Der Dienst kann deshalb keine Ports unter 1024 binden; `LPIC3_PORT` muss 1024 oder höher sein, ein Reverse Proxy übernimmt 80/443.
