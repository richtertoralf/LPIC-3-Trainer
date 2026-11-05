# LPIC-3 Trainer

Vorbereitung auf die **LPIC-3-Prüfungen** für Linux-Kenner, deren Englisch für die Prüfung noch nicht ausreicht.

Die App verbindet gezielte LPIC-3-Prüfungsvorbereitung mit individuellem technischem Englischtraining. Sie läuft im Browser auf eigener Infrastruktur und benötigt keine Cloud, keine externen Dienste und keine KI.

## Zielgruppe

Die App richtet sich an deutschsprachige Linux-Anwender mit vorhandenen Linux-Kenntnissen, deren Englisch für die LPIC-3-Prüfungen nicht ausreicht.

Sie kann allein oder gemeinsam genutzt werden. Linux-Vereine, Lerngruppen, Privatpersonen und Bildungseinrichtungen können sie auf einem eigenen Server betreiben und ihren Mitgliedern und Teilnehmern bereitstellen.

## Zweck

Die LPIC-3-Prüfungen werden auf Englisch abgelegt. Englischsprachige Lernmaterialien gibt es viele. Diese App ist keine weitere Fragensammlung und kein Englischkurs.

Ein Lernender kann den technischen Zusammenhang verstehen und trotzdem an der englischen Frage scheitern. Die App erkennt diesen Unterschied und reagiert gezielt darauf.

Das Lernprinzip:

- Die Prüfungsfragen bleiben auf Englisch.
- Deutsche Übersetzungen und Erklärungen sind bei Bedarf verfügbar.
- Technisches Fachenglisch wird direkt an den Prüfungsfragen gelernt.
- Vorhandenes Linux-Wissen wird berücksichtigt.

Ziel ist das sichere, selbstständige Verstehen und Beantworten englischer LPIC-3-Prüfungsfragen.

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
- Praktische Übungen für das eigene Linux-Lab (Anleitungen und Selbstkontrolle, keine Ausführung durch die App)
- Import eigener Prüfungsfragen
- Persönlicher Lernfortschritt je Nutzer
- Lernende wählen ihre LPIC-3-Module selbst
- Betreuer stellen Fragen bereit und begleiten Lerngruppen
- Anmeldung offen oder mit Freigabe durch einen Betreuer oder Administrator
- Nutzung auch offline: einmal geladene Lerninhalte bleiben im Browser verfügbar

## Abgrenzung

- Kein allgemeiner Englischkurs.
- Keine vollständige Übersetzung der LPIC-3-Prüfung ins Deutsche.
- Keine KI-Abhängigkeit.
- Keine Wiederholung bereits beherrschter Linux-Grundlagen.

## Status

Erste Entwicklungsversion (0.0.x), noch keine stabile Produktionsversion. Die technischen Vorgaben stehen in [AGENTS.md](AGENTS.md).

## Installation und Dokumentation

- [Installation](docs/installation.md): native Installation mit systemd (Standardweg), Konfiguration, Update, Docker Compose (optional); [Installationstest](docs/installationstest.md) mit Ergebnissen und Testplan
- [Administration](docs/administration.md): Benutzer, Gruppen, Fragenimport und Freigabe, Backup und Restore, `lpic3ctl`
- [Bedienung](docs/bedienung.md), [Architektur](docs/architektur.md), [Entwicklung](docs/entwicklung.md), [Entwicklungsstand](docs/stand.md)
- [Über den Autor](docs/ueber-den-autor.md): Motivation, Hintergrund und Bildungsverständnis

## Lizenz

Der Programmcode steht unter der MIT-Lizenz, siehe [LICENSE](LICENSE).

Lerninhalte und importierte Prüfungsfragen sind davon nicht erfasst. Ihre Nutzungsrechte liegen bei den jeweiligen Urhebern. Das Projekt ist unabhängig vom Linux Professional Institute.
