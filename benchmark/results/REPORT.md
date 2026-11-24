# Modellvergleich für Webcam Mouse

Stand: 24. November 2026. **Vier Modelle, zwei Aufgaben, acht abgeschlossene Modellläufe.** Alle Zahlen stammen aus ausgeführten Läufen und anschließend unabhängiger Prüfung. Keine Lösung wurde nach `main` gemergt.

## Kurzfazit

- **GPT-6.2 Astra:** erster Kandidat für Koordination, schwierige Fehlersuche und Review. In beiden Aufgaben die kürzeste gemessene Bearbeitungszeit und die wenigsten Brutto-Tokens. Trotzdem kein automatischer Qualitätsgewinner: Seine erste Implementierung bestand alle kurzen Tests, enthielt aber eine relevante Dauerbetriebs-Schwäche.
- **GPT-6.2 Sol:** meine Wahl als Standard-Implementierungsworker. Seine erste Lösung verband korrekte Kernfunktionen, alle zusätzlichen numerischen Prüfungen und stabile Verarbeitung längerer Float-Streams. In der Reparaturaufgabe ebenfalls vollständig und robust, aber mit mehr Aufwand als Astra.
- **GPT-6.1 Sol:** brauchbare Alternative für ausführliche Tests und dokumentierte Untersuchung, nicht meine erste Wahl für Geschwindigkeit. Sehr hoher Cache-Anteil; bei nicht gecachten Input-Tokens günstiger als die anderen Kandidaten, also keinesfalls pauschal „ineffizient“.
- **GPT-6 Luna:** für diese Art selbstständiger numerischer Implementierungs-/Reparaturarbeit kein überzeugender Sparworker. Es brauchte die meisten Brutto-Tokens und Tool-Aufrufe, und die Reparatur ließ zwei unabhängig reproduzierte Schwächen zurück. Für einfache Extraktion oder Zusammenfassungen ist damit noch nichts bewiesen.

**Empfohlenes Setup bleibt: Astra als Hauptagent, Sol 6.2 als Worker; schwierige oder fehlgeschlagene Worker-Aufträge zurück an Astra.** Das ist eine vorläufige Empfehlung für unsere Nutzung, keine allgemeine Rangliste und kein Nachweis geringerer Abo-Limitbelastung.

## 1. Versuchsaufbau

Die Kandidaten wurden aus dem tatsächlich erreichbaren, kontobezogenen Codex-Modellkatalog gewählt: `gpt-6.2-astra`, `gpt-6.2-sol`, `gpt-6.1-sol` und `gpt-6-luna`. Das bisher verwendete Sol 6.1 ist bewusst als Vergleich enthalten.

### Aufgabe A: Implementierung

Ein deterministischer `MotionTracker` wandelt Markerpositionen in relative Bewegung um: Empfindlichkeit, exponentielle Glättung, Sprungerkennung, Trackingverlust, Pause/Resume/Reset und Eingabevalidierung. Dazu eigene Tests und eine Implementierungsdokumentation. Kein echtes Eingabegerät, keine GUI oder Fremdabhängigkeiten.

Gemeinsamer Ausgangscommit: `8b7deea04a109fc12b5e6c6aa047dba5bf738022`; Aufgabenvertrag: [BENCHMARK.md](../../BENCHMARK.md).

### Aufgabe B: Bestehenden Code prüfen und reparieren

Alle Kandidaten erhielten dieselbe geerbte Implementierung und dieselben Tests in einer frischen Sitzung. Sie sollten die Eignung für kontinuierliche Webcam-Streams untersuchen, eine relevante Schwäche reproduzieren, einen vorher fehlschlagenden Regressionstest schreiben und eine geprüfte Reparatur liefern.

Gemeinsamer Ausgangscommit: `575e6b942b8c380a9017ecb6ec8f804c47030cff`; Aufgabenvertrag: [BENCHMARK_REVIEW.md](../../BENCHMARK_REVIEW.md). Die geerbte Implementierung war die Astra-Lösung aus Aufgabe A; die Kandidaten wurden nicht über deren Urheber informiert. Das ist ein einzelner ausgewählter Fehlerfall, keine repräsentative Stichprobe aller Codebasen.

