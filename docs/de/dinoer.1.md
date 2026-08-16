% DINOER(1) | Dinoer-Befehle
%
% August 2026

# BEZEICHNUNG

dinoer - ReAct-basiertes Werkzeug für Web-Automatisierung und Recherche für LLM-Agenten

# ÜBERSICHT

**shot.py** \[*Optionen*\] **--url** *URL*

**rpa.py** \[*Optionen*\] **--scenario** *DATEI*

**campagne.py** \[*Optionen*\] **--manifeste** *DATEI*

**journal.py** \[*Optionen*\]

**scripts/monter-repertoire-chiffre.sh**

**scripts/demonter-repertoire-chiffre.sh**

**scripts/monitor-verifier.sh** **--scenario** *DATEI* **--reference** *DATEI*

# BESCHREIBUNG

Dinoer verleiht einem LLM-Agenten Hände für Weboberflächen, die er sonst
nicht bedienen kann: von einem ReAct-Ausführungskern gesteuerte
Playwright-Aktionen, mit einem Accessibility-Baum (`--a11y`) als Augen,
wenn der Agent den Zustand liest. Jeder Befehl gibt ein einzelnes
JSON-Objekt auf der Standardausgabe aus, das dafür gedacht ist, von einem
Programm gelesen zu werden, nicht von einem Menschen.

Dinoer wird auf zwei Arten ausgeliefert: entweder in diesem `.deb` Paket oder als Git-Klon, der von **scripts/install.sh** unter Verwendung von **/opt/dinoer/** für alle installiert wird, die den Code ändern möchten. Die Python-Einstiegspunkte werden innerhalb der virtuellen Umgebung ausgeführt:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py ...

Für die vollständige Optionsliste eines jeden Befehls diesen mit
**--help** ausführen — diese Ausgabe ist gegenüber dieser Seite immer
maßgeblich.

# BEFEHLE

**shot.py**
: Erfasst eine Seite und gibt ein JSON zurück, das sie beschreibt. Mit
**--a11y** wird der Accessibility-Baum eingeschlossen. Aktionen können in
derselben Browsersitzung über **--actions** (eine JSON-Datei) ausgeführt
werden. **--reprendre-session** nutzt nur Cookies wieder, nie den
DOM-Zustand.

**rpa.py**
: Führt eine Szenariodatei (JSON) aus, die eine Sequenz von Aktionen
beschreibt, und gibt eine JSON-Zeile zurück. Dies ist der Befehl für
alles Wiederholbare, und der einzige, der Szenario-Assertions auswertet
und **--replay-verifier** unterstützt.

**campagne.py**
: Orchestriert eine Tiefenrecherche-Kampagne aus einem JSON-Manifest:
Paginierung pro Quelle, Deduplizierung über den Vektor-Cache, gezielte
Extraktion ohne Synthese. Liest fest `/opt/dinoer/dinoer.conf`, nur für
seinen `campagnes_dir`-Schlüssel — niemals `DINOER_CONF`, siehe DATEIEN
unten.

**journal.py**
: Liest das Append-only-Vorgangsprotokoll unter
**/var/log/dinoer/operations.jsonl**. Filtert nach Ziel, Datum,
Mutativität, Fehlern oder Intention; gibt Klartext oder JSON aus.

**scripts/monter-repertoire-chiffre.sh**, **scripts/demonter-repertoire-chiffre.sh**
: Mounten und Unmounten des mit gocryptfs verschlüsselten
Credentials-Verzeichnisses. Dinoer weigert sich, während es geschlossen
ist, irgendein Credential aufzulösen, und beendet sich mit Status 42,
statt auf etwas Schwächeres zurückzufallen. Einmalig konfiguriert durch
**scripts/configurer-repertoire-chiffre.sh**.

**scripts/monitor-verifier.sh**
: Führt einen strukturellen Nicht-Regressions-Durchlauf eines Szenarios
gegen eine gespeicherte Referenz aus und beendet sich bei Abweichung mit
einem von null verschiedenen Code. Dafür gedacht, von cron oder einem
systemd-Timer gesteuert zu werden; enthält keine eigene Schleife.

# GEMEINSAME OPTIONEN

Die folgenden Optionen werden von **shot.py** und **rpa.py** gemeinsam
genutzt, sofern nicht anders angegeben. Dies ist eine Auswahl, nicht die
vollständige Liste.

**--guide-version** *X.Y*
: Pflichtnachweis, dass **/opt/dinoer/docs/GUIDE_LLM.md** gelesen wurde.
Ohne diesen Nachweis — und ohne einen noch gültigen lokalen Marker —
verweigert der Befehl die Ausführung und beendet sich mit 1. Der
erwartete Wert ist der Kommentar *notice-version* in Zeile 3 dieses
Leitfadens. Dies ist die einzige Stelle, an der Dinoer nicht opt-in ist.

**--version**
: Gibt die installierte Version als JSON aus und beendet sich, ohne
einen Browser zu starten. Zu unterscheiden von **--guide-version**; die
beiden Zahlen stehen in keinem Zusammenhang.

**--a11y**
: Schließt den Accessibility-Baum in die JSON-Ausgabe ein. Der Agent
liest den DOM über diesen Baum; Dinoer hat keinen Screenshot- oder
Bilderfassungspfad.

**--wait-until** *networkidle*|*load*|*domcontentloaded*
: Wann die initiale Navigation als abgeschlossen gilt. Der Standardwert,
*networkidle*, wartet auf 500 ms Netzwerkstille und ist für die meisten
Ziele richtig. Eine Seite, die kontinuierlich abfragt, wird nie still —
dort *load* verwenden; das Erhöhen von **--timeout** hilft nicht, da die
Seite nie fertig wird.

