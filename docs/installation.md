# Installation

Der LPIC-3-Trainer läuft auf Ubuntu 24.04/26.04 LTS und Debian 12/13 (x86_64 und ARM64). Die native Installation mit systemd ist der Standardweg; Docker Compose ist optional.

Voraussetzungen:

- Python 3.11 oder neuer, `python3-venv`, `git`, systemd.
- Root-Rechte (sudo) für die Installation; der Dienst selbst läuft ohne Root als Benutzer `lpic3`.
- Internetzugang während der Installation (pip lädt die Python-Abhängigkeiten).
- Für den öffentlichen Betrieb ein Reverse Proxy mit HTTPS.

Prüfstand: Der komplette Ablauf (Installation, Dienststart durch systemd, Neustart, Upgrade von v0.0.2, Backup, Restore, Rollback, Deinstallation, Reverse Proxy) wurde am 5. November 2026 als Root in LXD-Systemcontainern mit Debian 12, Debian 13, Ubuntu 24.04 und Ubuntu 26.04 ausgeführt; Protokoll und Befunde in `docs/installationstest.md`. Nicht geprüft: blankes Metall oder VM mit eigenem Kernel, ARM64, Docker.

**Hinweis zu v0.0.2:** Der Installer von v0.0.2 bricht auf einem echten System ab (Konfigurationsverzeichnis für den Dienstbenutzer nicht lesbar) und `restore` schlägt unter Debian 12 fehl. Für eine Neuinstallation den aktuellen Stand von `main` oder einen neueren Tag verwenden; Workarounds in `docs/installationstest.md`, Abschnitt 3.

## Native Installation mit systemd (Standardweg)

### 1. Quellcode holen

```bash
sudo apt install git python3 python3-venv
git clone https://github.com/richtertoralf/LPIC-3-Trainer.git
cd LPIC-3-Trainer
git checkout main            # oder ein neuerer Tag als v0.0.2, siehe Hinweis oben
```

Für den Betrieb den Tag der gewünschten Version auschecken (`git tag` zeigt alle). `main` enthält den aktuellen Entwicklungsstand.

### 2. Installieren

```bash
sudo python3 -m app.cli install
```

`install` erledigt:

1. Prüfung der Voraussetzungen (Python, venv, systemd).
2. Systembenutzer `lpic3` ohne Login-Shell.
3. Kopie des Quellcodes nach `/opt/lpic3-trainer/app` und venv unter `/opt/lpic3-trainer/venv` (nur dieser Schritt nutzt das Shellskript `deploy/create-venv.sh`).
4. Konfiguration `/etc/lpic3-trainer/lpic3-trainer.env` (wird bei erneuter Installation nicht überschrieben).
5. Datenverzeichnis `/var/lib/lpic3-trainer` mit Datenbank, Migrationen und mitgelieferten Inhalten.
6. systemd-Unit `lpic3-trainer.service`, Symlink `/usr/local/bin/lpic3ctl`, Dienst aktivieren und starten.

Ist der Port bereits belegt, warnt die Installation. Dann `LPIC3_PORT` in der Konfiguration anpassen und `sudo lpic3ctl restart` ausführen.

Dateirechte nach der Installation: `/opt/lpic3-trainer` gehört root (nur lesbar für den Dienst), `/etc/lpic3-trainer` ist `0750 root:lpic3`, die Datei `lpic3-trainer.env` `0640 root:lpic3`, `/var/lib/lpic3-trainer` gehört `lpic3` (`0750`, Datenbank `0640`). Die systemd-Unit läuft mit `ProtectSystem=strict`, ohne Capabilities und mit Systemaufruffilter (`systemd-analyze security`: 1.3 bis 2.0, OK); sie darf nur in das Datenverzeichnis schreiben und kann keine Ports unter 1024 binden, dafür ist der Reverse Proxy zuständig.

Ohne Root liefern `lpic3ctl status` und `check` nur Standardwerte, weil die Konfiguration nicht lesbar ist; beide weisen darauf hin.

### 3. Status prüfen

```bash
sudo lpic3ctl status     # Dienst, Datenbank, Schema, Health-Check
sudo lpic3ctl check      # Prüfliste mit [OK]/[!!]
sudo lpic3ctl logs -n 50 # Protokolle aus journald
curl http://127.0.0.1:8000/health
```

### 4. Erster Administrator und Browserzugriff

Im Browser `http://127.0.0.1:8000/` öffnen (bei entferntem Server über den Reverse Proxy, siehe unten). Solange noch kein Konto existiert, erhält das erste über *Registrieren* angelegte Konto Administratorrechte. Alternativ auf der Kommandozeile:

```bash
sudo lpic3ctl user create admin --role admin
```

Hinweis: Sobald ein Konto existiert (auch ein per CLI angelegtes), werden weitere Registrierungen normale Lernende.

Weitere Benutzer legt der Administrator unter *Verwaltung › Benutzer* an oder gibt Registrierungen frei. Ein vergessenes Administratorpasswort setzt `sudo lpic3ctl user set-password <name>` zurück.

## Konfiguration

Datei `/etc/lpic3-trainer/lpic3-trainer.env` (Beispiel in `deploy/lpic3-trainer.env.example`):

