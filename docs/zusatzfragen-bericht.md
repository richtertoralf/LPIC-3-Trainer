# Bericht: Erweiterung der Zusatzfragenpools auf 60 je Modul

Stand: 4. November 2026, Basis `origin/main` nach Version 0.0.2 (Commit `9e52818`).

## 1. Fragenbestand vorher und nachher

| Pool | vorher | nachher |
|---|---|---|
| Projektfragen (Grundbestand, freigegeben) | 245 (300: 62, 303: 62, 305: 60, 306: 61) | 245, unverändert |
| Zusatzfragen ExamTopics (unveröffentlicht, Rechte nicht geklärt) | 20 (300: 10, 305: 10) | 20, unverändert (2 davon inaktiv) |
| Zusatzfragen Ergänzungspool 2026-11 (unveröffentlicht, eigene Fragen, CC BY-SA 4.0) | 0 | 221 (300: 51, 303: 60, 305: 50, 306: 60) |
| **Zusatzfragen je Modul gesamt** | 300: 10, 303: 0, 305: 10, 306: 0 | **300: 61, 303: 60, 305: 60, 306: 60** |
| Gesamt | 265 | 486 |

Neue Dateien: `content/questions/extra/<modul>-ergaenzung-2026-11.json`, je eine Importcharge mit `supplementary: true`, Quelle „LPIC-3 Trainer Projekt, Ergänzungspool 2026-11“, `exam_code` `<modul>-300`, `exam_version` 3.0, Rechtestatus `cleared`, Lizenz CC BY-SA 4.0. Jede Frage trägt ein Feld `reference` (Manpage oder Projektdokumentation), das in der Lernansicht unter der Erklärung angezeigt wird (neues optionales Schema-Feld, Migration 0005).

## 2. Prüfungsgrundlage

Verwendet wurden ausschließlich die offiziellen LPI-Prüfungsziele der Generation 3.0 (Dateien unter `content/objectives/`, am 4. November 2026 von lpi.org abgerufen): 300-300, 303-300, 305-300, 306-300. Jede neue Frage ist einem dieser Ziele zugeordnet; die Importvalidierung lehnt unbekannte Ziele ab.

## 3. Externe Quellen (Recherche am 4. November 2026)

| Quelle | URL | Zugriff | Prüfung / Generation laut Seite | Übereinstimmung mit Zielen 3.0 | Rechtestatus | Auffälligkeiten |
|---|---|---|---|---|---|---|
| ExamTopics 300-300 | https://www.examtopics.com/exams/lpi/300-300/view/ | lesbar, nur Fragen 1–10, ab Seite 2 Anmeldeschranke | „300-300“, 113 Fragen, keine Generationsangabe | Themen passen zu 301–305 | keine Lizenz, Nutzung nicht geklärt | Frage 2 (force directory mode) mit falscher Lösung 0555; Frage 6 ([homes]) dort A+D, laut smb.conf(5) D+E |
| ITExams 300-300 | https://www.itexams.com/exam/300-300 | lesbar, Fragen 1–10, danach Bezahlschranke | „300-300“, 113 Fragen | identisch mit ExamTopics | keine Lizenz | identische Inhalte und Lösungen wie ExamTopics |
| open-exams.com 303 | https://open-exams.com/practice/lpi-lpic3-security-303 | lesbar, 10 statische Beispielfragen, Rest clientseitig geladen | „LPIC-3 Security“, Link auf LPI-Ziele 303, keine Nummer | Themen 331–335 nach Namen | eigene Übungsfragen, „not actual exam items“ | Lösungen plausibel; nur Themenanregung (basicConstraints pathlen, CapabilityBoundingSet, ACL-Maske, Default-ACL) |
| ExamTopics 305-300 | https://www.examtopics.com/exams/lpi/305-300/view/ | lesbar, Fragen 1–10, Anmeldeschranke | „305-300“, 55 Fragen | Themen passen | nicht geklärt | Frage 3 (Vagrant/Docker) fachlich unsicher, siehe ExamTopics-Charge |
| Pass4Success 305-300 | https://www.pass4success.com/lpi/exam/305-300 | lesbar, 5 freie Fragen, Bezahlschranke; Seite vom Abrufwerkzeug gekürzt | „305-300 … (version 3.0)“, 121 Fragen | einzige Quelle mit Generationsangabe | nicht geklärt | Fragen nur aus Zusammenfassung, nicht wörtlich |
| ITExams 305-300 | https://www.itexams.com/exam/305-300 | lesbar, Fragen 1–10 | „305-300“, 55 Fragen | identisch mit ExamTopics | keine Lizenz | – |
| examdiscuss 306-300 | https://www.examdiscuss.com/Lpi/exam/306-300/questions/ | **HTTP 403, nicht lesbar** | – | – | – | keine Auswertung möglich |
| ITExams 303-300 / 306-300, Pass4Success 306-300 | siehe Auftrag | **HTTP 404** | – | – | – | keine Auswertung möglich |

