# Installationstest der nativen systemd-Installation

Stand: 5. November 2026, Arbeitspaket 1 (Branch `feat/ap1-install`), ergänzt um den Integrationstest des CLI-Standards (Abschnitt 6, Branch `fix/cli-upgrade-remote-config`). Dieses Dokument hält fest, was tatsächlich installiert und geprüft wurde, welche Fehler dabei gefunden und behoben wurden und was offen bleibt.

## 1. Testumgebung

Auf dem Entwicklungsrechner gibt es kein Root per `sudo`, aber LXD. Die Installation wurde deshalb als **echte Root-Installation mit systemd in isolierten LXD-Systemcontainern** durchgeführt. In jedem Container läuft ein eigenes systemd (PID 1), der Dienst wird durch systemd gestartet, `journalctl`, `useradd`, Dateirechte und Unit-Härtung wirken real. Nicht geprüft wurde die Installation auf blankem Metall oder in einer vollständigen VM; der Unterschied zum Container liegt in Kernel, Bootvorgang und Hardware, nicht in den Schritten des Installers.

| Container | Betriebssystem | Python | Ergebnis |
|---|---|---|---|
| `lpic3-deb12` | Debian 12 (bookworm) | 3.11.2 | Installation v0.0.2 (mit Workaround, siehe 3.1), Upgrade auf den neuen Stand, Rollback, Restore, erneutes Upgrade, Neustart des Containers |
| `lpic3-deb13` | Debian 13 (trixie) | 3.13.5 | Neuinstallation mit dem korrigierten Installer, Reverse Proxy mit nginx und HTTPS, Fehlversuch ohne Root |
| `lpic3-ubu24` | Ubuntu 24.04 LTS | 3.12.3 | Neuinstallation mit dem korrigierten Installer, Upgrade, Restore-Verweigerung bei fremdem Server, fehlgeschlagenes Upgrade mit automatischem Rückfall, Root-CLI bei gestopptem Dienst |
| `lpic3-ubu26` | Ubuntu 26.04 LTS | 3.14.4 | Neuinstallation, Änderung von Bindeadresse und Port, Zugriff von außen |
| `lpic3-min` | Ubuntu 24.04 minimal, ohne `python3-venv` | 3.12.3 | Fehlermeldung für fehlende Voraussetzung |

Die Container wurden mit `lxc launch images:debian/12`, `images:debian/13`, `ubuntu:24.04`, `ubuntu-daily:26.04` und `ubuntu-minimal:24.04` erzeugt; Netz über eine NAT-Bridge (`lxdbr0`, 10.200.77.0/24). Der Quellcode kam als Git-Klon (Tag `v0.0.2`) beziehungsweise als Archiv des Arbeitsstands in die Container.

## 2. Geprüfter Ablauf (Abschnitt 1.1 bis 1.3 des Auftrags)

Alle Schritte wurden mit den in `docs/installation.md` dokumentierten Befehlen ausgeführt.

