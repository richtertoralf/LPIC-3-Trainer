# Abnahmebericht – Prüfung von Installation, Bedienabläufen und Fragenbestand

Geprüfter Stand: `main`, Commit `37c197b` (4. November 2026). Prüfung am 4. November 2026 auf Ubuntu 24.04 (Entwicklungssystem, kein Root, kein Docker, kein systemd-Zugriff).

## 1. Was tatsächlich ausgeführt wurde

| Prüfung | Art | Ergebnis |
|---|---|---|
| ruff check, pytest Backend (82 Tests), Playwright Chromium (10 Tests) | ausgeführt | alle bestanden, keine JavaScript-Fehler |
| Frischer `git clone` nach `/tmp`, `python3 -m venv`, `pip install -e .`, `lpic3ctl content-sync`, `user create`, `user set-password`, `backup`, `restore`, `check`, `status`, `version`, `serve`, `/health` | ausgeführt (ohne Root, ohne systemd) | funktioniert, zwei Befunde (P1-3, P2-1) |
| Browser-Durchlauf der drei Rollen gegen diesen Server: Registrierung mit Freigabe, Rollenwechsel, Gruppen, Import ohne und mit Herkunft, Freigabe je Gruppe, Entzug, Üben, Kapiteltest, Modulsimulation, Eingangstest, Labs, Vokabeln, Fortschritt, 403-Prüfung aller Verwaltungsseiten, Handy-Breite 390 px | ausgeführt (Playwright-Skript, Screenshots) | funktioniert, Befunde unter P2/P3 |
| Freigabelogik in Modulsimulation, Kapiteltest und Eingangstest vor Freigabe, nach systemweiter Freigabe und nach Entzug; strenge Bewertung von Mehrfachauswahl | ausgeführt (Skript mit Test-Client) | korrekt |
| Statistische Analyse des Fragenbestands (Abdeckung je Ziel, Ähnlichkeit, Übersetzungen, Buchstaben in Erklärungen) | ausgeführt | siehe Abschnitt 4 |
| Native Installation mit `lpic3ctl install`, `upgrade`, `rollback`, `uninstall`, `purge` und systemd | nur automatisierter Test mit Stub-Befehlen und Code-Lesung | nicht auf einem echten System geprüft |
| Docker Compose | nur Code-Lesung | ungeprüft |
| Fachliche Richtigkeit der 245 Projektfragen | Stichprobe von 14 Fragen gelesen, Rest nur durch Importvalidierung | Stichprobe ohne Befund |
| 20 ExamTopics-Fragen | alle gelesen, strittige Punkte gegen Herstellerdokumentation geprüft | siehe Abschnitt 5 |

## 2. Befunde

### P0 – Blockierend

Keine. Installation aus dem Klon, Anmeldung, Datenzugriff und Lernbetrieb funktionieren.

### P1 – Vor Nutzung beheben

**P1-1 Einstieg ins Repository führt nicht zur Installation (Administrator).**
README.md enthält weder einen Link auf `docs/installation.md` noch auf `docs/`; der Status lautet weiter „Planungsphase“. Ein neuer Betreiber findet die Anleitung nur durch Durchsuchen des Repositorys.
Überprüft: `grep -i "install\|docs/" README.md` liefert nichts.
Auswirkung: Der erste Eindruck widerspricht dem Stand; die Installation wird nicht gefunden.
Empfehlung: README um Status und einen Verweis auf `docs/installation.md` ergänzen (Änderung der README ist Entscheidung des Auftraggebers).

**P1-2 Installationsanleitung verweist auf einen veralteten Stand (Administrator).**
`docs/installation.md` empfiehlt `git checkout v0.0.1`. Dieser Tag enthält weder die Migrationen 0002/0003 noch die Freigabeverwaltung und die 245 Fragen. Wer der Anleitung folgt, installiert eine Version ohne die geprüften Funktionen.
Überprüft: `git tag` zeigt nur `v0.0.1`; `docs/installation.md` Zeile 11.
Empfehlung: Neuen Tag (z. B. `v0.0.2`) setzen und die Anleitung darauf beziehen, oder die Anleitung auf `main` umstellen.

