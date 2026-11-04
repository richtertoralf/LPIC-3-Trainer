# Didaktisches Konzept für die Laboraufgaben (LABs)

Stand: 4. November 2026. Dieses Dokument hält die didaktischen Festlegungen des Auftraggebers zu den LABs fest und gleicht sie mit dem tatsächlichen Stand der Anwendung ab. Es ist die Grundlage für die nächste LAB-Überarbeitung; es wurde noch keine Funktion daraus umgesetzt.

## 1. Festlegungen

### 1.1 LAB-Umgebung

- Die LAB-Umgebung richten Lernende beziehungsweise Dozenten eigenständig auf einem Gerät ihrer Wahl ein.
- Empfehlung: Linux mit KVM/QEMU und libvirt, bei Bedarf virtuelle Router, virtuelle Netzwerke und Snapshots. Andere geeignete Virtualisierungsumgebungen bleiben zulässig; die Empfehlung ist keine Vorgabe.
- Die Dokumentation bietet Orientierung (Voraussetzungen, mögliche Architekturen, geeignete Werkzeuge, Sicherheitsaspekte, Funktionsprüfung), liefert aber keine vorgefertigte Umgebung.
- Keine automatische LAB-Provisionierung, keine zusätzliche Infrastruktur, keine zusätzliche Installationsarchitektur.

### 1.2 Fach-LABs

Jede Fach-LAB-Aufgabe soll enthalten:

1. Lernziel und Bezug zum offiziellen LPI-Prüfungsziel.
2. Technische Voraussetzungen.
3. Aufgabenstellung mit ausreichenden Hinweisen, aber ohne vorgeschriebenen vollständigen Lösungsweg. Konkrete Befehle sind Hinweise oder Hilfestellung, nicht der verpflichtende Weg.
4. Geschätzten Zeitbedarf.
5. Überprüfbare Erfolgskriterien.
6. Typische Schwierigkeiten und Hinweise für den Dozenten (getrennt darstellbar).
7. Verweis auf passende Prüfungsfragen beziehungsweise Prüfungsziele.

### 1.3 Lernbereiche und Lernwege

- LAB-Einrichtung, Fach-LABs und Prüfungsfragen sind getrennte Lernbereiche und dürfen in beliebiger Reihenfolge genutzt werden. Die fachliche Verbindung läuft über die offiziellen Prüfungsziele.
- Lernende dürfen mit Fragen beginnen und danach ein LAB bearbeiten, oder umgekehrt.

### 1.4 Einsatz durch Dozenten

- Die Rolle „Betreuer“ übernimmt die Aufgaben des Dozenten (z. B. freiberufliche Dozenten im Auftrag eines Bildungsunternehmens). Keine zusätzliche Rolle.
- Der Dozent bestimmt Unterrichtsablauf, Reihenfolge der Themen und Umfang der Übungen; kein verpflichtender Kursplan.
- Der Dozent kann die LABs zur Unterrichtsvorbereitung durchsehen; Lernende und Dozenten arbeiten mit denselben Aufgaben, Dozentenhinweise dürfen getrennt dargestellt werden.
- Für die Lerngruppe soll nachvollziehbar sein, welche LABs nicht begonnen, in Bearbeitung oder abgeschlossen sind. Keine Benotungs- oder Prüfungsverwaltung.
- Der Dozent soll anhand von Eingangstests, Fragen und Simulationen erkennen, welche Prüfungsziele seine Gruppe beherrscht und welche er vertiefen sollte.

Ziel: fachlich fundierte, flexibel nutzbare Unterstützung für Präsenzunterricht, betreute Lerngruppen und Selbststudium. Keine komplette Lernplattform.

## 2. Abgleich mit dem Stand der Anwendung (Version 0.0.2)