| Schritt | Ergebnis |
|---|---|
| Frischer Klon, `apt install git python3 python3-venv`, `git checkout v0.0.2` | ok auf allen Systemen |
| `sudo python3 -m app.cli install` | v0.0.2: **Fehler** (3.1). Korrigierter Stand: ok auf Debian 12/13, Ubuntu 24.04/26.04, Laufzeit ca. 20–40 s |
| Systembenutzer `lpic3` ohne Login-Shell | `uid=995(lpic3)`, Shell `/usr/sbin/nologin` |
| Verzeichnisse | `/opt/lpic3-trainer/{app,venv}` root 0755; `/etc/lpic3-trainer` root:lpic3 0750, `lpic3-trainer.env` root:lpic3 0640; `/var/lib/lpic3-trainer` lpic3 0750, Datenbank 0640 |
| Datenbank und Migrationen | Schema `0004` (v0.0.2) bzw. `0005` (neuer Stand), WAL-Modus, Inhalte importiert (486 Fragen) |
| systemd-Unit installiert, aktiviert, gestartet | `active (enabled)`; `systemd-analyze security`: v0.0.2 7.2 MEDIUM, neuer Stand 1.3–2.0 OK |
| Automatischer Start nach Neustart | Container-Reboot: Dienst nach dem Start `active`, Health ok, keine Fehler im Journal |
| Erster Administrator | per `lpic3ctl user create admin --role admin` und per Registrierung des ersten Kontos (erhält Administratorrechte) |
| Browserzugriff | über `http://127.0.0.1:8000/` (curl mit Cookie-Jar: Registrierung, Anmeldung, Modulwahl, drei Übungsantworten, Gruppenanlage und Mitgliederzuordnung über die Verwaltungsseiten) |
| `lpic3ctl status`, `check`, `version`, `logs` | ok; `check` liefert 10 OK-Punkte |
| `start`, `stop`, `restart` | ok, Health nach `stop` nicht erreichbar, nach `start` wieder ok |
| Passwort setzen | `lpic3ctl user set-password dozent`: Anmeldung mit neuem Passwort 303, mit altem 400; in der Weboberfläche durch Administratoren |
| Bindeadresse und Port | `LPIC3_HOST=0.0.0.0`, `LPIC3_PORT=8080`, `lpic3ctl restart`: von außen erreichbar, `check` weist auf fehlende Secure-Cookies hin |
| Reverse Proxy | nginx mit selbstsigniertem Zertifikat, `LPIC3_SECURE_COOKIES=true`: Sitzungscookie mit `Secure`, POST mit fremdem `Origin` 403, mit korrektem Origin 303 |
| Fehlende Voraussetzungen | ohne `python3-venv`: „Fehlende Voraussetzung: Das Modul venv fehlt“, Exit 3; ohne Root: v0.0.2 Traceback (3.4), neuer Stand „benötigt Root-Rechte“, Exit 2 |
| Upgrade `v0.0.2` auf den neuen Stand | Sicherung vorher, Konfiguration erhalten, Schema 0004 auf 0005, alle Benutzer (3), Versuche (3), Gruppen (1) und Mitgliedschaften (3) erhalten, Anmeldung danach möglich |
| Backup im WAL-Betrieb | Archiv über SQLite-Backup-API bei laufendem Dienst, 0600 |
| Restore bei gestopptem Dienst | ok, Sicherheitskopie `lpic3-trainer.before-restore-*.db`, Integritätsprüfung, Dienststart, Health |
| Restore bei fremdem Server | `lpic3ctl serve` im Vordergrund als `lpic3`, Restore bricht mit Exit 2 ab, Datenbank unverändert |
| Rollback nach Upgrade mit Schemaänderung | v0.0.2: **Fehler** (3.2). Neuer Stand: ohne Sicherung verweigert (Exit 2, nennt das Archiv); mit `--restore` Schema 0004, Daten vollständig, Dienst gesund |
| Fehlgeschlagenes Upgrade | Quelle mit nicht auflösbarer Abhängigkeit: pip-Fehler, vorherige Version automatisch zurückgespielt, Dienst `active`, Health ok |
| `uninstall` und erneute Installation | Unit, Symlink und `/opt/lpic3-trainer` entfernt, Konfiguration und Datenbank bleiben; `install` danach ohne Rückfragen, Benutzer weiterhin vorhanden |

## 3. Gefundene und behobene Fehler

### 3.1 Installation v0.0.2 bricht ab (P1)

`install` legte `/etc/lpic3-trainer` als `root:root 0750` an. Der Dienstbenutzer konnte die Umgebungsdatei nicht lesen, `runuser -u lpic3 lpic3ctl content-sync` brach mit `PermissionError` ab, Unit und Symlink wurden nicht angelegt. Der Stub-Test hatte das nicht gezeigt, weil er als ein einziger Benutzer läuft.

Behoben: Das Konfigurationsverzeichnis gehört `root:lpic3` (0750), die Datei `root:lpic3` (0640). Test: `tests/test_cli_permissions.py`.

Workaround für eine bestehende v0.0.2-Quelle: `sudo chgrp lpic3 /etc/lpic3-trainer && sudo python3 -m app.cli install --force`.

### 3.2 Rollback hinterlässt startunfähigen Dienst (P1)

Nach `lpic3ctl rollback` von Schema 0005 zurück auf v0.0.2 fand Alembic die Revision 0005 nicht, der Dienst blieb in einer Neustartschleife (`activating`). Der Hinweis „bei Schemaänderungen restore nutzen“ reichte nicht, weil `restore` in diesem Zustand den Dienst nicht als aktiv erkannte (3.3) und unter Debian 12 abbrach (3.5).