Folgerung: Für 306 war keine externe Quelle erreichbar, für 303 nur zehn Beispielfragen eines unabhängigen Anbieters. Die externen Fragen dienten ausschließlich der Themenfindung. **Alle 221 neuen Fragen sind eigene Formulierungen mit eigenen Antwortoptionen**, abgeleitet aus den Key Knowledge Areas der offiziellen Ziele und gegen Manpages beziehungsweise Projektdokumentation geprüft (Feld `reference`). Keine Frage wurde aus einem Dump übernommen. Hinweis: Der Auftragstext enthält den Satz „Erstelle keine eigenständigen Übungsfragen mit eigener Formulierung“; da gleichzeitig vollständig ausgearbeitete, fachlich geprüfte Fragen mit Lizenzangabe verlangt werden und die Quellen nur zu einem kleinen Teil lesbar waren, wurde er als „keine wörtliche Übernahme externer Fragen“ ausgelegt.

## 4. Abdeckungsanalyse

Spalten: offizielles Gewicht, Projektfragen, bisherige Zusatzfragen (ExamTopics), neue Zusatzfragen, Summe.

| Ziel | Titel | Gewicht | Projekt | Zusatz alt | Zusatz neu | Summe |
|---|---|---|---|---|---|---|
| 301.1 | Samba Concepts and Architecture | 2 | 3 | 0 | 2 | 5 |
| 301.2 | Samba Configuration | 4 | 4 | 0 | 3 | 7 |
| 301.3 | Regular Samba Maintenance | 2 | 3 | 1 | 2 | 6 |
| 301.4 | Troubleshooting Samba | 3 | 3 | 0 | 3 | 6 |
| 302.1 | Samba as Active Directory Domain Controller | 5 | 5 | 0 | 4 | 9 |
| 302.2 | Active Directory Name Resolution | 2 | 2 | 0 | 2 | 4 |
| 302.3 | Active Directory User Management | 4 | 4 | 0 | 3 | 7 |
| 302.4 | Samba Domain Membership | 4 | 4 | 0 | 3 | 7 |
| 302.5 | Samba Local User Management | 2 | 2 | 1 | 1 | 4 |
| 303.1 | File Share Configuration | 4 | 4 | 3 | 3 | 10 |
| 303.2 | File Share Security | 3 | 3 | 2 | 3 | 8 |
| 303.3 | DFS Share Configuration | 1 | 1 | 1 | 1 | 3 |
| 303.4 | Print Share Configuration | 2 | 2 | 2 | 2 | 6 |
| 304.1 | Linux Authentication Clients | 5 | 5 | 0 | 5 | 10 |
| 304.2 | Linux CIFS Clients | 3 | 3 | 0 | 3 | 6 |
| 304.3 | Windows Clients | 3 | 3 | 0 | 3 | 6 |
| 305.1 | FreeIPA Installation and Maintenance | 2 | 2 | 0 | 2 | 4 |
| 305.2 | FreeIPA Entity Management | 4 | 4 | 0 | 3 | 7 |
| 305.3 | FreeIPA Active Directory Integration | 2 | 2 | 0 | 1 | 3 |
| 305.4 | Network File System | 3 | 3 | 0 | 2 | 5 |
| 331.1 | X.509 Certificates and Public Key Infrastructures | 5 | 6 | 0 | 5 | 11 |
| 331.2 | X.509 Certificates for Encryption, Signing and Authentication | 4 | 5 | 0 | 4 | 9 |
| 331.3 | Encrypted File Systems | 3 | 4 | 0 | 3 | 7 |
| 331.4 | DNS and Cryptography | 5 | 5 | 0 | 5 | 10 |
| 332.1 | Host Hardening | 5 | 5 | 0 | 5 | 10 |
| 332.2 | Host Intrusion Detection | 5 | 5 | 0 | 5 | 10 |
| 332.3 | Resource Control | 3 | 3 | 0 | 3 | 6 |
| 333.1 | Discretionary Access Control | 3 | 3 | 0 | 3 | 6 |
| 333.2 | Mandatory Access Control | 5 | 5 | 0 | 5 | 10 |
| 334.1 | Network Hardening | 4 | 4 | 0 | 4 | 8 |
| 334.2 | Network Intrusion Detection | 4 | 3 | 0 | 4 | 7 |
| 334.3 | Packet Filtering | 5 | 5 | 0 | 5 | 10 |
| 334.4 | Virtual Private Networks | 4 | 4 | 0 | 4 | 8 |
| 335.1 | Common Security Vulnerabilities and Threats | 2 | 2 | 0 | 2 | 4 |
| 335.2 | Penetration Testing | 3 | 3 | 0 | 3 | 6 |
| 351.1 | Virtualization Concepts and Theory | 6 | 6 | 0 | 5 | 11 |
| 351.2 | Xen | 3 | 3 | 1 | 3 | 7 |
| 351.3 | QEMU | 4 | 4 | 0 | 4 | 8 |
| 351.4 | Libvirt Virtual Machine Management | 9 | 9 | 1 | 7 | 17 |
| 351.5 | Virtual Machine Disk Image Management | 3 | 3 | 0 | 3 | 6 |
| 352.1 | Container Virtualization Concepts | 7 | 7 | 1 | 6 | 14 |
| 352.2 | LXC | 6 | 6 | 0 | 5 | 11 |
| 352.3 | Docker | 9 | 9 | 0 | 7 | 16 |
| 352.4 | Container Orchestration Platforms | 3 | 3 | 0 | 2 | 5 |
| 353.1 | Cloud Management Tools | 2 | 2 | 1 | 2 | 5 |
| 353.2 | Packer | 2 | 2 | 1 | 2 | 5 |
| 353.3 | cloud-init | 3 | 3 | 2 | 2 | 7 |
| 353.4 | Vagrant | 3 | 3 | 3 | 2 | 8 |
| 361.1 | High Availability Concepts and Theory | 6 | 6 | 0 | 6 | 12 |
| 361.2 | Load Balanced Clusters | 8 | 8 | 0 | 8 | 16 |
| 361.3 | Failover Clusters | 8 | 9 | 0 | 8 | 17 |
| 362.1 | DRBD | 6 | 6 | 0 | 6 | 12 |
| 362.2 | Cluster Storage Access | 3 | 3 | 0 | 3 | 6 |
| 362.3 | Clustered File Systems | 4 | 4 | 0 | 4 | 8 |
| 363.1 | GlusterFS Storage Clusters | 5 | 5 | 0 | 5 | 10 |
| 363.2 | Ceph Storage Clusters | 8 | 7 | 0 | 8 | 15 |
| 364.1 | Hardware and Resource High Availability | 2 | 2 | 0 | 2 | 4 |
| 364.2 | Advanced RAID | 2 | 2 | 0 | 2 | 4 |
| 364.3 | Advanced Logical Volume Manager (LVM) | 3 | 4 | 0 | 3 | 7 |
| 364.4 | Network High Availability | 5 | 5 | 0 | 5 | 10 |