### Gemeinsame Bedingungen

- Gleicher Auftrag und Ausgangscommit je Aufgabe; eigener Branch und Worktree pro Kandidat, keine Übernahme anderer Kandidatenlösungen.
- Frische Worker-Sitzungen, Provider `openai-codex`, Reasoning `high`, kein angeforderter Fast-Tier; kein konfigurierter Fallback.
- Höchstens 35 Tool-Turns, 480 Sekunden konfiguriertes Laufzeitbudget und 540 Sekunden Controller-Timeout; maximal drei Modellprozesse gleichzeitig.
- Dieselbe VM und dasselbe Worker-Profil, Python 3.14.9. Die Profileinstellungen wurden nicht je Kandidat optimiert.
- Direkte CLI-Läufe statt automatischer Kanban-Aufgabenzerlegung: Hier sollte die Modellarbeit unter kontrollierten Bedingungen verglichen werden, nicht die Qualität einer automatischen Zerlegung.
- Worktrees trennen Arbeitskopien, sind aber keine Sicherheits-Sandbox. Alle Prozesse laufen unter demselben VM-Benutzer. Die aufgezeichneten Tool-Aufrufe zeigen keine Übernahme fremder Lösungen; das ist keine technisch erzwungene Geheimhaltung.

## 2. Unabhängige Funktionsprüfung

Die 30 Kernprüfungen wurden vor Einsicht in die erzeugten Implementierungen geschrieben. Sie prüfen unter anderem Reihenfolge von Skalierung/Glättung, den euklidischen Sprungschwellwert, zustandserhaltende Fehlerbehandlung, veränderliche Eingabelisten und alle Zustandsübergänge.

Zusätzlich gab es **nachträgliche, getrennt ausgewiesene** Prüfungen: sechs numerische Randfälle, einen deterministischen State-Machine-Replay mit 20 Seeds und je 500 Ereignissen sowie einen kontinuierlichen 2.400-Update-Stream. Diese Zusatzprüfungen sind keine rückwirkend umdefinierten Kern-Abnahmekriterien.

| Modell | A: Kern | A: numerische Zusatzfälle | A: eigene Tests | B: Kern | B: numerische Zusatzfälle | B: eigene Tests |
|---|---:|---:|---:|---:|---:|---:|
| GPT-6.2 Astra | 30/30 | 6/6 | 11 | 30/30 | 6/6 | 14 |
| GPT-6.2 Sol | 30/30 | 6/6 | 17 | 30/30 | 6/6 | 16 |
| GPT-6.1 Sol | 30/30 | 3/6 | 39 | 30/30 | 6/6 | 19 |
| GPT-6 Luna | 30/30 | 1/6 | 9 | 30/30 | 5/6 | 13 |

Alle eigenen Tests wurden vom Controller erneut ausgeführt und bestanden. Beide State-Machine-Replays bestanden bei allen Kandidaten. Mehr eigene Tests bedeuteten hier nicht automatisch bessere Randfallabdeckung.

Bei Sol 6.1 scheiterte A an einem überlaufenden Skalierungs-Zwischenergebnis, einem kleinen gemischten Integer/Float-Delta bei sehr großen Koordinaten und einer extrem knappen Kreisgrenze. Bei Luna kamen Probleme mit sehr großen Integern/Rationalen und der exakten rationalen Schwellwertgleichheit hinzu. Diese Werte sind überwiegend nicht kameratypisch, waren aber nützlich, um Robustheit und die weit gefasste Zahlenspezifikation zu untersuchen.

## 3. Wichtigster praktischer Fund: Kurze grüne Tests reichen nicht

Astra verwendete in A überall exakte `Fraction`-Arithmetik. Bei `smoothing=0.3` wuchs dadurch die Darstellung der rekursiven Filterausgabe kontinuierlich. Kleine Koordinaten verhinderten die steigenden Rechenkosten nicht. Astra erwähnte diese Einschränkung bereits in seiner Abschlussmeldung, beseitigte sie in A jedoch nicht.

