# Zusatzfragen (Fragen aus gesondert gekennzeichneten Quellen)

Dateien in diesem Verzeichnis sind **externe Zusatzquellen**. Sie werden bei `lpic3ctl content-sync` zwar importiert, bleiben aber unveröffentlicht, bis ein Betreuer sie unter *Verwaltung › Freigaben* für eine Lerngruppe oder ein Administrator sie systemweit freigibt. Jede Frage trägt in der Oberfläche die Kennzeichnung „Zusatzfrage“ mit Quelle und Rechtestatus.

Pflichtfelder im Dateikopf:

| Feld | Bedeutung |
|------|-----------|
| `"supplementary": true` | kennzeichnet die mitgelieferte Datei als externe Quelle (unveröffentlicht) |
| `"source"` | Quellenbezeichnung, wie sie Betreuer und Lernende sehen, z. B. `ExamTopics 04.11.2026` |
| `"exam_version"` | Prüfungsgeneration, z. B. `3.0` |
| `"rights"` | `cleared` (Lizenz bekannt), `unknown`, `unverified` (Herkunft bekannt, Nutzungsrechte nicht geklärt) |
| `"license"` | kurzer Hinweistext (max. 255 Zeichen) |

Die mitgelieferten Lerninhalte unter `content/` stehen unter CC BY-SA 4.0. **Dateien in diesem Verzeichnis sind davon ausgenommen**; ihre Nutzungsrechte liegen bei den jeweiligen Urhebern und sind im Feld `license` beschrieben.

## Enthaltene Quellen

### `305-examtopics-2026-11-04.json`

- Quelle: ExamTopics, öffentlich abrufbarer Fragen-Dump zur LPI-Prüfung 305-300 (https://www.examtopics.com/exams/lpi/305-300/view/), abgerufen am 4. November 2026 über Screenshots des Auftraggebers.
- Umfang: zehn Fragen (vagrant init, dom0_mem, Vagrant und Docker, Vagrant-Provider, IaaS-Provisionierung, virsh list, cloud-init, packer inspect, Capabilities, /var/lib/cloud).
- Herkunftsprüfung: Die Frage zu `vagrant init` ist dort „Topic 1 Question 1“; die Frage zu `dom0_mem` erscheint in demselben Dump und in Spiegelseiten (z. B. Pass4Success „Topic 2 Question 42“). Die übrigen Fragen stammen laut Auftraggeber aus Screenshots desselben Dumps. Solche Dumps geben nach eigener Darstellung echte Prüfungsfragen wieder. Das LPI untersagt die Weitergabe von Prüfungsinhalten; die Nutzungsrechte sind daher **nicht geklärt**.
- Fachliche Anmerkung: Bei der Frage „Vagrant as well as Docker (Choose three)“ ist die dritte Antwort (Änderungen an einem Basis-Image) eine Einordnung des Auftraggebers und in der Erklärung als vorläufig gekennzeichnet.
- Deutsche Übersetzungen, Erklärungen und Begriffslisten sind eigene Arbeit des Projekts.
- Nutzung: nur nach Freischaltung durch einen Betreuer, der die Zulässigkeit für seine Gruppe verantwortet.

### `300-examtopics-2026-11-04.json`

- Quelle: ExamTopics, öffentlich abrufbarer Fragen-Dump zur LPI-Prüfung 300-300 (https://www.examtopics.com/exams/lpi/300-300/view/), abgerufen am 4. November 2026 über Screenshots des Auftraggebers.
- Herkunftsprüfung: Beide Fragen finden sich in Spiegelseiten des Dumps, etwa Pass4Success („Topic 1 Question 38“ zu Raw Printing, „Topic 2 Question 33“ zu `force directory mode`) und itexams.com. Nutzungsrechte **nicht geklärt**.
- Umfang: zehn Fragen (Raw Printing, force directory mode, DFS-Freigabe, hide unreadable, [printers]-Freigabe, [homes] mit browseable = no, smbstatus-Ausgabe, Zugriffsbeschränkung, create mask und force create mode, passdb-Backends). Die acht weiteren Fragen stammen laut Auftraggeber aus Screenshots desselben Dumps (Spiegel bei Pass4Success und itexams.com).
- Berichtigungen gegenüber dem Dump, jeweils in der Erklärung vermerkt: Bei der Frage zur `[printers]`-Freigabe zeigte der Screenshot irrtümlich `[homes]`; das Beispiel wurde korrigiert. Bei der Frage zur `smbstatus`-Ausgabe fehlte `smbstatus` im Dump unter den Antworten; die Antwortliste wurde um die fachlich richtige Option ergänzt. Bei `[homes]` mit `browseable = no` wurde die Erklärung nach der smb.conf-Dokumentation präzisiert (die benutzerbezogene Home-Freigabe bleibt sichtbar).
- Abweichung: Für die Frage zu `force directory mode = 0555` nennt der Dump 0555 als Lösung. Nach der Samba-Dokumentation ergibt sich 0755 (directory mask, dann bitweises ODER mit force directory mode). Die Datei markiert 0755 als richtig und erklärt die Abweichung.
- Deutsche Übersetzungen, Erklärungen und Begriffslisten sind eigene Arbeit des Projekts.