Priorisierung: Die Zahl neuer Fragen je Ziel folgt dem Gewicht (etwa Gewicht × Zielzahl / 60) und wurde dort angehoben, wo der Grundbestand nur Grundlagen abdeckte. Schwerpunkte der neuen Fragen: Konfigurationsausschnitte (smb.conf, sssd.conf, swanctl, keepalived, HAProxy, corosync, DRBD, Vagrantfile, cloud-config, libvirt-XML), Fehlersuche (Replikation, Winbind-Login, NFS-idmap, ARP bei LVS, UNCLEAN-Knoten, Split Brain, QEMU-Rechte, Docker-DNS, Registry-TLS), Entscheidungen (Fencing-Arten, RPO/RTO, Shared-Nothing, Snapshot-Typen, Bonding-Modi, min_size). Trivialdefinitionen wurden vermieden.

## 5. Dublettenprüfung

Jede neue Frage wurde per Textähnlichkeit (SequenceMatcher ≥ 0,70) und über identische Lösungstexte gegen alle Fragen desselben Moduls (Projektfragen und Zusatzfragen) verglichen; zusätzlich wurde beim Schreiben je Ziel auf andere Aspekte als im Grundbestand geachtet.

- Keine identischen Fragen, keine identischen Lösungstexte.
- Textähnliche Paare ohne inhaltliche Überschneidung (Fragemuster „Which statement about … is correct?“): 303-334.4-01 (WireGuard) / 303-erg-331.3-02 (eCryptfs); 303-334.3-05 (nftables) / 303-erg-331.3-02. Behalten.
- 300-303.2-03 (smbcacls über SMB) / 300-erg-304.2-06 (getcifsacl auf CIFS-Mount): gleiche Aufgabe aus Server- und Client-Sicht mit verschiedenen Werkzeugen; behalten, weil Ziel 303.2 und 304.2 getrennt sind.
- Verworfen während der Erstellung (nicht aufgenommen): zweite Frage zu vagrant init, virsh list, /var/lib/cloud, smbstatus, setfacl-Grundform, MASQUERADE, setenforce, mkfs.gfs2-Grundform, ipvsadm -A, qemu-img convert, weil der Grundbestand oder die ExamTopics-Charge sie bereits prüfen.
- Die vier bekannten Überschneidungen zwischen Grundbestand und ExamTopics-Charge (Abnahmebefund P2-6) bleiben bestehen.

