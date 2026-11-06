# Bedienung

Anleitung für Lernende und Betreuer. Die Oberfläche ist deutsch, die Prüfungsfragen sind englisch.

Der Trainer dient der gezielten Vorbereitung auf die englischsprachigen LPIC-3-Prüfungen. Im Mittelpunkt steht das Fachenglisch-Training direkt an den Prüfungsfragen, ergänzt um Prüfungssimulationen und LAB-Anregungen für die eigene Testumgebung. Er setzt Linux-Kenntnisse auf dem Niveau einer aktiven LPIC-2 voraus (Voraussetzung des LPI für jede LPIC-3-Zertifizierung) und ist kein vollständiger Linux-Lehrgang; zum selbstständigen Lernen lässt er sich trotzdem nutzen.

## Konto und Module

1. Unter *Registrieren* ein Konto anlegen. Je nach Einstellung ist es sofort aktiv oder wartet auf Freigabe.
2. Unter *Module* die LPIC-3-Module wählen, auf die du dich vorbereitest: 300, 303, 305, 306. Die Auswahl ist jederzeit änderbar.
3. Die Startseite zeigt je Modul den Stand: geübte Fragen, Trefferquote, Hilfequote, Labs und die beste Simulation.

## Eingangstest

Jedes Modul bietet einmalig einen kurzen Eingangstest ohne Sprachhilfe und ohne Timer. Das Ergebnis je Thema erscheint in der Modulübersicht: „sicher“ bei allen richtig, „üben“ bei weniger als der Hälfte. So überspringst du Themen, die du schon beherrschst.

## Üben

In der Modulübersicht *Üben* für das ganze Modul oder *Üben* neben einem einzelnen Prüfungsziel. Die Frage erscheint auf Englisch.

Fragetypen wie in der echten Prüfung (LPI: „60 multiple-choice and fill-in-the-blank questions“, 90 Minuten):

- **Einfachauswahl**: genau eine Antwort ist richtig (Optionsfelder).
- **Mehrfachauswahl**: die Frage nennt, wie viele Antworten richtig sind („genau 2 Antworten sind richtig“, Kontrollkästchen). Gewertet wird nur die vollständig richtige Auswahl; eine teilweise richtige Antwort zählt als falsch, das Ergebnis zeigt dann, wie viele richtige getroffen und wie viele falsche gewählt wurden.
- **Lückentext (fill in the blank)**: ein Befehl, eine Option oder ein Dateiname wird eingetippt. Verglichen wird wörtlich nach Entfernen überflüssiger Leerzeichen; die Frage sagt, ob Groß- und Kleinschreibung zählt. Nach der Antwort werden alle akzeptierten Schreibweisen gezeigt.

Die Reihenfolge der Antwortmöglichkeiten wird je Lernendem gemischt, damit die Position nichts über die Lösung verrät; Fragen- und Ergebnisseite zeigen dieselbe Reihenfolge.

Sprachhilfen:

- **Übersetzung anzeigen**: deutsche Übersetzung von Frage und Antworten.
- **Fachbegriffe markieren**: bekannte Fachbegriffe werden im Text hervorgehoben. Antippen zeigt Übersetzung und Erklärung. Mit **Begriff merken** landet er in deiner Vokabelliste.
- **Alle Fachbegriffe dieser Frage**: Liste mit „merken“.

Die Nutzung der Hilfe wird gespeichert, verändert aber nicht die Bewertung. Die Hilfequote zeigt dir, wie oft du noch Hilfe brauchst.

Nach *Antwort prüfen* siehst du die richtige Lösung, die deutsche Erklärung und kommst mit *Nächste Frage* weiter. Es werden bevorzugt neue und zuletzt falsch beantwortete Fragen gezeigt. *Überspringen* holt eine andere Frage.

Die Modulübersicht zeigt zu jedem Prüfungsziel eine deutsche Zusammenfassung und die wichtigsten Werkzeuge (aufklappbar).

## Zusatzfragen

Neben den mitgelieferten Projektfragen können Betreuer eigene oder importierte Fragen für ihre Lerngruppe freigeben, Administratoren auch für alle. Solche Fragen erscheinen beim Üben und in Simulationen und sind mit „Zusatzfrage“, Quelle, Prüfungsgeneration und Rechtestatus markiert. Als Lernender siehst du nur freigegebene Fragen. In der Modulübersicht siehst du die freigeschalteten Quellen und kannst mit *Nur Zusatzfragen üben* oder *Ohne Zusatzfragen üben* die Auswahl eingrenzen.

## Vokabeln

*Vokabeln* listet gemerkte Begriffe. *Wiederholen* zeigt Karten: erst der englische Begriff, dann die deutsche Bedeutung; danach *Gewusst* oder *Nochmal*. Gelernte Begriffe lassen sich zurückholen. Das *Glossar* ist durchsuchbar (englisch und deutsch).

## Prüfungssimulation

