# Installation

Der LPIC-3-Trainer läuft auf Ubuntu 24.04/26.04 LTS und Debian 12/13 (x86_64 und ARM64). Die native Installation mit systemd ist der Standardweg; Docker Compose ist optional.

Voraussetzungen:

- Python 3.11 oder neuer, `python3-venv`, `git`, systemd.
- Root-Rechte (sudo) für die Installation; der Dienst selbst läuft ohne Root als Benutzer `lpic3`.
- Internetzugang während der Installation (pip lädt die Python-Abhängigkeiten) und für `lpic3ctl --upgrade` von GitHub. Der laufende Betrieb braucht kein Internet (Abschnitt *Betrieb ohne Internet, im LAN und im Internet*).
- Für den öffentlichen Betrieb ein Reverse Proxy mit HTTPS.

Prüfstand: Der komplette Ablauf (Installation, Dienststart durch systemd, Neustart, Upgrade von v0.0.2, Backup, Restore, Rollback, Deinstallation, Reverse Proxy) wurde am 5. November 2026 als Root in LXD-Systemcontainern mit Debian 12, Debian 13, Ubuntu 24.04 und Ubuntu 26.04 ausgeführt; Protokoll und Befunde in `docs/installationstest.md`. Nicht geprüft: blankes Metall oder VM mit eigenem Kernel, ARM64, Docker.

**Hinweis zu v0.0.2:** Der Installer von v0.0.2 bricht auf einem echten System ab (Konfigurationsverzeichnis für den Dienstbenutzer nicht lesbar) und `restore` schlägt unter Debian 12 fehl. Für eine Neuinstallation den aktuellen Stand von `main` oder einen neueren Tag verwenden; Workarounds in `docs/installationstest.md`, Abschnitt 3.

## Native Installation mit systemd (Standardweg)

### 1. Quellcode holen

```bash
sudo apt install git python3 python3-venv
git clone https://github.com/richtertoralf/LPIC-3-Trainer.git
cd LPIC-3-Trainer
git checkout v0.0.5          # oder ein neuerer Tag; nicht v0.0.2, siehe Hinweis oben
```

Für den Betrieb den Tag der gewünschten Version auschecken (`git tag` zeigt alle). `main` enthält den aktuellen Entwicklungsstand.

### 2. Installieren

```bash
sudo python3 -m app.cli install
```

Abweichung vom RICHTER.PROJECTS-Standard (`sudo ./install.sh`): Der LPIC-3 Trainer hat kein Installationsskript, weil `lpic3ctl` ein Python-Modul der Anwendung ist und die Erstinstallation mit dem Systempython ohne venv läuft (Vorgabe in AGENTS.md). Dieser Weg ist auf Debian 12/13 und Ubuntu 24.04/26.04 geprüft; eine zusätzliche Skriptschicht nur zur Vereinheitlichung gibt es nicht. Alle weiteren Verwaltungsbefehle folgen dem Standard (`--version`, `--status`, `--upgrade`, `--uninstall`).

`install` erledigt:

1. Prüfung der Voraussetzungen (Python, venv, systemd).
2. Systembenutzer `lpic3` ohne Login-Shell.
3. Kopie des Quellcodes nach `/opt/lpic3-trainer/app` und venv unter `/opt/lpic3-trainer/venv` (nur dieser Schritt nutzt das Shellskript `deploy/create-venv.sh`).
4. Konfiguration `/etc/lpic3-trainer/lpic3-trainer.env` (wird bei erneuter Installation nicht überschrieben).
5. Datenverzeichnis `/var/lib/lpic3-trainer` mit Datenbank, Migrationen und mitgelieferten Inhalten.
6. systemd-Unit `lpic3-trainer.service`, Symlink `/usr/local/bin/lpic3ctl`, Dienst aktivieren und starten.

Ist der Port bereits belegt, warnt die Installation. Dann `LPIC3_PORT` in der Konfiguration anpassen und `sudo lpic3ctl restart` ausführen.