**--timeout** *MS*
: Timeout pro Operation in Millisekunden (Standard 10000).

**--stealth**
: Entfernt die automatischen Markierungen, die einen Headless-Browser
identifizieren. Ändert weder die IP-Adresse des Betreibers noch fälscht
es eine Identität — der Punkt ist Gleichbehandlung, keine Verschleierung.

**--secrets** *DATEI*
: Löst Credentials aus einer expliziten JSON-Datei innerhalb eines
gemounteten Verzeichnisses auf, statt der standardmäßigen
host-basierten Suche. Nie ein Passwort auf der Kommandozeile übergeben:
Szenariofelder nutzen `"depuis_secrets"` plus `secret_cle`, und das
Credential wird innerhalb von Playwright aufgelöst.

**--no-evaluer**
: Verweigert die Aktion **evaluer** für den gesamten Lauf — es wird kein
beliebiges JavaScript auf der Zielseite ausgeführt.

**--no-filtre-evaluer**
: Deaktiviert die stdout-Neutralisierung von Rückgabewerten, URLs und
Fehlermeldungen von **evaluer** — nur für explizite Debug-Läufe. Die
Neutralisierung ist standardmäßig aktiv; bei Deaktivierung wird
`boussole.filtre_evaluer_actif: false` in der Ausgabe gesetzt, damit der
Betreiber es aus dem JSON selbst prüfen kann.

**--replay-verifier** *DATEI*
: Vergleicht den aktuellen Lauf mit einer gespeicherten Referenz und
beendet sich bei Abweichung mit einem von null verschiedenen Code. Die
Referenz wird von **--sauver-verifier-reference** geschrieben. Nur
**rpa.py**.

# DATEIEN

**/etc/dinoer/dinoer.conf**
: Konfiguration, die vom Credential Resolver (`shot.py`, `rpa.py`) über
**DINOER_CONF** gelesen wird, was diesen Pfad überschreibt). Erstellt vom Administrator und niemals automatisch generiert.  `secrets_dir` darin verweist auf das gemountete
Verzeichnis mit den Anmeldeinformationen. **campagne.py liest diese Datei nicht** — korrigiert
15/08/2026: es liest einen fest codierten `/opt/dinoer/dinoer.conf` für seinen eigenen
`campagnes_dir` Schlüssel (nur [`campagne.py::_CONF_PATH`]), niemals `DINOER_CONF`,
und somit wird diese Datei auf dem `.deb` Kanal nicht angezeigt, selbst wenn sie vorhanden ist.

**/opt/dinoer/**
: Anwendungscode, die Python-Virtualisierungsumgebung und die
Dokumentation, auf die die Befehle selbst verweisen.

**/opt/dinoer/docs/GUIDE_LLM.md**
: Der Einstiegspunkt, den ein Agent lesen muss. **MANUEL.md** im
selben Verzeichnis enthält die exakten Befehle mit echten Pfaden.

**/var/log/dinoer/**
: Persistentes Append-only-Vorgangsprotokoll (`operations.jsonl`) und
das strukturierte Beweisverzeichnis. Bleibt über erneute Deployments
erhalten.

**/tmp/dinoer/**
: Vergängliches, pro Lauf angelegtes Arbeitsverzeichnis, beim Neustart
gelöscht.

# RÜCKGABEWERT

**0**
: Der Lauf wurde abgeschlossen. Beachten Sie, dass ein HTTP-Fehler 404
oder 403 auf dem Ziel im JSON gemeldet wird, nicht als Fehlschlag des
Befehls.

**1**
: Der Lauf ist fehlgeschlagen, oder die Vorabprüfung des Leitfadens
wurde nicht erfüllt (*guide_non_lu*).

**2**
: Inkompatible Argumente, abgelehnt, bevor irgendein Browser gestartet
wurde.

**42**
: Das Credentials-Verzeichnis ist geschlossen, oder eine Credentials-Datei
hat ihre Integritätsprüfsumme nicht bestanden. Mit
**scripts/monter-repertoire-chiffre.sh** mounten, oder die Credentials-Datei
prüfen, wenn die Meldung eine ungültige Prüfsumme nennt.

**43**
: Keine **secrets_dir** konfiguriert. Konfigurieren Sie sie in **dinoer.conf**, oder verweisen Sie
**DINOER_CONF** auf eine projektspezifische Konfigurationsdatei.

# BEISPIELE

Eine Seite mit dem Accessibility-Baum erfassen:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url https://example.com --a11y --guide-version 1.6

Nur den Zustand einer Seite lesen, ohne eine Aktion auszuführen:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url https://example.com --guide-version 1.6

Ein Administrationspanel erreichen, das Statistiken kontinuierlich
aktualisiert:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url http://target.local/ --wait-until load --a11y

Ein Szenario mit Credentials aus einer expliziten Datei ausführen:

    /opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
        --scenario ./login.json --secrets ~/Vaults/project/creds.json

Prüfen, dass eine Seite sich strukturell nicht verschlechtert hat:

    bash scripts/monitor-verifier.sh --scenario ./page.json --reference ./page.ref.json

Das Vorgangsprotokoll für ein Ziel lesen:

    /opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible example.com --format json

# SIEHE AUCH

Die vollständige Dokumentation wird mit dem Paket installiert:
**/opt/dinoer/docs/MANUEL.md** für das Betriebshandbuch,
**/opt/dinoer/docs/GUIDE_LLM.md** für den agentenseitigen Leitfaden,
**/opt/dinoer/docs/FAQ_LLM.md** für Antworten nach Funktionsweise und
Version.