| Festlegung | Stand | Bewertung |
|---|---|---|
| LAB-Umgebung eigenständig, Empfehlung KVM/QEMU/libvirt | Jedes LAB nennt im Feld `environment_de` seine Testumgebung (z. B. „zwei Test-VMs mit Debian 12“). Eine eigene Anleitung zur LAB-Einrichtung gibt es nicht; `docs/bedienung.md` enthält nur den Hinweis, nur Testsysteme zu nutzen. | **offen**: Dokument zur LAB-Einrichtung (Voraussetzungen, Architekturen, Werkzeuge, Sicherheit, Funktionsprüfung) fehlt. |
| Keine automatische Provisionierung | Die App zeigt Anleitungen nur an und führt nichts aus (AGENTS.md, umgesetzt). | erfüllt |
| Lernziel und Bezug zum Prüfungsziel | Felder `goal_de` und `objective`; Anzeige mit Zielcode und Titel. | erfüllt |
| Technische Voraussetzungen | Feld `environment_de`. | erfüllt |
| Aufgabenstellung mit Hinweisen, ohne verpflichtenden Lösungsweg | Die zwölf vorhandenen LABs sind als Schritt-für-Schritt-Anleitungen mit vollständigen Befehlen aufgebaut (`steps` mit `commands`). Die Oberfläche stellt die Befehle als Teil der Anleitung dar, nicht als Hilfestellung. | **offen**: Darstellung („Hinweis“, einklappbar) und Formulierung der Schritte anpassen; eigenständiges Arbeiten in den Vordergrund stellen. |
| Geschätzter Zeitbedarf | Feld `duration_minutes`. | erfüllt |
| Überprüfbare Erfolgskriterien | Selbstkontrollfragen (`checks`) mit aufklappbarer Antwort; keine ausdrücklichen Erfolgskriterien („Ergebnis X muss vorliegen“). | **teilweise**: Feld für Erfolgskriterien ergänzen oder Checks entsprechend umformulieren. |
| Typische Schwierigkeiten und Dozentenhinweise, getrennt dargestellt | nicht vorhanden. | **offen**: optionales Feld (z. B. `instructor_notes_de`), nur für Betreuer und Administratoren sichtbar. |
| Verweis auf passende Prüfungsfragen beziehungsweise Prüfungsziele | Verweis auf das Prüfungsziel vorhanden; von dort führt die Modulübersicht zum Üben je Ziel. Kein direkter Link vom LAB zu den Fragen des Ziels. | **teilweise**: Link „Fragen zu diesem Ziel üben“ auf der LAB-Seite. |
| Getrennte Lernbereiche, beliebige Reihenfolge | LABs, Fragen und Simulationen sind unabhängig erreichbar (Navigation Labs, Module, Vokabeln). | erfüllt |
| Betreuer als Dozent, keine neue Rolle | Rolle Betreuer mit Gruppen, Freigaben, Lernstandsansicht. | erfüllt |
| Dozent bestimmt Ablauf, kein Kursplan | Es gibt keinen Kursplan; Reihenfolge ist frei. | erfüllt |
| LABs zur Vorbereitung durchsehen | Betreuer sehen alle LABs wie Lernende. Dozentenhinweise fehlen (siehe oben). | teilweise |
| LAB-Status der Gruppe (nicht begonnen, in Bearbeitung, abgeschlossen) | Lernende können ein LAB als erledigt markieren (`lab_progress`); die Gruppenansicht zeigt nur die Zahl erledigter Labs je Mitglied. Den Zustand „in Bearbeitung“ gibt es nicht. | **teilweise**: Status „begonnen“ ergänzen und je Gruppe eine LAB-Übersicht (Mitglied × LAB) anzeigen. |
| Dozent erkennt beherrschte und zu vertiefende Prüfungsziele | Die Gruppenansicht zeigt je Mitglied und Modul: geübte Fragen, Trefferquote, Hilfequote, beste Simulation. Eingangstest-Ergebnisse je Thema sind nur dem Lernenden sichtbar; eine Auswertung je Prüfungsziel über die Gruppe fehlt. | **teilweise**: Gruppenauswertung je Thema/Ziel (Trefferquote aus Übungen, Simulationen und Eingangstests) für Betreuer. |

## 3. Vorschlag für die nächste LAB-Überarbeitung

Reihenfolge nach Nutzen für den Unterricht, alle Punkte ohne neue Infrastruktur und ohne neue Rolle:

1. **Dokument `docs/lab-umgebung.md`**: Voraussetzungen (Hardware, Virtualisierung im BIOS), empfohlene Architektur (Host mit KVM/QEMU/libvirt, isoliertes virtuelles Netz, optional virtueller Router, Snapshots vor jedem LAB), geeignete Werkzeuge (virt-manager, virsh, cloud-init-Images, Vagrant als Alternative), Sicherheitsaspekte (keine produktiven Systeme, isolierte Netze, Firewall-Labs nur per Konsole), Funktionsprüfung (Checkliste: VM startet, Netz, Snapshot/Rollback). Hinweis, dass andere Umgebungen zulässig sind.
2. **LAB-Schema erweitern** (rückwärtskompatibel, Migration): optionale Felder `success_criteria_de` (Liste), `instructor_notes_de`, `pitfalls_de`; Befehle in Schritten als einklappbare „Hinweise“ darstellen; Link zu „Fragen zu Ziel X üben“.
3. **LAB-Status**: Zustände „nicht begonnen / begonnen / abgeschlossen“ je Lernendem; Übersicht Mitglied × LAB in der Gruppenansicht für Betreuer.
4. **Gruppenauswertung je Prüfungsziel** für Betreuer aus vorhandenen Daten (Übungen, Simulationen, Eingangstests), ohne Benotung.
5. **Vorhandene zwölf LABs** entsprechend überarbeiten: Aufgabe zuerst, Hinweise danach, Erfolgskriterien ergänzen, Dozentenhinweise ergänzen.

Nicht vorgesehen: automatische Provisionierung, Kurspläne, Benotung, zusätzliche Dienste.