**P1-3 Wiederherstellung bei laufendem Server ohne systemd verliert Daten (Administrator).**
`lpic3ctl restore` ersetzt die Datenbankdatei und stoppt den Dienst nur über systemd. Läuft der Server anders (Docker, `lpic3ctl serve` im Vordergrund, Entwicklung), schreibt er danach in die gelöschte alte Datei weiter. Alle Änderungen bis zum nächsten Neustart gehen verloren.
Reproduziert: Server gestartet, `restore --yes`, danach Registrierung `admin1` über den Browser (303, Anmeldung möglich), Server neu gestartet, Anmeldung schlägt mit 400 fehl, `user list` zeigt den Benutzer nicht. `docs/installation.md` empfiehlt für Docker Befehle im laufenden Container (`docker compose … exec lpic3-trainer lpic3ctl backup`); ein Restore auf diesem Weg hätte denselben Effekt.
Empfehlung: `restore` muss einen laufenden Server erkennen (z. B. Health-Endpunkt prüfen) und abbrechen oder zum Stoppen auffordern; Docker-Anleitung auf „Container stoppen, dann restore“ umstellen.

### P2 – Verbesserung

**P2-1 CLI-Befehle scheitern vor dem ersten Start, wenn das Datenverzeichnis fehlt (Administrator, Entwickler).**
`lpic3ctl content-sync`, `migrate`, `user create` und `import` brechen mit „unable to open database file“ ab, solange `LPIC3_DATA_DIR` nicht existiert; nur `serve` und `install` legen es an. `docs/entwicklung.md` beschreibt `content-sync` vor `uvicorn` als Weg.
Reproduziert im frischen Klon. Nach `lpic3ctl serve` funktionieren alle Befehle. Bei der nativen Installation tritt das Problem nicht auf, weil `install` das Verzeichnis anlegt.
Empfehlung: Verzeichnis in `app/migrate.upgrade_database` oder in `migrations/env.py` vor dem Verbinden anlegen.

**P2-2 Administratoren können Benutzer nicht in der Weboberfläche anlegen (Administrator).**
Unter *Verwaltung › Benutzer* gibt es Freigeben, Rolle, Deaktivieren, Passwort zurücksetzen und Löschen, aber kein Formular zum Anlegen. Konten entstehen nur durch Selbstregistrierung oder `lpic3ctl user create` auf der Kommandozeile.
Überprüft im Browser; `app/templates/admin/users.html`.
Auswirkung: Geschlossene Lerngruppen ohne Selbstregistrierung brauchen das Terminal.
Empfehlung: Formular „Benutzer anlegen“ mit Rolle und Startpasswort.

**P2-3 Betreuer sehen alle Benutzer des Systems (Betreuer, Datenschutz).**
*Verwaltung › Benutzer* zeigt Betreuern jede Person mit Status, nicht nur ihre Gruppen; auch *Verwaltung › Import* listet die Importe aller Betreuer (löschen können sie nur eigene).
Überprüft: `app/routers/admin.py`, Funktionen `users()` und `import_form()` filtern nicht nach Rolle.
Empfehlung: Betreuer auf ausstehende Freigaben und eigene Gruppenmitglieder beschränken, Importliste auf eigene Chargen.

**P2-4 Prüfungssimulation lässt sich ohne Rückfrage unbeantwortet abgeben (Lernender).**
„Abgeben“ wertet sofort; mit 0 von 60 Antworten gibt es keine Warnung. Ein Fehlklick beendet die Simulation endgültig.
Überprüft im Browser.
Empfehlung: Bestätigung bei unbeantworteten Fragen.

**P2-5 Herkunftsangaben: Prüfungsnummer und Original-URL nicht im Datenmodell (alle Rollen).**
Gespeichert und angezeigt werden Quelle, Prüfungsgeneration, Rechtestatus und Lizenztext. Die vollständige Prüfungsnummer (z. B. `305-300`) steht nur im freien Lizenztext, die Original-URL nur in `content/questions/extra/README.md`. Das Feld `author` wird gespeichert, aber nirgends angezeigt.
Überprüft: `app/models.py` (`ImportBatch`), Templates `learn/_source_tag.html`, `admin/releases.html`, `module.html`.
Empfehlung: Felder `exam_code` und `source_url` ergänzen und in Freigabe- und Lernansicht anzeigen.

**P2-6 Überschneidungen zwischen Grundbestand und Zusatzfragen (Lernender).**
`305-353.3-02` (Projekt) und `305-examtopics-screenshot-10` fragen beide nach `/var/lib/cloud/`; `305-353.4-01` und `305-examtopics-screenshot-01` prüfen beide `vagrant init`; `305-351.4-01` und `305-examtopics-screenshot-06` beide `virsh list`; `300-301.3-01` und `300-examtopics-screenshot-07` beide `smbstatus`. Innerhalb des Grundbestands gibt es keine identischen Fragen (Ähnlichkeitsanalyse über alle Fragetexte).
Auswirkung: Bei freigegebenen Zusatzfragen erscheinen Themen doppelt; kein Fehler in der Bewertung.
Empfehlung: Vor der Erweiterung auf 60 Zusatzfragen je Modul Dubletten gegen den Grundbestand prüfen (Analyse im Import oder in den Tests).