- *Simulation* in der Modulübersicht: 60 Fragen, 90 Minuten, verteilt nach Themengewicht (bei weniger verfügbaren Fragen entsprechend weniger).
- *Kapiteltest* neben einem Thema: 15 Fragen zum Thema.
- Keine Sprachhilfen, Timer oben rechts, Zähler der beantworteten Fragen unten. Bei Ablauf der Zeit wird automatisch abgegeben.
- Ergebnis: richtig/gesamt, Prozent, Einordnung gegenüber der Bestehensgrenze (etwa 60 %), Ergebnis je Thema und jede Frage mit Lösung. Von dort kannst du jede Frage mit Sprachhilfe öffnen.
- *Alle Ergebnisse* zeigt die Historie.

## Labs

*Labs* ist ein eigener Lernbereich neben Fragen und Simulationen; die Reihenfolge ist frei (erst Fragen, dann LAB, oder umgekehrt, oder im Wechsel).

**LAB-Umgebung.** Die Fach-LABs laufen in deiner eigenen Testumgebung. Die Anleitung *LAB-Umgebung einrichten* (Schaltfläche oben auf der Labs-Seite, auch unter `docs/lab-umgebung.md`) beschreibt Hardwarevoraussetzungen, KVM/QEMU mit libvirt, VMs, isolierte Netze, einen virtuellen Router, zusätzliche Platten, Sicherheit, Snapshots und eine Funktionsprüfung. KVM/libvirt ist eine Empfehlung; andere Virtualisierer sind zulässig. Der Trainer stellt keine Maschinen bereit und führt nichts aus.

**Fach-LABs.** Jede Aufgabe zeigt Lernziel, offizielles Prüfungsziel, Voraussetzungen, Zeitbedarf, die Aufgabenstellung mit konkretem Ziel, Werkzeuge und Dokumentation sowie überprüfbare Erfolgskriterien. Darunter liegt die *Hilfestellung*: ein möglicher Lösungsweg in Schritten mit Befehlen, eingeklappt. Versuche die Aufgabe zuerst eigenständig; andere Lösungen sind richtig, wenn sie die Erfolgskriterien erfüllen. Gefährliche Schritte (Formatieren, Firewall-Richtlinie, Löschen von VMs) tragen einen Warnhinweis. Es folgen Selbstkontrollfragen mit aufklappbarer Antwort und typische Fehler.

**Status.** *LAB beginnen* setzt das LAB auf *in Bearbeitung*, *Als abgeschlossen markieren* auf *abgeschlossen*; beides lässt sich zurücknehmen. Nur abgeschlossene LABs zählen im Fortschritt. Betreuer deiner Gruppe sehen deinen LAB-Stand; LABs, die sie für die Gruppe empfehlen, tragen in deiner Liste die Kennzeichnung *empfohlen*.

**Fragen zum LAB.** Die Schaltfläche *Fragen zu diesem Prüfungsziel üben* führt direkt in den Übungsmodus für das Prüfungsziel des LABs.

Wichtig: Die App führt nichts aus. Nutze nur eigene Testsysteme wie virtuelle Maschinen, nie produktive Systeme.

## Fortschritt

*Fortschritt* zeigt je Modul die geübten Fragen, Trefferquote und Hilfequote je Thema, Simulationen und Tests sowie den Stand der Vokabeln.

## Gruppen

Unter *Gruppen* kannst du Lerngruppen beitreten (sofort oder nach Freigabe durch den Betreuer). Betreuer sehen den Lernstand der Mitglieder und können Fragen für die Gruppe bereitstellen.

## Offline

Einmal aufgerufene Seiten (Fragen, Ergebnisse, Labs, Vokabeln) bleiben im Browser verfügbar. Ohne Verbindung erscheint ein Hinweis; Antworten werden dann nicht gespeichert. Die App lässt sich auf Android und Desktop über „Zum Startbildschirm hinzufügen“ installieren.

## Für Betreuer

- *Verwaltung › Benutzer*: Konten freigeben.
- *Verwaltung › Gruppen*: Gruppe anlegen, Beitritte freigeben, Lernstand und LAB-Stände einsehen, LABs empfehlen, *Auswertung je Prüfungsziel* (Trefferquote, Sprachhilfe, Einschätzung „vertiefen“/„sicher“, häufig falsch beantwortete Fragen).
- *Verwaltung › Import*: eigene Fragen als JSON hochladen, mit Quelle und Prüfungsgeneration. Format in `content/README.md`. Die Fragen bleiben unveröffentlicht.
- *Verwaltung › Freigaben*: eigene Importe und die mitgelieferten Zusatzpools für die eigenen Lerngruppen freigeben oder die Freigabe zurücknehmen; der Rechtestatus jedes Pools steht daneben.
- *Verwaltung › Fragen*: eigene Fragen deaktivieren oder aktivieren.

Details in `docs/administration.md`.