Der Controller führte bei allen Kandidaten **denselben** kontinuierlichen Stream mit 2.400 Updates in sechs 400er-Blöcken aus. Zahlen unten sind gemessene Millisekunden für den gesamten Update-Loop, nicht Modell-Antwortzeit oder Webcam-Ende-zu-Ende-Latenz.

| Modell | A: Float-Stream | B: Float-Stream nach Reparatur | B: Integer-Baseline, danach Float-Stream |
|---|---:|---:|---:|
| GPT-6.2 Astra | 2.019,7 ms | 171,1 ms | 176,2 ms |
| GPT-6.2 Sol | 23,9 ms | 160,0 ms | 160,9 ms |
| GPT-6.1 Sol | 18,1 ms | 161,9 ms | 160,2 ms |
| GPT-6 Luna | 11,2 ms | 36,8 ms | 2.018,0 ms |

Bei Astras erster Lösung war der letzte 400er-Block etwa 7,6-mal langsamer als der erste. Die Reparaturen von Astra, Sol 6.2 und Sol 6.1 beseitigten diese beobachtete Zunahme für beide getesteten Streams und behielten die numerischen Zusatzfälle bei.

**Lunas Reparatur war nur teilweise gelungen:** Ein reiner Float-Stream wurde schnell. Eine einzige Integer-Baseline vor den Float-Samples hielt den Code jedoch auf dem ursprünglichen, wachsenden Fraction-Pfad; der letzte Block war wieder etwa 7,5-mal langsamer als der erste. Außerdem veränderte sein Float-Pfad die strikte Kreisgrenze: Nach `(0.0, 0.0)` wird `(1.0, 1e-12)` bei `max_jump=1.0` nicht als Sprung verworfen, obwohl der exakte Abstand größer als 1 ist.

Die Zusatzmessungen liefern Hinweise auf Designprobleme, keine Hard-Realtime-Garantie. Sie wurden sequenziell auf einer gemeinsamen VM ohne CPU-Affinität oder statistische Wiederholungsserie ausgeführt. Die von Kandidaten selbst erstellten Benchmarks nutzten unterschiedliche Streams; deren behauptete Speedups wurden daher **nicht** als gemeinsame Vergleichsmetrik übernommen.

## 4. Bearbeitungszeit und Tokenverbrauch

Die Zeiten umfassen CLI-Start bis CLI-Ende und damit auch Tool-Arbeit, Tests, eventuelle Wartezeit und Kommunikation mit dem Gateway. Wegen paralleler Läufe und geteilter Infrastruktur sind sie deskriptiv, keine isolierte Modell-Latenzmessung.

| Aufgabe | Modell | Sekunden | Input-Tokens | davon Cache-Read | Output-Tokens | Brutto gesamt | Modell-API-Aufrufe | Tool-Aufrufe |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | GPT-6.2 Astra | 122,07 | 158.388 | 107.648 | 4.088 | 162.476 | 11 | 12 |
| A | GPT-6.2 Sol | 239,77 | 264.803 | 175.872 | 9.407 | 274.210 | 14 | 18 |
| A | GPT-6.1 Sol | 263,09 | 207.435 | 165.248 | 10.924 | 218.359 | 12 | 11 |
| A | GPT-6 Luna | 169,30 | 348.199 | 299.008 | 6.298 | 354.497 | 19 | 19 |
| B | GPT-6.2 Astra | 273,99 | 376.766 | 282.752 | 7.964 | 384.730 | 17 | 27 |
| B | GPT-6.2 Sol | 380,35 | 556.356 | 400.640 | 13.831 | 570.187 | 21 | 28 |
| B | GPT-6.1 Sol | 462,35 | 573.501 | 532.864 | 13.295 | 586.796 | 23 | 29 |
| B | GPT-6 Luna | 352,11 | 852.391 | 783.232 | 11.221 | 863.612 | 33 | 39 |