**P2-7 Fragenbestand enthält kaum Mehrfachauswahl (Lernender).**
Nur 3 von 245 Projektfragen sind Mehrfachauswahl, 242 haben genau eine richtige Antwort mit meist vier Optionen. Die echte Prüfung verwendet häufig fünf Optionen und „Choose two/three“.
Überprüft: Analyse der Inhaltsdateien.
Empfehlung: Beim Ausbau Mehrfachauswahl und fünf Optionen gezielt ergänzen.

**P2-8 Zwei ExamTopics-Fragen sind inhaltlich unsicher (Lernender, Betreuer).**
Siehe Abschnitt 5: `305-examtopics-screenshot-03` (Vagrant und Docker) und `300-examtopics-screenshot-08` (Zugriff beschränken). Beide sollten vor einer Freigabe entweder umformuliert oder deaktiviert werden.

### P3 – Später

- Nach der Anmeldung landen Administratoren und Betreuer wie Lernende auf der Modulauswahl; die Verwaltung ist nur über die Navigation erreichbar.
- Der Eingangstest kann je Modul nur einmal abgelegt werden; eine Wiederholung ist nicht vorgesehen.
- Zurückgesetzte Passwörter werden als Hinweistext angezeigt; es gibt keinen Zwang zur Änderung beim nächsten Login.
- Die Vokabelmarkierung erkennt nur wörtliche Treffer, keine Wortformen.
- Keine Fragen vom Typ „Lückentext“ (in der echten Prüfung vorhanden).
- Der Begriff „Zusatzfrage“ wird auch für eigene Fragen eines Betreuers verwendet; „Importierte Frage“ wäre klarer.
- Wer nach einem per CLI angelegten Administrator als Erster über den Browser registriert, wird Lernender. Die Anleitung sagt nur „das erste Konto wird Administrator“.

## 3. Bewertung je Rolle

**Administrator.** Installation (Phase 1) aus dem Klon ohne systemd nachvollzogen; Anleitung und Code stimmen überein (Befehle, Verzeichnisse, Umgebungsvariablen, erster Administrator per Registrierung oder CLI, Passwort zurücksetzen per `lpic3ctl user set-password` auf der Kommandozeile und für andere Konten in der Weboberfläche). Voraussetzungen, Distributionen und Aufruf nach der Installation sind in `docs/installation.md` beschrieben; nicht erwähnt ist, dass `pip` während der Installation Internetzugang braucht. Einschränkungen: P1-1, P1-2, P1-3, P2-1, P2-2. Alle übrigen Verwaltungsaufgaben (Freigabe von Konten, Rollen, Gruppen, Import, Freigaben, Einstellungen, Statistik) sind ohne Terminal bedienbar.

**Betreuer.** Anmeldung, Gruppen anlegen, Beitritte freigeben, Mitglieder hinzufügen, Import mit Pflichtfeldern (Abweisung ohne Quelle und Generation beobachtet), Freigabe und Entzug je Gruppe, Lernstand der Mitglieder: alles im Browser bedienbar. Systemweite Freigabe ist korrekt nicht verfügbar; fremde Gruppen antworten mit 403, fremde Importe werden nicht angezeigt. Einschränkung: P2-3.

**Lernender.** Registrierung mit Freigabe, Modulauswahl, Gruppenbeitritt, Üben mit Übersetzung und Begriffsmarkierung, Auswertung mit Erklärung, Vokabeln, Labs, Kapiteltest, Modulsimulation, Eingangstest, Fortschritt: vollständig im Browser, auch bei 390 px Breite ohne horizontales Scrollen. Alle Verwaltungsseiten antworten mit 403, fremde Prüfungen mit 404; die Prüfung erfolgt serverseitig (FastAPI-Abhängigkeiten `require_supervisor` und `require_admin`, Tests in `tests/test_auth_roles.py` und `tests/test_release.py`).

## 4. Fragenbestand