Dateirechte nach der Installation: `/opt/lpic3-trainer` gehört root (nur lesbar für den Dienst), `/etc/lpic3-trainer` ist `0750 root:lpic3`, die Datei `lpic3-trainer.env` `0640 root:lpic3`, `/var/lib/lpic3-trainer` gehört `lpic3` (`0750`, Datenbank `0640`). Die systemd-Unit läuft mit `ProtectSystem=strict`, ohne Capabilities und mit Systemaufruffilter (`systemd-analyze security`: 1.3 bis 2.0, OK); sie darf nur in das Datenverzeichnis schreiben und kann keine Ports unter 1024 binden, dafür ist der Reverse Proxy zuständig.

Ohne Root ist die Konfiguration nicht lesbar: `lpic3ctl --status` zeigt dann nur Version und Dienstzustand und bittet um `sudo lpic3ctl --status`; `check` arbeitet mit Standardwerten und weist darauf hin.

### 3. Status prüfen

```bash
lpic3ctl --version       # installierte Version, Commit, Release oder Branch, Installationszeit (offline)
sudo lpic3ctl --status   # Dienst, Autostart, Datenbank, Schema, Health-Check, Zugriffsadressen
sudo lpic3ctl check      # Prüfliste mit [OK]/[!!]
sudo lpic3ctl logs -n 50 # Protokolle aus journald
curl http://127.0.0.1:8000/health
```

`--status` endet mit 0, wenn kein technischer Fehler vorliegt, auch bei bewusst gestopptem Dienst; mit 1 bei `failed`, bei aktivem Dienst ohne Antwort am Health-Endpunkt oder ohne Installation; mit 2 bei ungültiger Konfiguration. Ohne Root ist die Konfiguration nicht lesbar; `--status` zeigt dann Version und Dienstzustand und den Hinweis „Bitte sudo lpic3ctl --status verwenden.“ statt irreführender Standardwerte. Bei `LPIC3_HOST=0.0.0.0` listet `--status` jede LAN- und VPN-Adresse des Servers mit Port und Schnittstelle (ohne Container- und VM-Bridges); das sind die konfigurierten Adressen, die Erreichbarkeit aus dem Netz prüft der Befehl nicht.

### 4. Erster Administrator und Browserzugriff

Im Browser `http://127.0.0.1:8000/` öffnen (bei entferntem Server über den Reverse Proxy, siehe unten). Solange noch kein Konto existiert, erhält das erste über *Registrieren* angelegte Konto Administratorrechte. Alternativ auf der Kommandozeile:

```bash
sudo lpic3ctl user create admin --role admin
```

Hinweis: Sobald ein Konto existiert (auch ein per CLI angelegtes), werden weitere Registrierungen normale Lernende.

Weitere Benutzer legt der Administrator unter *Verwaltung › Benutzer* an oder gibt Registrierungen frei. Ein vergessenes Administratorpasswort setzt `sudo lpic3ctl user set-password <name>` zurück.

## Konfiguration

### 1. Überblick

Der Trainer wird über Umgebungsvariablen mit dem Präfix `LPIC3_` eingestellt.
Bei der nativen Installation stehen sie in einer Datei, die systemd beim Start
einliest. Dazu kommt eine Einstellung in der Weboberfläche: der
Registrierungsmodus. Alle Einstellungen gelten dauerhaft für die Installation;
es gibt keine Einstellungen je Kurs oder Lerngruppe.

### 2. Speicherorte

| Betrieb | Ort |
|---|---|
| Native Installation | `/etc/lpic3-trainer/lpic3-trainer.env` (Vorlage: `deploy/lpic3-trainer.env.example`, nach der Installation auch unter `/opt/lpic3-trainer/app/deploy/`) |
| Docker Compose | `environment` in `deploy/docker-compose.yml` und `ENV` in `deploy/Dockerfile`; keine Konfigurationsdatei |
| Entwicklung | `.env.example` im Repository, in die Shell übernehmen |
| Registrierungsmodus | Datenbank, gesetzt unter *Verwaltung › Einstellungen* |

### 3. Einstellungen