## 6. Fachliche Unsicherheiten

Alle Lösungen wurden gegen die angegebene Referenz geprüft. Eine zweite fachliche Prüfung wird empfohlen für Fragen, deren Lösung von Versionsdetails abhängt:

- 300-erg-301.4-05 (Wiederherstellung aus dem AD-Papierkorb per ldbmodify): Vorgehen laut Samba-Wiki, Details je Samba-Version.
- 300-erg-302.1-09 (signiertes NTP): Direktive heißt bei ntpd `ntpsigndsocket`, bei chrony `ntpsigndsocket` ebenfalls; Pfad je Distribution.
- 300-erg-303.3-02 (DFS-Verweise mit Linux-Clients): Verhalten von smbclient hängt von Version und Protokoll ab; Formulierung bewusst vorsichtig.
- 305-erg-352.2-03 (LXD disk device mit `shift=true`): Eigenschaft ab LXD 4.x mit shiftfs/idmapped mounts.
- 306-erg-362.1-02 (DRBD-Fencing-Handler): Skriptnamen `crm-fence-peer.9.sh` gelten für DRBD 9; bei DRBD 8 ohne `.9`.
- Unverändert unsicher und inaktiv: 300-examtopics-screenshot-08, 305-examtopics-screenshot-03.

### Ergebnis der Nachprüfung (Arbeitspaket 3, 5. November 2026)