| Modell, beide Aufgaben | Brutto-Tokens | Nicht gecachter Input | Summe Bearbeitungssekunden |
|---|---:|---:|---:|
| GPT-6.2 Astra | 547.206 | 144.754 | 396,06 |
| GPT-6.2 Sol | 844.397 | 244.647 | 620,12 |
| GPT-6.1 Sol | 805.155 | 82.824 | 725,44 |
| GPT-6 Luna | 1.218.109 | 118.350 | 521,41 |

**So sind die Zahlen zu lesen:**

- Brutto = Input + Output laut Hermes-Telemetrie; wiederholt gesendeter Kontext wird bei jedem Aufruf gezählt. Das sind keine einzigartigen Wörter der Lösung.
- Cache-Read ist ein Teil des Inputs, kein zusätzlich zu addierender Verbrauch. Nicht gecachter Input = Input minus Cache-Read.
- Ausgewiesene Reasoning-Tokens werden nicht nochmals auf Output addiert; die Messdatei bewahrt sie separat auf.
- Für die acht Hauptläufe wurden insgesamt **3.414.867 Tokens** ausgewiesen. Einschließlich der getrennten Hilfsaufrufe zur Sitzungstitel-Erzeugung: **3.417.479 Tokens**. Koordinierende Chat-/Tool-Arbeit dieses Berichts ist darin nicht enthalten.
- Alle Läufe meldeten `cost_status=included`. Die von Hermes dafür ausgewiesenen null Dollar sind **keine Aussage über kostenlose Ressourcen oder null Abo-Verbrauch**. Unterschiedliche Modellgewichte, Caching und Abo-Regeln sind aus diesen Zahlen nicht zuverlässig in Prozent des Fünf-Stunden-Limits umzurechnen.
- Insbesondere darf aus Astras Brutto-Vorsprung nicht abgeleitet werden, dass Astra der billigste API- oder Abo-Kandidat ist. Sol 6.1 hatte erheblich weniger nicht gecachten Input; belastbare monetäre Einsparungen wurden nicht gemessen.

## 5. Qualitative Bewertung

### GPT-6.2 Astra

**Stärken:** knappste Lösung in A, wenige Schritte, niedrigste Bearbeitungszeit und niedrigste Brutto-Tokens in beiden Aufgaben. B enthielt eine echte Reproduktion, einen repräsentationsbasierten Regressionstest und eine nachvollziehbare begrenzte Präzisionsstrategie. Beide unabhängigen Zahlenprüfungen vollständig bestanden.

**Schwächen:** In A numerische Exaktheit über praktische Dauerbetriebs-Eignung gestellt. Obwohl die Einschränkung genannt wurde, wäre die erste Lösung kein ungeprüfter Merge-Kandidat. Auch die Reparatur verwendet für den einfachen Anwendungsfall relativ aufwendige rationale Arithmetik.

**Bewertung:** sehr guter anspruchsvoller Bearbeiter/Reviewer in dieser Stichprobe, aber weiterhin unabhängige Prüfung nötig.

### GPT-6.2 Sol

**Stärken:** A war der beste Kompromiss aus vollständigen Kernfunktionen, numerischer Robustheit und stabiler normaler Stream-Verarbeitung. B reparierte das geerbte Problem ohne die getesteten Grenzfälle zu verlieren. Dokumentierte auch numerische Kompromisse und prüfte in A seine Dokumentationsbeispiele.

**Schwächen:** längere Bearbeitung und deutlich mehr Brutto-Tokens als Astra. Der numerische Sonderfallcode macht selbst das kleine Modul komplexer; die Reparatur ist ebenfalls keine einfache Float-only-Lösung.

**Bewertung:** bevorzugter Standardworker für klar spezifizierte Implementierungsaufträge mit Tests. Die Einsparung gegenüber direkter Astra-Nutzung muss im realen Abo-Betrieb separat beobachtet werden.

### GPT-6.1 Sol

**Stärken:** umfangreiche eigene Tests und besonders ausführliche Reparaturbelege; in B unter anderem wiederholte Messungen und Untersuchung langer stationärer Filtertails. Beide Aufgaben vollständig beendet. Sehr hoher Cache-Anteil.