- 245 Projektfragen (300: 62, 303: 62, 305: 60, 306: 61), 20 ExamTopics-Zusatzfragen (je 10 für 300 und 305).
- Alle Fragen sind einem Prüfungsziel der Generation 3.0 zugeordnet; jedes Ziel hat mindestens eine Frage, die Verteilung entspricht grob dem Gewicht (niedrigste Abdeckung: 334.2 mit 3 Fragen bei Gewicht 4, 363.2 mit 7 bei Gewicht 8).
- Alle Fragen haben eine Übersetzung von Frage und Antworten sowie eine deutsche Erklärung; jede Frage trifft Glossarbegriffe.
- Bewertung: Einzelauswahl und Mehrfachauswahl wurden mit vollständig richtiger, teilweiser und gemischter Auswahl geprüft; nur die vollständig richtige Auswahl zählt (wie in der Prüfung).
- Eindeutigkeit: Die Importvalidierung erzwingt genau eine richtige Antwort bei Einzelauswahl und mindestens zwei bei Mehrfachauswahl. Keine identischen Fragen im Grundbestand; Überschneidungen mit den Zusatzfragen siehe P2-6.
- Fachliche Richtigkeit: Stichprobe von 14 Projektfragen ohne Befund. Eine vollständige fachliche Zweitprüfung der 245 Fragen hat nicht stattgefunden und sollte vor einem Einsatz mit Prüfungsanspruch durch eine zweite Person erfolgen.
- Für einen ersten Lernbetrieb ist der Bestand ausreichend. Eine Modulsimulation mit 60 Fragen zieht aber fast den gesamten Bestand; eine zweite Simulation enthält weitgehend dieselben Fragen.

## 5. Bewertung der 20 ExamTopics-Fragen

Herkunft: ExamTopics-Dumps zu 300-300 und 305-300, Nutzungsrechte nicht geklärt (siehe `content/questions/extra/README.md`). Alle Fragen sind unveröffentlicht importiert.

| Frage | Bewertung | Begründung |
|---|---|---|
| 300-01 Raw Printing | richtig (E) | Beim Raw-Druck rendert der Client-Treiber, Samba reicht an CUPS weiter (Samba-Wiki „Setting up Samba as a Print Server“, CUPS-Queue im Raw-Modus). |
| 300-02 force directory mode = 0555, Client 0750 | richtig (0755), Dump sagt 0555 | smb.conf(5): `directory mask` wird per UND angewendet, danach `force directory mode` per ODER. 0750 UND 0755 = 0750, ODER 0555 = 0755. Der Dump ist hier falsch. |
| 300-03 msdfs root = yes | richtig | smb.conf(5), Parameter `msdfs root`. |
| 300-04 hide unreadable = yes | richtig | smb.conf(5), Parameter `hide unreadable`. |
| 300-05 [printers] fehlende Zeile `printable = yes` | richtig, Beispiel korrigiert | Der Screenshot zeigte `[homes]`; die Korrektur ist in der Erklärung vermerkt. |
| 300-06 [homes] browseable = no | richtig (D, E) | smb.conf(5), Abschnitt [homes]: Die automatisch erzeugte Home-Freigabe erbt `browseable` aus [global] und bleibt sichtbar; nur „homes“ selbst wird versteckt. UNC-Zugriff funktioniert. |
| 300-07 smbstatus-Ausgabe | richtig, Antwortliste verändert | Im Dump fehlte `smbstatus` unter den Antworten; die Datei ergänzt es. Keine unveränderte Übernahme, in der Erklärung vermerkt. |
| 300-08 Zugriff beschränken: valid users, write list | **unsicher** | `valid users` beschränkt den Zugriff; `write list` erweitert Schreibrechte auf einer schreibgeschützten Freigabe und beschränkt nicht den Zugriff. Die Antwortoptionen bieten keine zweite saubere Beschränkung (z. B. `hosts allow`). Nicht als sichere Vorbereitung verwenden, vor Freigabe umformulieren oder deaktivieren. |
| 300-09 create mask 711, force create mode 750, Datei 777 → 751 | richtig | smb.conf(5): (0777 UND 0711) ODER 0750 = 0751. |
| 300-10 Backends smbpasswd, ldapsam | richtig | smb.conf(5), Parameter `passdb backend` (smbpasswd, tdbsam, ldapsam). |
| 305-01 vagrant init | richtig (C) | Vagrant-Dokumentation `vagrant init`: erzeugt ein Vagrantfile. |
| 305-02 dom0_mem im Bootloader | richtig (A) | Xen-Dokumentation: `dom0_mem` ist ein Startparameter des Hypervisors (Xen command line), gesetzt in der GRUB-Xen-Zeile. |
| 305-03 Vagrant und Docker, drei Antworten | **unsicher** | A (Verzeichnisse teilen) und C (Basis-Images laden) sind belegt. D („Änderungen an einem Basis-Image anwenden“) ist Auslegungssache: Docker baut Schichten über ein Basis-Image, Vagrant provisioniert eine Box, ändert das Box-Image aber nicht. Die Datei kennzeichnet D als vorläufig. Nicht als sichere Vorbereitung verwenden. |
| 305-04 Standard-Provider VirtualBox | akzeptabel | Vagrant-Dokumentation „Basic Provider Usage“: Auswahl nach `--provider`, `VAGRANT_DEFAULT_PROVIDER`, Vagrantfile, dann installierte Provider mit Priorität; VirtualBox ist der mitgelieferte Provider und ohne weitere Plugins die Vorgabe. Die Erklärung weist auf die Abhängigkeit hin. |
| 305-05 IaaS-Instanzen aus Images | richtig (B) | Allgemeine IaaS-Praxis, deckt sich mit Prüfungsziel 353.1. |
| 305-06 virsh list | richtig (C) | virsh(1): `list` zeigt laufende Domänen, `--all` auch gestoppte. |
| 305-07 cloud-init-Zweck | richtig (E) | cloud-init-Dokumentation: Initialisierung einer Instanz aus einem generischen Image. |
| 305-08 packer inspect | richtig (E) | Packer-Dokumentation `packer inspect`: zeigt die Bestandteile eines Templates. |
| 305-09 Capabilities | akzeptabel (E) | capabilities(7): Aufteilung der Root-Rechte; Container entziehen Capabilities, um Aktionen zu verhindern. Die Formulierung „infringe the container“ ist unscharf, die übrigen Optionen sind klar falsch. |
| 305-10 /var/lib/cloud/ | richtig (A) | cloud-init-Dokumentation, Verzeichnislayout. |