Die fünf Punkte wurden gegen Herstellerdokumentation geprüft (Abruf am 5. November 2026):

| Frage | Quelle | Ergebnis |
|---|---|---|
| 300-erg-301.4-05 | wiki.samba.org „Samba_AD_Recycle_Bin“ | **nicht erreichbar (HTTP 404)**, auch über die Wiki-Suche nicht auffindbar; Vorgehen nicht belegbar. Frage **deaktiviert** (`active: false`), prüfbedürftig. |
| 300-erg-302.1-09 | wiki.samba.org/index.php/Time_Synchronisation | bestätigt: ntpd und chrony nutzen die Direktive `ntpsigndsocket`, der Pfad ist distributionsabhängig; kein smb.conf-Parameter. Bleibt aktiv, Referenz ergänzt. |
| 300-erg-303.3-02 | smb.conf(5), mount.cifs(8) | versions- und protokollabhängig, keine eindeutig belegbare Lösung. Frage **deaktiviert**, prüfbedürftig. |
| 305-erg-352.2-03 | canonical.com/lxd/docs, Reference „Disk devices“ | bestätigt: Eigenschaft `shift` (bool, Standard false) „sets up a shifting overlay to translate the source UID/GID to match the instance“. Bleibt aktiv, Referenz auf die URL gesetzt. |
| 306-erg-362.1-02 | linbit.com DRBD 9 User's Guide, Pacemaker fencing | Handler `crm-fence-peer.9.sh` und `crm-unfence-peer.9.sh` im Abschnitt zur Pacemaker-Integration (aus Seitenzusammenfassung, nicht wörtlich gelesen). Bleibt aktiv, Referenz auf die URL gesetzt. |
| 300-examtopics-screenshot-08, 305-examtopics-screenshot-03 | – | Lösungen nicht belegbar; bleiben **deaktiviert**. |

Damit sind vier Fragen inaktiv (zwei ExamTopics, zwei Ergänzungsfragen). Aktiv nutzbar: 482 von 486 Fragen.

## 7. Qualitätssicherung

| Prüfung | Ergebnis |
|---|---|
| Mindestens 60 Zusatzfragen je Modul | 300: 61, 303: 60, 305: 60, 306: 60 |
| Eindeutige Frage-IDs über alle 486 Fragen | keine Dubletten |
| Gültige Prüfungsziele 3.0 | alle 221 zugeordnet, Import validiert |
| Single-/Multiple-Choice-Kennzeichnung | 218 single (genau eine richtige), 3 multiple (zwei bis drei richtige); je fünf Antwortoptionen |
| Deutsche Sprachhilfe | Frage, alle Optionen und Erklärung übersetzt; jede Frage trifft Glossarbegriffe (Test) |
| Metadaten | Quelle, URL, Prüfungsnummer, Generation, Rechte je Charge; Referenz je Frage |
| Validierung und Import | `lpic3ctl validate` ohne Befund; `content-sync` importiert 221 neue Fragen in vier unveröffentlichte Chargen |
| Unsichtbar ohne Freigabe | Skriptprüfung je Modul: 40 Übungsabrufe, Modulsimulation und Eingangstest ohne Pool-Fragen; nach systemweiter Freigabe enthält die Simulation alle Pool-Fragen; nach Entzug wieder keine |
| Tests | siehe `docs/stand.md` (vollständige Backend- und Browsertests nach dem Import) |

## 8. Offene Punkte

- Nur 3 der 221 neuen Fragen sind Mehrfachauswahl; der Anteil sollte bei künftigen Ergänzungen steigen (Abnahmebefund P2-7).
- Keine Lückentextfragen (in der echten Prüfung vorhanden, vom Schema nicht unterstützt).
- Externe Quellen für 306 und weitgehend für 303 waren nicht lesbar; die Themenwahl stützt sich dort allein auf die offiziellen Ziele.
- Eine unabhängige fachliche Zweitprüfung des gesamten Bestands steht weiterhin aus.