**Schwächen:** trotz 39 eigenen Tests in A drei zusätzliche Zahlenfälle verfehlt. B brachte eine größere, komplexere Präzisionsimplementierung und zusätzliche Artefakte hervor und nutzte fast das gesamte Laufzeitbudget. Mehr Test-/Dokumentationsumfang war nicht kostenlos.

**Bewertung:** brauchbare Alternative für gründliche Untersuchungen, aber für unseren Standard nicht klar besser als Sol 6.2. Langfristige Recherche-/Schreibqualität wurde nicht getestet.

### GPT-6 Luna

**Stärken:** kompakte, schnelle normale Float-Implementierung in A; alle 30 Kernfälle bestanden. B erkannte die zugrunde liegende Fraction-Problematik und verbesserte den reinen Float-Fall stark.

**Schwächen:** höchster Brutto-Verbrauch und die meisten Tool-Aufrufe; in B auch ein fehlerhafter `write_file`-Aufruf ohne `path`. Seine neue Regression fordert nach einem einzelnen Update Float-Ausgaben, statt das eigentliche Langzeitwachstum allgemein zu prüfen. Das übersah den weiter langsamen gemischten Pfad. Strikte Jump-Semantik ging an einer Grenze verloren. Die Review-Dokumentation nennt am Ende zudem eine veraltete Testzahl von 12, während tatsächlich 13 bestanden.

**Bewertung:** normale Funktion erfüllt, Reparaturauftrag nur teilweise robust gelöst. Für unbeaufsichtigte numerische Kernlogik derzeit nicht empfohlen.

## 6. Anweisungstreue und Grenzen des Ergebnisses

Alle acht Läufe lieferten Code, Tests und Dokumentation; keiner endete nur mit einem Plan. Die geschützten Aufgabenbeschreibungen und README blieben unverändert. In den aufgezeichneten Aktionen wurden keine Kandidaten-Commits/Pushes oder Netzwerk-Recherchen beobachtet; die Veröffentlichung übernahm allein der Controller. Erwartete Fehltests vor Implementierung/Reparatur sind in den Rohprotokollen sichtbar.

Das ursprüngliche Problem „ignoriert im langen Alltag meine Anweisungen“ ist damit **nicht abschließend vermessen**. Diese Aufgaben waren klar begrenzt, enthielten präzise Schnittstellen und hatten frische Kontexte. Es gab keinen Langzeit-Chatvergleich, keinen gleichwertigen Planungstest und keine mehrfache Stichprobe jeder Aufgabe. Auch der Bewerter ist ein Modell; deshalb stützt sich das Urteil auf ausgeführte Tests, beobachtete Änderungen und prüfbare Messwerte statt auf einen bloßen Modell-Gesamtscore.

### Rollenempfehlung mit Sicherheitsnetz

| Rolle | Vorschlag | Begründung / Sicherheit der Aussage |
|---|---|---|
| Hauptagent, Aufgaben klären und koordinieren | GPT-6.2 Astra | Vorläufig; schnell und zielgerichtet in beiden Aufgaben, Planung selbst nicht separat gebenchmarkt |
| Klar begrenzte Implementierung | GPT-6.2 Sol | Direkte Evidenz aus A und B; unabhängige Tests und Review beibehalten |
| Schwierige Fehleranalyse / Abschlussreview | GPT-6.2 Astra | Direkte Reparaturevidenz; bei besonders kritischen Änderungen zweiter Blick statt Selbstabnahme |
| Zusätzliche Test-/Evidenzarbeit | Sol 6.2; Sol 6.1 als Alternative | Sol 6.1 war gründlich, aber langsamer; nicht nur nach Anzahl eigener Tests bewerten |
| Einfache Extraktion, Zusammenfassung, mechanische Arbeit | Noch kein belastbarer Gewinner | Dafür wurde keine eigene Aufgabe getestet; Lunas Name/Klasse allein belegt keine Ersparnis |