Behoben: `rollback` vergleicht vor jeder Änderung die Schema-Revision der Datenbank mit den Migrationen der vorherigen Version. Passt sie nicht, verweigert der Befehl und nennt die Sicherung von vor dem Upgrade. `lpic3ctl rollback --restore ARCHIV` spielt die Programmdateien und die Datenbank gemeinsam zurück (Sicherheitskopie, Integritätsprüfung, Revisionsprüfung der Sicherung, Dienststart, Health). Test: `tests/test_cli_install.py::test_04_rollback_refuses_unknown_schema_and_restores_backup`.

### 3.3 Dienst in Neustartschleife galt als „nicht aktiv“ (P1)

`service_active()` erkannte nur `active`. Ein Dienst im Zustand `activating` hält die Datenbank bald wieder offen; `restore` hätte ihn nicht gestoppt. Behoben: `activating` und `reloading` gelten als aktiv und werden gestoppt. Test in `tests/test_cli_permissions.py`.

### 3.4 Traceback ohne Root (P2)

Als normaler Benutzer endeten `lpic3ctl status`, `check` und `install` mit einem `PermissionError`-Traceback beim Lesen der 0640-Konfiguration. Behoben: Die Datei wird übersprungen, `status` und `check` melden „nicht lesbar (Root-Rechte nötig)“, `install` meldet wie vorgesehen „benötigt Root-Rechte“.

### 3.5 Restore unter Debian 12 unmöglich (P1)

`TarFile.extract(..., filter="data")` gibt es erst ab Python 3.11.4; Debian 12 liefert 3.11.2, `restore` brach mit `TypeError` ab. Behoben: Fallback ohne `filter` nach eigener Prüfung des Archivmitglieds (nur reguläre Datei, kein Pfad). Test in `tests/test_cli_permissions.py`.

Workaround für v0.0.2 auf Debian 12: Dienst stoppen, Datenbank mit Python `tarfile` aus dem Archiv entpacken, mit `install -o lpic3 -g lpic3 -m 0640` an die Stelle von `/var/lib/lpic3-trainer/lpic3-trainer.db` setzen, Dienst starten (so wurde der Testcontainer wiederhergestellt).

### 3.6 Root-Befehle und Dateieigentümer (P2, vorbeugend)

`lpic3ctl user create` oder `migrate` als Root bei gestopptem Dienst könnten `-wal`/`-shm`-Dateien mit Eigentümer root hinterlassen. Nach jedem als Root ausgeführten Befehl werden Datenverzeichnis und Konfiguration jetzt wieder dem Dienstbenutzer zugeordnet. Im Test blieben die Dateien ohnehin `lpic3`, weil die CLI die Verbindung sauber schließt.

### 3.7 Härtung der Unit (P3)

`systemd-analyze security` bewertete die Unit mit 7.2 (MEDIUM). Ergänzt: `UMask=0027`, `PrivateDevices`, `ProtectProc=invisible`, `ProcSubset=pid`, `ProtectHostname`, `ProtectClock`, `ProtectKernelLogs`, `RestrictNamespaces`, `SystemCallFilter=@system-service` ohne `@privileged @resources`, leere `CapabilityBoundingSet`. Neue Bewertung 1.3 (Ubuntu) bis 2.0 (Debian) OK. Der Dienst startet und arbeitet damit auf allen vier Systemen. Folge: Ports unter 1024 kann der Dienst nicht mehr binden; dafür ist der Reverse Proxy zuständig.

### 3.8 Kleinigkeiten

- `pyproject.toml`: `license` als SPDX-Zeichenkette (setuptools-Warnung bei jeder venv-Erstellung).
- Alembic-INFO-Zeilen erscheinen nicht mehr bei `user`, `backup`, `restore`, `status`, `check` (nur noch bei `serve`, `migrate`, `install`, `upgrade`, `content-sync`, `import`).

## 4. Offen

- Keine Installation auf blankem Metall oder in einer VM mit eigenem Kernel; Bootvorgang und Hardware wurden nicht geprüft. Der Ablauf dafür steht in Abschnitt 5.
- Docker Compose weiterhin ungetestet (kein Docker auf dem Entwicklungsrechner).
- ARM64 nicht geprüft (nur x86_64-Container).
- Die Containertests sind manuell protokolliert (Logs im Arbeitsverzeichnis der Sitzung), nicht als wiederholbarer Test im Repository. Der Stub-Test `tests/test_cli_install.py` bleibt der automatisierte Nachweis.
- `lpic3ctl --upgrade` gegen das echte GitHub-Repository wurde nur im Fall „bereits aktuell“ ausgeführt (Abschnitt 6, Schritt D); ein echtes Release-Upgrade von GitHub gibt es erst, wenn ein Tag neuer als die installierte Version existiert. Der Mechanismus selbst ist mit einer lokalen Remote geprüft.

