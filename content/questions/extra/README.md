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
- Herkunftsprüfung: Die Frage zu `vagrant init` ist dort „Topic 1 Question 1“; die Frage zu `dom0_mem` erscheint in demselben Dump und in Spiegelseiten (z. B. Pass4Success „Topic 2 Question 42“). Solche Dumps geben nach eigener Darstellung echte Prüfungsfragen wieder. Das LPI untersagt die Weitergabe von Prüfungsinhalten; die Nutzungsrechte sind daher **nicht geklärt**.
- Deutsche Übersetzungen, Erklärungen und Begriffslisten sind eigene Arbeit des Projekts.
- Nutzung: nur nach Freischaltung durch einen Betreuer, der die Zulässigkeit für seine Gruppe verantwortet.

### `300-examtopics-2026-11-04.json`

- Quelle: ExamTopics, öffentlich abrufbarer Fragen-Dump zur LPI-Prüfung 300-300 (https://www.examtopics.com/exams/lpi/300-300/view/), abgerufen am 4. November 2026 über Screenshots des Auftraggebers.
- Herkunftsprüfung: Beide Fragen finden sich in Spiegelseiten des Dumps, etwa Pass4Success („Topic 1 Question 38“ zu Raw Printing, „Topic 2 Question 33“ zu `force directory mode`) und itexams.com. Nutzungsrechte **nicht geklärt**.
- Abweichung: Für die Frage zu `force directory mode = 0555` nennt der Dump 0555 als Lösung. Nach der Samba-Dokumentation ergibt sich 0755 (directory mask, dann bitweises ODER mit force directory mode). Die Datei markiert 0755 als richtig und erklärt die Abweichung.
- Deutsche Übersetzungen, Erklärungen und Begriffslisten sind eigene Arbeit des Projekts.