| Variable | Standard | Bedeutung |
|----------|----------|-----------|
| `LPIC3_HOST` | `127.0.0.1` | Bindeadresse. Nur hinter einem Reverse Proxy auf andere Adressen setzen. |
| `LPIC3_PORT` | `8000` | Port |
| `LPIC3_DATA_DIR` | `/var/lib/lpic3-trainer` | Datenbank und Sicherungen |
| `LPIC3_DB_PATH` | `<DATA_DIR>/lpic3-trainer.db` | abweichender Datenbankpfad |
| `LPIC3_CONTENT_DIR` | `<App>/content` | Verzeichnis der mitgelieferten Inhalte |
| `LPIC3_SECURE_COOKIES` | `false` | `true` hinter HTTPS |
| `LPIC3_SESSION_HOURS` | `720` | Sitzungsdauer in Stunden |
| `LPIC3_LOG_LEVEL` | `info` | Uvicorn-Logstufe |
| `LPIC3_EXAM_QUESTIONS` | `60` | Fragen je Modulsimulation |
| `LPIC3_EXAM_MINUTES` | `90` | Zeit je Modulsimulation |
| `LPIC3_TOPIC_EXAM_QUESTIONS` | `15` | Fragen je Kapiteltest |
| `LPIC3_ENTRY_QUESTIONS` | `10` | Fragen je Eingangstest |

Nach Änderungen: `sudo lpic3ctl restart`.

Für die Entwicklung gibt es `.env.example` im Repository.

## Reverse Proxy mit HTTPS

Beispiel für nginx:

```nginx
server {
    listen 443 ssl;
    server_name lpic3.example.org;
    ssl_certificate     /etc/letsencrypt/live/lpic3.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lpic3.example.org/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $remote_addr;
        client_max_body_size 6m;
    }
}
```

In der Konfiguration `LPIC3_SECURE_COOKIES=true` setzen. Der `Host`- beziehungsweise `X-Forwarded-Host`-Header muss gesetzt sein, sonst lehnt die Origin-Prüfung Formulare ab.

## Update

Neue Version aus Git holen und aus dem Checkout upgraden:

```bash
cd ~/LPIC-3-Trainer
git fetch --tags
git checkout v0.0.3        # gewünschte neue Version, siehe git tag
sudo lpic3ctl upgrade --source "$PWD"
```

`upgrade`:

1. zeigt die installierte Version,
2. sichert Datenbank und Konfiguration nach `/var/lib/lpic3-trainer/backups/`,
3. stoppt den Dienst, verschiebt die alte Version nach `/opt/lpic3-trainer/app.previous`,
4. kopiert die neue Version, erneuert das venv,
5. führt Datenbankmigrationen aus und importiert die mitgelieferten Inhalte,
6. aktualisiert die systemd-Unit und startet den Dienst.

Die Konfiguration wird nicht überschrieben. Schlägt ein Schritt fehl, wird die vorherige Version automatisch zurückgespielt.

Zurück zur vorherigen Programmversion:

```bash
sudo lpic3ctl rollback                       # nur Programmdateien, wenn das Schema unverändert ist
sudo lpic3ctl rollback --restore ARCHIV      # Programmdateien und Datenbank aus der Sicherung von vor dem Upgrade
```

Hat das Upgrade das Datenbankschema geändert, verweigert `rollback` ohne `--restore` die Ausführung und nennt das passende Archiv unter `/var/lib/lpic3-trainer/backups/`. Die vorherige Version würde sonst mit einem unbekannten Schema nicht mehr starten. Einzelheiten in `docs/administration.md`.

Version prüfen:

```bash
lpic3ctl version
```

## Backup und Restore

```bash
sudo lpic3ctl backup                 # nach /var/lib/lpic3-trainer/backups/
sudo lpic3ctl restore <Archiv>       # stoppt den systemd-Dienst, sichert die aktuelle Datenbank,
                                     # spielt das Archiv ein, prüft die Integrität, startet den Dienst
```

`restore` verweigert die Ausführung, wenn ein Server läuft, der nicht über systemd verwaltet wird (Docker, Vordergrundstart). Diesen zuerst stoppen. Einzelheiten in `docs/administration.md`.

## Docker Compose

Alternativ zur nativen Installation:

```bash
git clone https://github.com/richtertoralf/LPIC-3-Trainer.git
cd LPIC-3-Trainer
docker compose -f deploy/docker-compose.yml up -d --build
```

Die Anwendung ist dann unter `http://127.0.0.1:8000/` erreichbar. Daten liegen im Volume `lpic3-data` unter `/var/lib/lpic3-trainer`, also in derselben Struktur wie bei der nativen Installation.

Backup im laufenden Container: `docker compose -f deploy/docker-compose.yml exec lpic3-trainer lpic3ctl backup --to /var/lib/lpic3-trainer/backups`.

Restore nur bei gestopptem Container, sonst verweigert `restore` die Ausführung:

```bash
docker compose -f deploy/docker-compose.yml stop
docker compose -f deploy/docker-compose.yml run --rm lpic3-trainer lpic3ctl restore /var/lib/lpic3-trainer/backups/<Archiv> --yes
docker compose -f deploy/docker-compose.yml start
```

Hinweis: Der Docker-Betrieb wurde nicht getestet, weil auf dem Entwicklungssystem kein Docker verfügbar war (siehe `docs/stand.md`).

## Entfernen

```bash
sudo lpic3ctl uninstall      # Dienst und Programmdateien entfernen, Daten bleiben
sudo lpic3ctl purge          # zusätzlich Konfiguration und Daten löschen, mit Rückfrage
sudo lpic3ctl purge --yes    # ohne Rückfrage (Skripte)
```
