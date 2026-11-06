# LPIC-3 Trainer

[![Version 0.0.4](https://img.shields.io/badge/version-0.0.4-blue)](app/__init__.py)
[![Lizenz MIT](https://img.shields.io/badge/Lizenz-MIT-blue)](LICENSE)

**Linux verstehen – LPIC-3-Prüfungsenglisch sicher beherrschen.** Fachenglisch-Training für die LPIC-3-Prüfungen: gezielte Vorbereitung für erfahrene Linux-Administratoren, deren Englisch für die Prüfung noch nicht ausreicht.

**Status:** In Entwicklung – installierbar und in den Kernfunktionen getestet, Installation auf Debian 12/13 und Ubuntu 24.04/26.04 geprüft, noch keine betreute Nutzung mit einer realen Lerngruppe ([Entwicklungsstand](docs/stand.md), [Pilotbetrieb](docs/pilotbetrieb.md)).

Die App verbindet gezielte LPIC-3-Prüfungsvorbereitung mit individuellem technischem Englischtraining. Sie läuft im Browser auf eigener Infrastruktur und benötigt keine Cloud, keine externen Dienste und keine KI.

**Kernaussage:** Der LPIC-3 Trainer unterstützt Linux-Anwender bei der gezielten Vorbereitung auf die englischsprachigen LPIC-3-Zertifizierungsprüfungen. Das Alleinstellungsmerkmal ist das technische Englischtraining direkt an den Prüfungsfragen. Gelernt wird vor allem an Prüfungsfragen, ergänzt um Prüfungssimulationen und praktische LAB-Anregungen, mit denen wesentliche Prüfungsinhalte im eigenen Labor ausprobiert werden. So lässt sich vorhandenes Wissen überprüfen und vertiefen, und Wissenslücken werden sichtbar. Die App kann auch zum selbstständigen Lernen genutzt werden, ersetzt aber keinen vollständigen Linux-Lehrgang.

## Zielgruppe

Die App richtet sich an deutschsprachige Linux-Administratoren mit umfangreichen Linux-Kenntnissen, deren Englisch für die LPIC-3-Prüfungen nicht ausreicht.

LPIC-3 ist die höchste Stufe der distributionsunabhängigen LPI-Zertifizierung und richtet sich an Linux-Profis im Unternehmensumfeld. Das Linux Professional Institute setzt für jede LPIC-3-Zertifizierung eine aktive LPIC-2-Zertifizierung voraus, die ihrerseits eine aktive LPIC-1 verlangt; Zertifizierungen gelten fünf Jahre. Die LPIC-3-Prüfungen werden nur auf Englisch und Japanisch angeboten, nicht auf Deutsch (Stand November 2026, lpi.org). Genau hier setzt die App an: Das Linux-Wissen ist vorhanden, die Prüfungssprache ist die Hürde.

Sie kann allein oder gemeinsam genutzt werden. Linux-Vereine, Lerngruppen, Privatpersonen und Bildungseinrichtungen können sie auf einem eigenen Server betreiben und ihren Mitgliedern und Teilnehmern bereitstellen.

## Zweck

Die LPIC-3-Prüfungen werden auf Englisch abgelegt. Englischsprachige Lernmaterialien gibt es viele. Diese App ist keine weitere Fragensammlung und kein Englischkurs.

Ein Lernender kann den technischen Zusammenhang verstehen und trotzdem an der englischen Frage scheitern: an einem unbekannten Fachbegriff, an einer Formulierung oder am feinen Unterschied zwischen zwei Antwortmöglichkeiten. Die App macht diesen Unterschied zwischen fehlendem Fachwissen und fehlendem Sprachverständnis sichtbar, statt beides zu vermischen.

Das Lernprinzip:

- Die Prüfungsfragen bleiben auf Englisch.
- Deutsche Übersetzungen und Erklärungen sind bei Bedarf verfügbar.
- Technisches Fachenglisch wird direkt an den Prüfungsfragen gelernt.
- Vorhandenes Linux-Wissen wird berücksichtigt.

Ziel ist das sichere, selbstständige Verstehen und Beantworten englischer LPIC-3-Prüfungsfragen.

So greifen die vorhandenen Funktionen dafür ineinander:

- Der **Eingangstest** je Modul läuft ohne Sprachhilfen und ordnet vorhandenes Linux-Wissen den Themen zu; Themen mit „sicher“ lassen sich überspringen.
- Beim **Üben** bleibt die Frage englisch. Übersetzung und markierte Fachbegriffe sind zuschaltbar, die Antwort wird unabhängig davon gewertet. Mit *Begriff merken* wandern unbekannte Fachbegriffe in die persönliche Vokabelliste und werden dort wiederholt; das Glossar erklärt die Begriffe im Prüfungskontext.
- Die **Hilfequote** je Modul und Thema zeigt, wie oft noch deutsche Hilfe nötig war. Sie soll mit der Zeit sinken, denn in der Prüfung gibt es keine Hilfe.
- Die **Prüfungssimulation** stellt die Prüfungssituation nach: englische Fragen, ohne Sprachhilfen, mit Zeitlimit und den Fragetypen der echten Prüfung.
- Betreuer sehen in der **Auswertung je Prüfungsziel** ihrer Gruppe, ob ein Thema fachlich zu vertiefen ist (niedrige Trefferquote) oder ob vor allem das Fachenglisch zu üben ist (richtige Antworten, aber hoher Hilfebedarf).

Abgedeckt werden alle LPIC-3-Prüfungen mit derselben Lernmethode:

- 300: Mixed Environments
- 303: Security
- 305: Virtualization and Containerization
- 306: High Availability and Storage

## Funktionen

- Englische Prüfungsfragen mit zuschaltbaren deutschen Übersetzungen und Erklärungen
- Technisches Englischtraining anhand der Prüfungsfragen
- Kurze Eingangstests zur Berücksichtigung vorhandener Linux-Kenntnisse
- Prüfungssimulationen ohne Sprachhilfen für einzelne Kapitel und ganze Module
- Praktische LAB-Anregungen zu prüfungsrelevanten Themen für das eigene Linux-Lab (Anleitungen und Selbstkontrolle, keine Ausführung durch die App)
- Import eigener Prüfungsfragen
- Persönlicher Lernfortschritt je Nutzer
- Lernende wählen ihre LPIC-3-Module selbst
- Betreuer stellen Fragen bereit und begleiten Lerngruppen
- Anmeldung offen oder mit Freigabe durch einen Betreuer oder Administrator
- Nutzung auch offline: einmal geladene Lerninhalte bleiben im Browser verfügbar

## Abgrenzung

- Kein vollständiger Linux-Lehrgang und keine systematische Fachausbildung: Die App setzt das Fachwissen voraus, das LPI für LPIC-3 erwartet, und hilft, es zu überprüfen, zu festigen und auf Englisch sicher abzurufen.
- Kein interaktiver Kurs mit Lektionen: Gelernt wird an Prüfungsfragen, Erklärungen und LAB-Anregungen, die Reihenfolge wählt jeder selbst. Eigenständige Lernmodule nach didaktischen Regeln sind als spätere Ergänzung denkbar, aber nicht Bestandteil der Anwendung.
- Kein allgemeiner Englischkurs.
- Keine vollständige Übersetzung der LPIC-3-Prüfung ins Deutsche.
- Keine KI-Abhängigkeit.
- Keine Wiederholung bereits beherrschter Linux-Grundlagen.

## Entwicklungsstand

- **Verfügbar:** Üben mit Sprachhilfen, Eingangstest, Prüfungssimulation, Vokabeln, zwölf LAB-Aufgaben mit Anleitung zur eigenen LAB-Umgebung, Lerngruppen mit Auswertung je Prüfungsziel, Fragenimport mit Freigabe, Offline-Nutzung, Installation und Verwaltung mit `lpic3ctl`.
- **Wird erprobt:** Pilotbetrieb mit Administrator, Dozent und Lernenden; bisher nur automatisiert durchgespielt, Plan für eine reale Lerngruppe in [docs/pilotbetrieb.md](docs/pilotbetrieb.md).
- **Bekannte Grenzen:** Version 0.0.x, keine stabile Produktionsversion; LABs fachlich geprüft, aber nicht vollständig in einer Testumgebung durchgespielt; Docker-Betrieb ungetestet; 20 Zusatzfragen aus externen Quellen mit ungeklärten Nutzungsrechten bleiben unveröffentlicht. Einzelheiten in [docs/stand.md](docs/stand.md).

Die technischen Vorgaben stehen in [AGENTS.md](AGENTS.md).

## Erste Schritte

Voraussetzungen: Debian 12/13 oder Ubuntu 24.04/26.04 mit systemd, Python 3.11 oder neuer, Root-Rechte für die Installation.

```sh
sudo apt install git python3 python3-venv
git clone https://github.com/richtertoralf/LPIC-3-Trainer.git
cd LPIC-3-Trainer
git checkout v0.0.4
sudo python3 -m app.cli install
```

Funktionstest: `lpic3ctl --status` zeigt Dienst, Datenbank und die Adresse `http://127.0.0.1:8000/`; das erste im Browser registrierte Konto wird Administrator. Ausführlich: [Installation](docs/installation.md).

## Bedienung und Verwaltung

| Befehl | Zweck |
|---|---|
| `lpic3ctl --help` | alle Verwaltungsbefehle |
| `lpic3ctl --version` | installierte Version mit Commit, Release oder Branch und Installationszeit, ohne Netz |
| `lpic3ctl --status` | Dienst, Autostart, Datenbank, Schema, Health-Check, Zugriffsadressen; Exit 0 auch bei gestopptem Dienst, 1 bei Fehler, 2 bei ungültiger Konfiguration |
| `sudo lpic3ctl --upgrade` | auf das neueste stabile Release (Tag `vX.Y.Z`) aktualisieren, mit Sicherung und Prüfung vor dem Dienststopp; bereits aktuell: keine Änderung |
| `sudo lpic3ctl --upgrade --source PFAD` | aus einem lokalen Checkout aktualisieren (Entwicklungsstand, offline, ältere Version) |
| `sudo lpic3ctl --uninstall` | Dienst und Programm entfernen, Konfiguration und Daten bleiben |
| `sudo lpic3ctl --uninstall --purge` | zusätzlich Konfiguration, Daten und Dienstkonto entfernen, mit Rückfrage |

Die Befehle folgen dem einheitlichen Verwaltungsstandard der RICHTER.PROJECTS-Anwendungen. Die bisherigen Unterbefehle (`lpic3ctl status`, `upgrade`, `backup`, `restore`, `rollback`, `user`, …) bleiben gültig; vollständige Liste in [docs/administration.md](docs/administration.md).

## Installation und Dokumentation

- [Installation](docs/installation.md): native Installation mit systemd (Standardweg), Konfiguration, Update, Docker Compose (optional); [Installationstest](docs/installationstest.md) mit Ergebnissen und Testplan
- [Administration](docs/administration.md): Benutzer, Gruppen, Fragenimport und Freigabe, Backup und Restore, `lpic3ctl`
- [LAB-Umgebung einrichten](docs/lab-umgebung.md): eigene Testumgebung für die praktischen Aufgaben (Empfehlung KVM/QEMU mit libvirt); [LAB-Konzept](docs/lab-konzept.md)
- [Pilotbetrieb](docs/pilotbetrieb.md): Bedienablauf für Administrator, Dozent und Lernende, Plan für eine reale Lerngruppe; [Umsetzungsbericht November 2026](docs/umsetzungsbericht-2026-11.md)
- [Bedienung](docs/bedienung.md), [Architektur](docs/architektur.md), [Entwicklung](docs/entwicklung.md), [Entwicklungsstand](docs/stand.md)
- [Über den Autor](docs/ueber-den-autor.md): Motivation, Hintergrund und Bildungsverständnis

## Lizenz

Der Programmcode steht unter der MIT-Lizenz, siehe [LICENSE](LICENSE).

Lerninhalte und importierte Prüfungsfragen sind davon nicht erfasst. Ihre Nutzungsrechte liegen bei den jeweiligen Urhebern. Das Projekt ist unabhängig vom Linux Professional Institute.

## Mitmachen

- Fehler und Ideen: [Issues](https://github.com/richtertoralf/LPIC-3-Trainer/issues)
- Praxistests: Rückmeldungen aus einer Lerngruppe oder einem Linux-Verein nach dem Ablauf in [docs/pilotbetrieb.md](docs/pilotbetrieb.md)
- Eigene Prüfungsfragen: Format in [content/README.md](content/README.md); nur selbst erstellte oder zulässig lizenzierte Fragen
- Dokumentation und Code: [docs/entwicklung.md](docs/entwicklung.md)