Quellen: smb.conf(5) (z. B. https://manpages.ubuntu.com/manpages/jammy/man5/smb.conf.5.html), Vagrant https://developer.hashicorp.com/vagrant/docs/providers/basic_usage und https://developer.hashicorp.com/vagrant/docs/cli/init, Packer-CLI-Dokumentation, cloud-init-Dokumentation, virsh(1), capabilities(7).

## 6. Herkunftsangaben

| Angabe | Datenmodell | Verwaltung (Freigaben/Import) | Lernansicht |
|---|---|---|---|
| Quelle (`source`) | ja | ja | ja |
| Prüfungsgeneration (`exam_version`) | ja | ja | ja |
| Rechtestatus (`rights`) | ja | ja | ja |
| Lizenz-/Hinweistext (`license`) | ja | Freigaben: ja (Kleindruck); Import: ja | ja |
| Vollständige Prüfungsnummer (z. B. 305-300) | nein, nur im Lizenztext | nur im Lizenztext | nur im Lizenztext |
| Original-URL | nein, nur in `content/questions/extra/README.md` | nein | nein |
| Autor (`author`) | ja | nein | nein |
| Importierende Person, Datum, Datei | ja | ja | nein |
| Trennung Projektfragen / externe Fragen | ja (`bundled`, `supplementary`, `released`) | ja | ja (Kennzeichnung „Zusatzfrage“) |

Fehlend: Prüfungsnummer und URL als eigene Felder, Anzeige des Autors (P2-5).

## 7. Behebungsstatus (Version 0.0.2, 4. November 2026)

| Befund | Status | Umsetzung |
|---|---|---|
| P1-1 README ohne Installationsverweis | behoben | README: Status „Erste Entwicklungsversion“ und Abschnitt „Installation und Dokumentation“ mit Verweisen auf `docs/`. AGENTS.md und CLAUDE.md unverändert. |
| P1-2 Anleitung verweist auf v0.0.1 | behoben | Version 0.0.2, Tag `v0.0.2` nach dem Merge; `docs/installation.md` beschreibt den vollständigen Ablauf (Checkout, Installation, Status, Erstadministrator, Browserzugriff, Konfiguration, Update, Backup/Restore). |
| P1-3 Restore bei laufendem Server | behoben | `restore` prüft den Dienstzustand: systemd-Dienst wird gestoppt und wieder gestartet; ein anderer laufender Server (Health-Endpunkt antwortet) führt zum Abbruch mit Exit-Code 2 und klarer Meldung. Sicherheitskopie vor dem Restore, `PRAGMA integrity_check` danach, Health-Check nach dem Start. Regressionstests: Restore bei laufendem Server wird verweigert und verändert nichts; Restore nach Stopp überlebt zwei Neustarts; defektes Archiv wird abgewiesen. Docker-Anleitung: stop, restore, start. |
| P2-1 CLI ohne Datenverzeichnis | behoben | `upgrade_database` legt das Verzeichnis an; Regressionstest ruft `content-sync` auf leerem Verzeichnis. |
| P2-2 Benutzer anlegen im Web | behoben | Formular „Benutzer anlegen“ unter *Verwaltung › Benutzer* (nur Administrator), Backend- und Browsertest. |
| P2-3 Betreuer sehen alle Benutzer | behoben | Betreuer sehen nur wartende Konten und Mitglieder eigener Gruppen; Importliste nur eigene Chargen. Test. |
| P2-4 Abgabe ohne Rückfrage | behoben | Bestätigung bei unbeantworteten Fragen; automatische Abgabe bei Zeitablauf unverändert. Browsertest. |
| P2-5 Prüfungsnummer und URL | behoben | Felder `exam_code` (Pflichtmuster, muss zum Modul passen; Standard Modul-300) und `source_url` in Migration 0004, Import, Formular, CLI, Freigabe-, Import- und Lernansicht; Autor in der Freigabeansicht. Alle Chargen tragen die Prüfungsnummer. |
| P2-6 Dubletten | teilweise | Import meldet mögliche Dubletten (ab 80 % Textähnlichkeit) in Weboberfläche und CLI. Die vier dokumentierten Überschneidungen bleiben bestehen, weil externe Fragen nicht verändert werden. |
| P2-7 Kaum Mehrfachauswahl | offen | Keine Erweiterung des Fragenpools in diesem Auftrag (Vorgabe). |
| P2-8 Unsichere ExamTopics-Fragen | behoben | Beide Fragen mit `active: false` ausgeschlossen, in Erklärung und `content/questions/extra/README.md` als unsicher gekennzeichnet; keine Antwort wird als bestätigt dargestellt. Test prüft das Kennzeichen. |
| Zusatzbefund: Migrationen mit Fremdschlüsseln | behoben | Beim Prüfen von P2-5 fiel auf, dass SQLite-Tabellenumbauten im Batch-Modus mit aktiven Fremdschlüsseln `ON DELETE`-Aktionen auslösen können. `migrations/env.py` schaltet Fremdschlüssel während Migrationen aus; `content-sync` repariert verlorene Chargenverknüpfungen mitgelieferter Dateien. Upgrade-Test mit Bestandsdaten (0001 → 0004, Gruppenfreigaben bleiben erhalten). |
| P3 | offen | unverändert |

Erneut geprüft nach der Umsetzung: vollständige Backend- und Browsertests, Browser-Durchlauf der drei Rollen (siehe `docs/stand.md`). Verbleibend: native systemd-Installation und Docker nur per Code und Stub-Test geprüft; P2-6 teilweise, P2-7 offen.

## 8. Gesamtbeurteilung

- **Bereit für einen ersten praktischen Test** mit Administrator, Betreuer und Lernendem: ja, auf einem von Hand gestarteten Server (Klon, venv, `lpic3ctl serve`) oder nach einer nativen Installation, sofern P1-2 (Anleitung auf aktuellen Stand) und P1-3 (Restore nur bei gestopptem Server) beachtet werden. Die native systemd-Installation und Docker sind weiterhin nicht auf einem echten System geprüft.
- **Vorher beheben:** P1-1 bis P1-3; für geschlossene Gruppen zusätzlich P2-2.
- **Nur per Code geprüft:** `lpic3ctl install/upgrade/rollback/uninstall/purge` mit systemd (Stub-Test), Docker Compose. **Tatsächlich ausgeführt:** alles Übrige (Abschnitt 1).
- **Fragenbestand:** für einen ersten Lernbetrieb ausreichend; Simulationen wiederholen sich jedoch, Mehrfachauswahl fehlt fast ganz, zwei ExamTopics-Fragen sind unsicher.
- **Vor einer Erweiterung auf 60 Zusatzfragen je Modul:** Dublettenprüfung gegen den Grundbestand (P2-6), Felder für Prüfungsnummer und URL (P2-5), Entscheidung zu den unsicheren Fragen (P2-8), fachliche Zweitprüfung des Grundbestands und eine Kennzeichnung, die unveränderte Dump-Fragen von bearbeiteten (z. B. 300-05, 300-07) unterscheidbar hält.