## 5. Testplan für einen echten Server oder eine VM

Voraussetzung: frisches Debian 12/13 oder Ubuntu 24.04/26.04, Root per sudo, Internetzugang, keine andere Anwendung auf Port 8000.

1. `sudo apt install git python3 python3-venv`, Klon, `git checkout <Tag>`, `sudo python3 -m app.cli install`. Erwartung: Exit 0, letzte Zeile „Installation abgeschlossen“.
2. `sudo lpic3ctl check` (alle Punkte OK), `systemctl status lpic3-trainer`, `curl http://127.0.0.1:8000/health`.
3. `id lpic3`, `ls -la /etc/lpic3-trainer /var/lib/lpic3-trainer`, `ls -ld /opt/lpic3-trainer`. Erwartung wie in Abschnitt 2.
4. Im Browser registrieren (erstes Konto = Administrator), Modul wählen, drei Fragen beantworten, unter Verwaltung eine Gruppe anlegen.
5. `sudo reboot`; danach `systemctl is-active lpic3-trainer` und Health.
6. `sudo lpic3ctl backup`, `sudo lpic3ctl restore <Archiv>`: Sicherheitskopie, Integrität ok, Dienst wieder aktiv, Anmeldung mit dem Konto aus Schritt 4.
7. `sudo lpic3ctl --upgrade` (neuestes stabiles Release; zweiter Aufruf meldet „Bereits aktuell“ ohne Neustart) oder neueren Tag auschecken und `sudo lpic3ctl --upgrade --source "$PWD"`; Daten aus Schritt 4 vorhanden, Schema aktuell, `lpic3ctl --version` zeigt Commit und Release. Noch nicht auf einem echten System ausgeführt: der Weg ohne `--source` und die Prüfung vor dem Dienststopp (Stand 5. November 2026, nur Stub-Tests).
8. `sudo lpic3ctl rollback` (erwartet: Verweigerung mit Hinweis auf die Sicherung, falls Schemaänderung), dann `sudo lpic3ctl rollback --restore <Archiv>`; anschließend erneut upgraden.
9. Reverse Proxy mit HTTPS einrichten, `LPIC3_SECURE_COOKIES=true`, Anmeldung über den Proxy, `Set-Cookie` enthält `Secure`.
10. `sudo lpic3ctl uninstall` (Daten bleiben), erneut `install` (Konfiguration und Daten wieder nutzbar), zum Schluss optional `sudo lpic3ctl purge`.

## 6. Integrationstest des CLI-Standards (5. November 2026)

Umgebung: LXD-Systemcontainer `lpic3-ubu26` (Ubuntu 26.04 daily 20261016, Python 3.14.4, systemd als PID 1, NAT-Netz mit Internetzugang), Ausführung als Root. Ausgangspunkt: Installation von Tag `v0.0.3` mit `python3 -m app.cli install`. Für die Upgrade-Tests diente ein lokales Bare-Repository `/root/remote.git` (Klon des Projekt-Repositorys) mit Test-Tags `v0.0.4` bis `v0.0.7`, eingestellt über `LPIC3_UPGRADE_REMOTE` in `/etc/lpic3-trainer/lpic3-trainer.env`; die Test-Releases sind Versionssprung-Commits auf dem Branch `fix/cli-upgrade-remote-config`. Im produktiven GitHub-Repository wurden keine Tags angelegt.