Keine automatische Änderung unserer konfigurierten Modelle und kein Gewinner-Merge. Für Webcam Mouse würde ich **die Sol-6.2-Implementierung aus A als Ausgangspunkt für den nächsten menschlich geprüften PR betrachten**, nicht unmittelbar eine der numerisch aufwendigen Reparaturvarianten übernehmen.

## 7. Branches, Nachweise und Reproduktion

| Modell | Implementierung A | Review/Reparatur B |
|---|---|---|
| GPT-6.2 Astra | [benchmark/gpt-6.2-astra](https://github.com/Benedikt123/webcam-mouse/tree/benchmark/gpt-6.2-astra), `640d28d` | [benchmark/review-gpt-6.2-astra](https://github.com/Benedikt123/webcam-mouse/tree/benchmark/review-gpt-6.2-astra), `e5dd8af` |
| GPT-6.2 Sol | [benchmark/gpt-6.2-sol](https://github.com/Benedikt123/webcam-mouse/tree/benchmark/gpt-6.2-sol), `6d54e73` | [benchmark/review-gpt-6.2-sol](https://github.com/Benedikt123/webcam-mouse/tree/benchmark/review-gpt-6.2-sol), `e3700fc` |
| GPT-6.1 Sol | [benchmark/gpt-6.1-sol](https://github.com/Benedikt123/webcam-mouse/tree/benchmark/gpt-6.1-sol), `2dfbd9f` | [benchmark/review-gpt-6.1-sol](https://github.com/Benedikt123/webcam-mouse/tree/benchmark/review-gpt-6.1-sol), `1e5ac5a` |
| GPT-6 Luna | [benchmark/gpt-6-luna](https://github.com/Benedikt123/webcam-mouse/tree/benchmark/gpt-6-luna), `28679a5` | [benchmark/review-gpt-6-luna](https://github.com/Benedikt123/webcam-mouse/tree/benchmark/review-gpt-6-luna), `397a258` |

Alle acht Remote-Branch-Commits wurden nach dem Push zurückgelesen und mit dem lokalen SHA verglichen. `main` enthält ausschließlich die beiden Aufgabenbeschreibungen zusätzlich zum ursprünglichen Repository, keine Modelllösung.

In diesem Verzeichnis liegen die unabhängigen Prüfscripte, bereinigte Messdaten in `measurements.json`, `measurements.csv` und die vollständigen Controller-Prüfausgaben unter `checks/`. Die ursprünglichen Modell-Traces und Usage-Dateien bleiben lokal erhalten; sie werden wegen möglicher Kontext-/Pfadangaben nicht ungeprüft öffentlich hochgeladen.

Beispiel, von einem Checkout des Report-Branches aus mit absolutem Pfad zu einem separat ausgecheckten Kandidaten:

```sh
CANDIDATE=/path/to/candidate python benchmark/results/acceptance.py
CANDIDATE=/path/to/candidate python benchmark/results/numeric_probes.py
CANDIDATE=/path/to/candidate python benchmark/results/replay_probe.py
python benchmark/results/stress.py /path/to/candidate
python benchmark/results/stress.py /path/to/candidate --integer-baseline
cd /path/to/candidate
python -m unittest discover -s tests -v
```

### Transparenz über Controller-Korrekturen

Die erste Startserie erreichte kein Modell: Der Gateway lehnte die lokal dokumentierte CLI-Option `--run-budget` ab. Diese vier Null-Token-Startfehler wurden separat erhalten; die gültigen Läufe nutzten das Profil-Laufzeitbudget. Außerdem wurde eine anfangs zu strenge Zusatzprüfung von exakter Fraction-Ausgabegleichheit auf numerische Toleranz korrigiert und für alle Kandidaten neu ausgeführt. Diese Fehler sind nicht den Kandidaten angelastet.

Nicht geprüft: physische Webcam, GUI, echte Maussteuerung, Python-3.11-Ausführung, plattformübergreifendes Verhalten, langfristige Repository-Integration oder reale Kosten-/Limitvorteile. Das Projekt ist nach diesem Test weiterhin ein geprüfter Motion-Core-Versuch auf separaten Branches, noch keine fertige Webcam-Maus.
