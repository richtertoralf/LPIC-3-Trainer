# Installation

Der LPIC-3-Trainer läuft auf Ubuntu 24.04/26.04 LTS und Debian 12/13 (x86_64 und ARM64). Benötigt werden Python 3.11 oder neuer, `python3-venv` und systemd. Ein Reverse Proxy mit HTTPS ist für den öffentlichen Betrieb Pflicht.

## Native Installation mit systemd

```bash
sudo apt install git python3 python3-venv
git clone https://github.com/richtertoralf/LPIC-3-Trainer.git
cd LPIC-3-Trainer
git checkout v0.0.1
sudo python3 -m app.cli install
```

`install` erledigt:

1. Prüfung der Voraussetzungen (Python, venv, systemd).
2. Systembenutzer `lpic3` ohne Login-Shell.
3. Kopie des Quellcodes nach `/opt/lpic3-trainer/app` und venv unter `/opt/lpic3-trainer/venv` (nur dieser Schritt nutzt das Shellskript `deploy/create-venv.sh`).
4. Konfiguration `/etc/lpic3-trainer/lpic3-trainer.env` (wird bei erneuter Installation nicht überschrieben).
5. Datenverzeichnis `/var/lib/lpic3-trainer` mit Datenbank, Migrationen und mitgelieferten Inhalten.
6. systemd-Unit `lpic3-trainer.service`, Symlink `/usr/local/bin/lpic3ctl`, Dienst aktivieren und starten.

Ist der Port bereits belegt, warnt die Installation. Dann `LPIC3_PORT` in der Konfiguration anpassen und `lpic3ctl restart` ausführen.

Danach im Browser `http://127.0.0.1:8000/` öffnen. Das erste registrierte Konto erhält Administratorrechte. Alternativ:

```bash
sudo lpic3ctl user create admin --role admin
```

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

Neue Version aus Git holen und aus dem frischen Checkout upgraden:

```bash
cd ~/LPIC-3-Trainer
git fetch --tags
git checkout v0.0.2
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
sudo lpic3ctl rollback
```

Bei Schemaänderungen zusätzlich die Sicherung von vor dem Upgrade mit `lpic3ctl restore` einspielen (siehe `docs/administration.md`).

Version prüfen:

```bash
lpic3ctl version
```

## Docker Compose

Alternativ zur nativen Installation:

```bash
git clone https://github.com/richtertoralf/LPIC-3-Trainer.git
cd LPIC-3-Trainer
docker compose -f deploy/docker-compose.yml up -d --build
```

Die Anwendung ist dann unter `http://127.0.0.1:8000/` erreichbar. Daten liegen im Volume `lpic3-data` unter `/var/lib/lpic3-trainer`, also in derselben Struktur wie bei der nativen Installation. Backups im Container: `docker compose -f deploy/docker-compose.yml exec lpic3-trainer lpic3ctl backup`.

Hinweis: Der Docker-Betrieb wurde in dieser Version nicht getestet, weil auf dem Entwicklungssystem kein Docker verfügbar war (siehe `docs/stand.md`).

## Entfernen

```bash
sudo lpic3ctl uninstall      # Dienst und Programmdateien entfernen, Daten bleiben
sudo lpic3ctl purge          # zusätzlich Konfiguration und Daten löschen, mit Rückfrage
sudo lpic3ctl purge --yes    # ohne Rückfrage (Skripte)
```