| Variable | Standard | Zulässige Werte | Bedeutung |
|----------|----------|-----------------|-----------|
| `LPIC3_HOST` | `127.0.0.1` (Docker: `0.0.0.0`) | IP-Adresse oder Hostname | Bindeadresse. Nur hinter einem Reverse Proxy oder für Tests im LAN ändern, siehe [Zugriff aus dem lokalen Netzwerk](#zugriff-aus-dem-lokalen-netzwerk). |
| `LPIC3_PORT` | `8000` | ganze Zahl | Port |
| `LPIC3_DATA_DIR` | `/var/lib/lpic3-trainer` (Vorlage) | Pfad | Datenbank und Sicherungen; ohne Variable im Checkout `./data` |
| `LPIC3_DB_PATH` | `<DATA_DIR>/lpic3-trainer.db` | Pfad | abweichender Datenbankpfad |
| `LPIC3_CONTENT_DIR` | `<App>/content` | Pfad | Verzeichnis der mitgelieferten Inhalte |
| `LPIC3_SECURE_COOKIES` | `false` | `true`, `1`, `yes`, `on` = an; jeder andere Wert = aus | `true` hinter HTTPS |
| `LPIC3_SESSION_HOURS` | `720` | ganze Zahl (Stunden) | Sitzungsdauer |
| `LPIC3_LOG_LEVEL` | `info` | Uvicorn-Logstufen, z. B. `warning`, `info`, `debug` | Uvicorn-Logstufe |
| `LPIC3_EXAM_QUESTIONS` | `60` | ganze Zahl | Fragen je Modulsimulation |
| `LPIC3_EXAM_MINUTES` | `90` | ganze Zahl | Zeit je Modulsimulation |
| `LPIC3_TOPIC_EXAM_QUESTIONS` | `15` | ganze Zahl | Fragen je Kapiteltest |
| `LPIC3_ENTRY_QUESTIONS` | `10` | ganze Zahl | Fragen je Eingangstest |
| `LPIC3_PASSWORD_MIN_LENGTH` | `8` | ganze Zahl 1 bis 1024 | Mindestlänge neuer Passwörter in Zeichen |
| `LPIC3_PASSWORD_MAX_LENGTH` | `128` | ganze Zahl von der Mindestlänge bis 1024 | Höchstlänge neuer Passwörter in Zeichen |
| `LPIC3_UPGRADE_REMOTE` | GitHub-Repository des Projekts | Git-URL oder Pfad | Git-Remote für `lpic3ctl --upgrade` und `version --remote`, z. B. ein lokaler Spiegel |

Registrierungsmodus (*Verwaltung › Einstellungen*): `open` (Standard, neue
Konten sind sofort aktiv) oder `approval` (neue Konten warten auf Freigabe durch
Betreuer oder Administrator). Das erste registrierte Konto erhält unabhängig
davon Administratorrechte.

Passwortrichtlinie: Die beiden Längen gelten einheitlich für alle Stellen, die
ein Passwort setzen; ohne die Variablen gelten 8 und 128 Zeichen. Wirkung und
Beispiele: [Administration, Passwortrichtlinie](administration.md#passwortrichtlinie).

Nur für `lpic3ctl` und Tests: `LPIC3_CONFIG_DIR`, `LPIC3_INSTALL_DIR`,
`LPIC3_SYSTEMD_DIR` und `LPIC3_BIN_DIR` verschieben die Pfade, die `lpic3ctl`
verwendet; die systemd-Unit nutzt fest `/etc/lpic3-trainer` und
`/opt/lpic3-trainer`. `LPIC3_UNPRIVILEGED_TEST` ist ausschließlich für die
automatischen Tests. Im Betrieb keine dieser Variablen setzen.

### 4. Prioritäten

- Für den Dienst gilt nur die Datei, die systemd über `EnvironmentFile` einliest;
  fehlt eine Variable, gilt der eingebaute Standard.
- Für `lpic3ctl` gilt: bereits in der Shell gesetzte `LPIC3_*`-Variablen haben
  Vorrang vor der Datei. Für Prüfungen deshalb keine `LPIC3_*`-Variablen in der
  eigenen Shell setzen, sonst zeigt `lpic3ctl` andere Werte als der Dienst
  verwendet.
- `LPIC3_DB_PATH` hat Vorrang vor `LPIC3_DATA_DIR`.
- Docker: `environment` in der Compose-Datei vor `ENV` im Dockerfile.

### 5. Einrichtung und Änderung

Datei mit Root-Rechten bearbeiten, danach neu starten und prüfen:

```bash
sudoedit /etc/lpic3-trainer/lpic3-trainer.env
sudo lpic3ctl restart
sudo lpic3ctl check
```

Den Registrierungsmodus ändert ein Administrator in der Weboberfläche.

### 6. Wirksamkeit

| Änderung | Wirksam |
|---|---|
| `LPIC3_*` in der Datei | nach `sudo lpic3ctl restart` |
| `LPIC3_UPGRADE_REMOTE` | beim nächsten Aufruf von `lpic3ctl` |
| Registrierungsmodus | sofort |
| Passwortlängen | ab dem nächsten Setzen eines Passworts; bestehende Passwörter bleiben gültig |

### 7. Geheimnisse und Berechtigungen

- Die Konfiguration enthält keine Geheimwerte. Passwörter liegen nur als
  Argon2id-Hash in der Datenbank; Sitzungen werden serverseitig verwaltet.
- `/etc/lpic3-trainer` ist `0750 root:lpic3`, die Datei `0640 root:lpic3`.
  Ohne Root ist sie nicht lesbar; `lpic3ctl` meldet das.
- Sicherungen (`lpic3ctl backup`) haben den Modus `0600` und enthalten die
  Datenbank mit Passworthashes sowie die Konfigurationsdatei.
- Bekannte Grenze: Die Anwendung übernimmt Proxy-Header wie
  `X-Forwarded-For` unabhängig vom Absender. Bei direkter Bindung an eine
  Netzwerkadresse ohne Reverse Proxy sind diese Angaben nicht verlässlich; für
  den Dauerbetrieb deshalb wie unter [Sicherheit](#zugriff-aus-dem-lokalen-netzwerk)
  beschrieben hinter einem Reverse Proxy betreiben.

### 8. Installation, Aktualisierung, Entfernen

| Vorgang | Wirkung auf die Konfiguration |
|---|---|
| `install` | legt die Datei aus der Vorlage an, wenn sie fehlt; eine vorhandene Datei bleibt |
| `--upgrade` | verändert die Datei nicht und ergänzt keine neuen Variablen; prüft vor dem Dienststopp, ob die neue Version die vorhandene Konfiguration annimmt (sonst Abbruch mit Exitcode 2, der Dienst läuft weiter); sichert Datenbank und Datei. Neue Variablen von Hand übernehmen, siehe [Konfiguration nach dem Upgrade vergleichen](#konfiguration-nach-dem-upgrade-vergleichen) |
| `restore --with-config` | ersetzt die Datei durch die Fassung aus der Sicherung |
| `--uninstall` | Datei, Daten und Dienstkonto bleiben |
| `--uninstall --purge` | löscht `/etc/lpic3-trainer` und das in `LPIC3_DATA_DIR` eingetragene Verzeichnis vollständig samt Inhalt sowie das Dienstkonto. Vorher prüfen, dass dieses Verzeichnis nur Daten des Trainers enthält; eine Einschränkung auf eigene Daten ist geplant (#26). |

### 9. Prüfung und Fehlerdiagnose

- `sudo lpic3ctl --status` zeigt Konfigurationsdatei, Datenbank, Schema,
  Health-Check und Adressen; eine ungültige Konfiguration ergibt Exitcode 2.
- `sudo lpic3ctl --check` prüft Datei, Werte, Datenverzeichnis, Datenbank,
  Schema, Inhaltsdateien, Unit, Dienst und Health-Endpunkt und zeigt die
  wirksame Passwortrichtlinie. Ungültige Werte erscheinen unter
  *Konfigurationswerte*. `--check` endet mit Exitcode 0, wenn alles in Ordnung
  ist, sonst mit 1 – auch bei ungültigen Werten (Exit 2 dafür ist geplant, #23). Eine andere Datei als die
  installierte kann `--check` nicht prüfen.
- Ungültige Werte verhindern den Start des Dienstes; die Meldung steht im
  Journal (`sudo lpic3ctl logs`). Bei den Passwortlängen nennt sie den
  zulässigen Bereich.
- `lpic3ctl check` ohne Root kann die Datei nicht lesen und prüft dann mit den
  Standardwerten.

## Zugriff aus dem lokalen Netzwerk

Standardmäßig bindet der Dienst mit `LPIC3_HOST=127.0.0.1` nur an die Loopback-Adresse: Die Anwendung ist dann ausschließlich auf dem Server selbst erreichbar (oder über einen Reverse Proxy auf demselben Rechner). Von einem anderen Rechner im LAN kommt ohne weitere Einstellung keine Verbindung zustande, auch wenn Dienst und Health-Check lokal funktionieren.

Sollen Lernende im lokalen Netz direkt zugreifen, die Bindeadresse ausschließlich in `/etc/lpic3-trainer/lpic3-trainer.env` ändern (keine Änderung an der systemd-Unit oder am Programmcode):

```ini
LPIC3_HOST=0.0.0.0        # alle IPv4-Adressen des Servers
# oder nur eine Schnittstelle, z. B.
# LPIC3_HOST=192.168.1.20
LPIC3_PORT=8000
```

Dann den Dienst neu starten und die Bindung kontrollieren:

```bash
sudo lpic3ctl restart
ss -ltnp | grep 8000            # erwartet: 0.0.0.0:8000 bzw. die gewählte Adresse, Prozess python/uvicorn
curl http://127.0.0.1:8000/health
curl http://<Server-IP>:8000/health    # vom Server selbst und von einem anderen Rechner im LAN
```

Zeigt `ss` weiterhin `127.0.0.1:8000`, wurde die Datei nicht gelesen (Tippfehler, Variable auskommentiert) oder der Dienst nicht neu gestartet; `sudo lpic3ctl status` zeigt die wirksame Adresse. Mit `LPIC3_HOST=::` bindet der Dienst an IPv6 (auf Linux üblicherweise auch IPv4).

**Firewall.** Ist auf dem Server eine Firewall aktiv, muss der Port freigegeben werden, am besten nur für das lokale Netz:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp     # ufw (Ubuntu)
sudo nft add rule inet filter input ip saddr 192.168.1.0/24 tcp dport 8000 accept   # nftables (Debian), Regelsatz dauerhaft speichern
```

Die Hardening-Optionen der systemd-Unit erlauben Ports ab 1024; 8000 ist davon nicht betroffen.

**Virtuelle Maschinen (libvirt/KVM).** Läuft der Trainer in einer VM, entscheidet das virtuelle Netz, wer ihn erreicht:

- *NAT* (libvirt-Standardnetz `default`, meist 192.168.122.0/24): Die VM erreicht das LAN, das LAN die VM aber nicht. Vom Virtualisierungshost aus ist `http://192.168.122.x:8000/` erreichbar, von anderen Rechnern nicht. Für den LAN-Zugriff entweder eine Portweiterleitung auf dem Host einrichten (libvirt-Hook oder nftables-DNAT vom Host-Port auf die VM) oder das Netz wechseln.
- *Bridged* (VM hängt über eine Linux-Bridge wie `br0` oder ein macvtap-Gerät direkt am physischen Netz): Die VM bekommt eine Adresse aus dem LAN und ist für alle Rechner im LAN wie ein eigener Server erreichbar. Das ist für den Unterricht der einfachste Weg.
- *Isoliert* (ohne Forwarding): nur Host und andere VMs im selben Netz.

In allen Fällen muss `LPIC3_HOST` in der VM auf `0.0.0.0` oder die VM-Adresse stehen, sonst nimmt der Dienst nur Verbindungen aus der VM selbst an. Eine Anleitung zu den libvirt-Netztypen steht in `docs/lab-umgebung.md`.

**Sicherheit.** Ohne Reverse Proxy läuft die Verbindung über unverschlüsseltes HTTP: Anmeldedaten und Sitzungscookies sind im LAN mitlesbar, und `LPIC3_SECURE_COOKIES` muss `false` bleiben, sonst sendet der Browser das Sitzungscookie nicht. Direkter HTTP-Zugriff ist deshalb nur für Tests und kurze Übungen in einem vertrauenswürdigen, abgeschotteten Netz vertretbar. Für den dauerhaften Mehrbenutzerbetrieb, auch im LAN, den Dienst bei `LPIC3_HOST=127.0.0.1` lassen und einen Reverse Proxy mit HTTPS davorschalten (nächster Abschnitt); `lpic3ctl check` weist auf eine öffentliche Bindung ohne `LPIC3_SECURE_COOKIES=true` hin. Nie direkt ins Internet freigeben.

## Betrieb ohne Internet, im LAN und im Internet

Der Trainer ist für den Betrieb auf eigener Infrastruktur gebaut. Der laufende Lernbetrieb braucht keine Verbindung nach außen.

**Alles kommt vom eigenen Server.** HTML, CSS, JavaScript, Icons, Web-App-Manifest und Service Worker liefert der Trainer selbst aus (`/static/`). Schriften kommen aus dem System des Clients (`system-ui` und die Monospace-Systemschrift). Es werden keine Webfonts, Skripte oder Stylesheets von CDNs geladen, es gibt kein Analytics und kein Tracking. Übersetzungen, Fachbegriffe und Erklärungen stammen aus den mitgelieferten Inhalten; es gibt keine externen APIs und keine KI-Dienste. Der Service Worker bearbeitet nur Anfragen an den eigenen Ursprung. Das wird automatisiert geprüft: `tests/test_offline_resources.py` kontrolliert die gerenderten Seiten, die statischen Dateien und die Templates auf fremde Adressen; `tests/e2e/test_offline.py` zeichnet im Browser alle Anfragen eines Lerndurchlaufs auf und verlangt, dass keine an einen anderen Host geht.

**Wann Internet nötig ist.** Nur außerhalb des Lernbetriebs:

| Vorgang | Externe Verbindung | Ohne Internet |
|---|---|---|
| Installation | Paketquellen der Distribution (`apt`), PyPI für die Python-Abhängigkeiten (`pip`), GitHub für den Quellcode | Quellcode als Checkout mitbringen; `pip` braucht einen lokalen Paketspiegel oder vorab geladene Wheels (nicht Teil des Trainers, nicht geprüft) |
| `sudo lpic3ctl --upgrade` | GitHub (Tags und Quellcode) | `--upgrade --source PFAD` mit lokalem Checkout oder `LPIC3_UPGRADE_REMOTE` auf einen eigenen Git-Spiegel |
| `lpic3ctl version --remote` | GitHub (neuestes Release) | `lpic3ctl --version` arbeitet offline |
| Docker-Build | Docker Hub (Basis-Image) und PyPI | nicht vorgesehen |
| Links in der Oberfläche | Prüfungsziele beim LPI, Originalquellen von Zusatzfragen, Herstellerdokumentation in LABs | öffnen im Browser des Lernenden, nie vom Server; ohne Internet bleiben sie ohne Ziel, der Lernbetrieb ist nicht betroffen |

Lernende brauchen nur den Server im LAN. Einmal geladene Seiten bleiben über den Service Worker auch ohne Verbindung zum Server lesbar (Abschnitt *Offline-Verhalten* in `docs/architektur.md`). Ein Betrieb in einem vollständig abgeschotteten Netz nach vorheriger Online-Installation wurde nicht gesondert durchgespielt; die Tests belegen, dass die Anwendung keine fremden Adressen anspricht.

**Mindeststandard im LAN.**

- Dienst über `LPIC3_HOST` an die LAN-Adresse oder `0.0.0.0` binden (Abschnitt *Zugriff aus dem lokalen Netzwerk*) oder, empfohlen, bei `127.0.0.1` lassen und einen Reverse Proxy mit HTTPS auf demselben Rechner davorschalten.
- Ist eine Firewall aktiv, den Port nur für das lokale Netz freigeben.
- Unverschlüsseltes HTTP nur in einem vertrauenswürdigen, abgeschotteten Netz und nur für Tests oder kurze Übungen. Für den dauerhaften Mehrbenutzerbetrieb HTTPS auch im LAN; ein Zertifikat einer eigenen CA oder ein selbstsigniertes Zertifikat reicht, wenn die Clients es kennen.
- Regelmäßig `sudo lpic3ctl backup` (Abschnitt *Backup und Restore*).

**Mindeststandard im Internet.**

- Dienst bleibt bei `LPIC3_HOST=127.0.0.1`. Nach außen zeigt nur der Reverse Proxy mit HTTPS (Ports 80 und 443), nie Port 8000.
- `LPIC3_SECURE_COOKIES=true` in `/etc/lpic3-trainer/lpic3-trainer.env`.
- Zertifikate nach Wahl des Administrators (Let's Encrypt, eigene CA, gekauftes Zertifikat). Der Trainer verwaltet keine Zertifikate und spricht selbst kein TLS.
- Firewall: nur 80/443 und der Administrationszugang offen. Betriebssystem aktuell halten, Backups einrichten.
- Monitoring, Fail2ban oder vergleichbare Schutzmechanismen sind Sache des Administrators und nicht vorgeschrieben. Anschlusspunkte des Trainers: `/health`, `lpic3ctl --status` mit Exit-Codes und die Logs in journald (`lpic3ctl logs`).

**Reverse Proxy frei wählbar.** Der Trainer schreibt keine Proxy-Software vor; nginx ist nur das Beispiel im nächsten Abschnitt. Apache httpd, Caddy, HAProxy, Traefik oder ein anderer HTTP-Reverse-Proxy sind geeignet, wenn er

- Anfragen per HTTP/1.1 an `http://127.0.0.1:8000` weiterreicht,
- `Host` oder `X-Forwarded-Host` sowie `X-Forwarded-Proto` setzt (sonst lehnt die Origin-Prüfung Formulare ab),
- Uploads von mindestens 5 MB zulässt (Fragenimport; die Anwendung begrenzt auf 5 MB).

WebSockets oder besondere Timeouts braucht die Anwendung nicht.

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

Standardweg: auf das neueste stabile Release aktualisieren.

```bash
sudo lpic3ctl --upgrade
```

`--upgrade` fragt die Tags des Repositorys ab und nimmt das höchste `vX.Y.Z`. Vorabversionen (`v1.0.0-rc1`) und der Branch `main` werden nie automatisch installiert. Ist das Release bereits installiert, meldet der Befehl „Bereits aktuell“ und ändert nichts, insbesondere kein Neustart (Exit 0). Ist der installierte Stand neuer (Entwicklungsinstallation aus einem Checkout), gibt es kein Downgrade. Trägt eine Entwicklungsinstallation dieselbe Versionsnummer wie das Release, aber einen anderen Commit, einen Branch oder lokale Änderungen, meldet der Befehl das als Entwicklungsstand und ersetzt nichts; das Release lässt sich dann bewusst mit `--upgrade --source` aus einem Checkout des Tags installieren. Ohne Netz oder ohne Zugriff auf GitHub bricht der Befehl vor jeder Änderung mit Exit 1 ab.

Manueller Weg für Entwicklungsstände, Offline-Server oder eine ältere Version: aus einem lokalen Checkout upgraden.

```bash
cd ~/LPIC-3-Trainer
git fetch --tags
git checkout v0.0.5        # gewünschter Stand, siehe git tag
sudo lpic3ctl --upgrade --source "$PWD"
```

Ablauf in beiden Fällen:

1. zeigt die installierte Version,
2. baut die neue Version mit eigenem Prüf-venv neben der laufenden auf (`/opt/lpic3-trainer/app.new`), prüft Abhängigkeiten, Import und die vorhandene Konfiguration mit dem neuen Code; schlägt das fehl, läuft der Dienst unverändert weiter (Exit 2 bei unpassender Konfiguration, sonst 1),
3. sichert Datenbank und Konfiguration nach `/var/lib/lpic3-trainer/backups/`,
4. stoppt den Dienst nur, wenn er lief, verschiebt die alte Version nach `/opt/lpic3-trainer/app.previous` und tauscht die neue ein, erneuert das venv,
5. führt Datenbankmigrationen aus und importiert die mitgelieferten Inhalte,
6. aktualisiert die systemd-Unit und stellt den vorherigen Dienstzustand wieder her: ein laufender Dienst wird neu gestartet, ein gestoppter bleibt gestoppt, Autostart bleibt unverändert.

Die Konfiguration wird nicht überschrieben (siehe *Konfiguration nach dem Upgrade vergleichen*). Schlägt ein Schritt nach dem Tausch fehl, wird die vorherige Version automatisch zurückgespielt. Jede Installation schreibt `/opt/lpic3-trainer/app/BUILD` mit Version, Commit, Branch oder Release, `dirty`, Quelle und Zeitpunkt; `lpic3ctl --version` liest nur diese Datei.

Zurück zur vorherigen Programmversion:

```bash
sudo lpic3ctl rollback                       # nur Programmdateien, wenn das Schema unverändert ist
sudo lpic3ctl rollback --restore ARCHIV      # Programmdateien und Datenbank aus der Sicherung von vor dem Upgrade
```

Hat das Upgrade das Datenbankschema geändert, verweigert `rollback` ohne `--restore` die Ausführung und nennt das passende Archiv unter `/var/lib/lpic3-trainer/backups/`. Die vorherige Version würde sonst mit einem unbekannten Schema nicht mehr starten. Einzelheiten in `docs/administration.md`.

### Konfiguration nach dem Upgrade vergleichen

Die zentrale Konfiguration bleibt `/etc/lpic3-trainer/lpic3-trainer.env`. Ein Upgrade verändert diese Datei nicht. Das ist beabsichtigt: Keine lokale Einstellung wird ungeprüft überschrieben, und die Datei bleibt vollständig unter Kontrolle des Administrators. Neue Konfigurationsvariablen einer Version, zum Beispiel `LPIC3_PASSWORD_MIN_LENGTH` und `LPIC3_PASSWORD_MAX_LENGTH` seit 0.0.4, erscheinen deshalb nicht automatisch in einer bestehenden Datei. Fehlt eine Variable, verwendet die Anwendung ihren eingebauten Standardwert; mit einer älteren Datei läuft sie also weiter.

Vergleiche nach jedem Upgrade die Beispielkonfiguration der installierten Version mit deiner Datei. Die Beispieldatei wird bei jeder Installation mit dem Programm nach `/opt/lpic3-trainer/app/deploy/` kopiert und passt damit immer zur installierten Version:

```bash
sudo diff -u /etc/lpic3-trainer/lpic3-trainer.env /opt/lpic3-trainer/app/deploy/lpic3-trainer.env.example
```

Alternativ die Fassung des installierten Release-Tags von GitHub laden; `lpic3ctl --version` zeigt den Tag. Nimm den Tag, nicht `main`: Dort können bereits Optionen eines noch nicht veröffentlichten Stands stehen, die die installierte Version nicht kennt. Beispiel für v0.0.5:

```bash
curl -fsSL https://raw.githubusercontent.com/richtertoralf/LPIC-3-Trainer/v0.0.5/deploy/lpic3-trainer.env.example -o /tmp/lpic3-trainer.env.example
sudo diff -u /etc/lpic3-trainer/lpic3-trainer.env /tmp/lpic3-trainer.env.example
```

Unterschiede bei Werten, die du bewusst gesetzt hast (`LPIC3_HOST`, Port, Datenverzeichnis), sind normal. Achte auf Variablen, die nur in der Beispieldatei vorkommen: Diese Einstellungen trägst du bei Bedarf von Hand mit dem gewünschten Wert in deine Datei ein. Es gibt keine automatische Übernahme und keine Konfigurationsmigration. Danach den Dienst neu starten und die Konfiguration prüfen:

```bash
sudo lpic3ctl --restart
sudo lpic3ctl --check
```

`--check` meldet ungültige Werte, zum Beispiel eine Passwortlänge außerhalb des erlaubten Bereichs, unter *Konfigurationswerte* und endet dann mit Exitcode 1 (siehe [Prüfung und Fehlerdiagnose](#9-prüfung-und-fehlerdiagnose)).

Version prüfen:

```bash
lpic3ctl --version            # z. B. LPIC-3 Trainer 0.0.5 (commit 1a2b3c4, release v0.0.5, installiert 2026-11-06T16:00:00+01:00)
lpic3ctl version --remote     # zusätzlich das neueste stabile Release auf GitHub
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

Konfiguration: Es gibt keine Konfigurationsdatei. `deploy/Dockerfile` setzt `LPIC3_HOST=0.0.0.0`, `LPIC3_PORT=8000` und `LPIC3_DATA_DIR`; `deploy/docker-compose.yml` setzt `LPIC3_SECURE_COOKIES` und `LPIC3_SESSION_HOURS`. Weitere Variablen aus [Einstellungen](#3-einstellungen) unter `environment` ergänzen und den Container neu erstellen (`docker compose -f deploy/docker-compose.yml up -d`).

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
sudo lpic3ctl --uninstall            # Dienst und Programmdateien entfernen, Konfiguration und Daten bleiben
sudo lpic3ctl --uninstall --purge    # zusätzlich Konfiguration, Daten und Dienstkonto löschen, mit Rückfrage
sudo lpic3ctl --uninstall --purge --yes   # ohne Rückfrage (Skripte)
```

Gleichwertig: `lpic3ctl uninstall` und `lpic3ctl purge [--yes]`.