| Schritt | Prüfung | Ergebnis |
|---|---|---|
| A | v0.0.3 installiert; Benutzer `tester` angelegt, Kommentarzeile und `LPIC3_PASSWORD_MIN_LENGTH=6` in der env-Datei | ok |
| B | `python3 -m app.cli --upgrade --source /root/work` (Checkout mit CLI-Standard) auf die laufende v0.0.3 | ok, Exit 0; Dienst `active`/`enabled`, neu gestartet; env-Datei mit Marker und Variable erhalten; Benutzer erhalten; `BUILD` mit version, commit, branch, dirty=false, source, installed_at |
| C | `lpic3ctl --version` | `LPIC-3 Trainer 0.0.3 (commit a61fa5f, branch fix/cli-upgrade-remote-config, installiert 2026-11-05T19:05:01+00:00)`, Exit 0, ohne Netz |
| C | `lpic3ctl --status` unmittelbar nach dem Neustart | **Befund:** Exit 1 „Dienst aktiv, aber der Health-Endpunkt antwortet nicht“, weil die Anwendung in der ersten Sekunde nach dem Start noch Migrationen und Inhaltsimport ausführt; zwei Sekunden später Exit 0 mit `Health-Check: ok`. Behoben: `--status` wiederholt den Health-Check bei aktivem Dienst bis zu fünfmal im Abstand von zwei Sekunden. |
| D | `lpic3ctl --upgrade` gegen GitHub (installiert 0.0.3, neuestes Tag v0.0.3) | „Bereits aktuell. Keine Änderung, kein Neustart.“, Exit 0, `ActiveEnterTimestamp` unverändert |
| E | `LPIC3_UPGRADE_REMOTE=https://github.invalid/nix.git lpic3ctl --upgrade` | Exit 1 „Kein Zugriff auf GitHub; Installation unverändert …“, `BUILD` und Dienst unverändert |
| F | Remote in der zentralen env-Datei | **Befund:** die Variable wurde beim Import gelesen, also vor dem Laden der env-Datei, und damit ignoriert. Behoben (`remote_url()` zur Laufzeit), Regressionstest. |
| G | `lpic3ctl --upgrade` bei laufendem Dienst, Remote mit v0.0.4 und Vorabversion v0.0.5-rc1 | v0.0.4 installiert, rc1 ignoriert; Dienst neu gestartet, `/health` meldet 0.0.4; env-Datei und Datenbank (Benutzer) erhalten; Sicherung vor dem Upgrade; `BUILD` mit `release=v0.0.4`; `--version` zeigt `release v0.0.4`; `--status` Exit 0 |
| H | `lpic3ctl --upgrade` erneut | „Bereits aktuell“, Exit 0, kein Neustart |
| I | Anmeldung über HTTP mit dem in v0.0.3 angelegten Konto | 303 und `/api/me` liefert das Konto; Passwortrichtlinie aus der env-Datei wirkt |
| J | Dienst gestoppt, Release v0.0.5 | Upgrade läuft durch, „Der Dienst war gestoppt und bleibt gestoppt.“; `is-active inactive`, `is-enabled enabled`; `--status` Exit 0 mit `Dienst: inactive` |
| K1 | Port 8000 fremd belegt, Dienst neu gestartet | Unit im Zustand `activating` (Neustartschleife); `--status` Exit 1 mit Fehlerzeile; nach Freigabe des Ports Exit 0 |
| K2 | `LPIC3_PASSWORD_MAX_LENGTH=1` in der env-Datei, Release v0.0.6 | `--status` Exit 2 mit Variablenname; `--upgrade` Exit 2 „die vorhandene Konfiguration passt nicht zur neuen Version“, Dienst nicht gestoppt, kein Neustart, `BUILD` weiter v0.0.5, kein `app.new` übrig |
| L | Release v0.0.7 mit defekter Inhaltsdatei (Fehler erst nach dem Tausch, bei content-sync) | Exit 1, „Vorherige Version wird wiederhergestellt“, danach `active`, `/health` 0.0.5, `--version` v0.0.5, Benutzer vorhanden, `app.previous` wieder `app`. **Befund:** die Fehlermeldung des Kindprozesses lautete „Ungültige Konfiguration: 300-mixed-environments.json: invalid JSON“, weil jeder `ValueError` so benannt wurde. Behoben (`ConfigError` nur für `LPIC3_*`-Werte), Regressionstest. |
| M | defektes Tag aus der Remote entfernt, `--upgrade` | v0.0.6 installiert, Exit 0, `/health` 0.0.6 |
| N | `lpic3ctl --uninstall` | Dienst und `/opt/lpic3-trainer` entfernt, `/etc/lpic3-trainer/lpic3-trainer.env`, Datenbank und Sicherungen vorhanden. Danach gibt es kein `lpic3ctl` mehr; „nicht installiert“ (Exit 1) meldet nur `python3 -m app.cli --status` aus einem Checkout. |

Kosmetischer Befund: In einer Pipe erschienen die Meldungen von `lpic3ctl` nach denen der Kindprozesse (gepufferte Ausgabe). Behoben durch `flush` in `say`/`warn`. Die pip-Warnung „BuildBackendWarning: Editable installation“ unter Python 3.14 stammt von setuptools und ist unkritisch.

Nicht geprüft: `--upgrade --purge`-Kombinationen, ARM64, blankes Metall, Docker.
