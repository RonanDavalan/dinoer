# Dinoer — Betreiberleitfaden

Version 1.11 — August 2026 (v1.23.0) — Oberfläche an die Dinoer-Rekonstruktion
angepasst: kein Screenshot, kein Set-of-Mark, kein `watch.py`; der Agent
liest den Accessibility-Baum und steuert Playwright-Aktionen über
CSS-Selektoren.

*Ebenfalls verfügbar auf Englisch, Französisch und Spanisch unter
`docs/`, `docs/fr/` und `docs/es/`.*

---

## Warum Dinoer — was Sie tatsächlich delegieren

### Das Problem, das Dinoer löst

Wenn Sie mit einem LLM an einer Webanwendung arbeiten, entsteht eine
Wahrnehmungsasymmetrie: Das Modell liest Code, führt Befehle aus,
beobachtet Textausgaben — aber es sieht nicht die Oberfläche, die Ihre
Nutzer sehen. Sie schon.

Diese Asymmetrie erzeugt eine spezifische Form von Unsicherheit: Sie
wissen nicht, ob das, was das Modell beschreibt, dem entspricht, was Sie in
einem Browser sehen würden. Um sicherzugehen, müssen Sie ihm entweder aufs
Wort glauben oder es selbst überprüfen.

Dinoer löst dieses Problem, indem es dem Modell dieselbe strukturierte
Sicht verschafft, die Sie in einem Browser hätten: den Accessibility-Baum,
gelesen über ein echtes Headless-Chromium, plus die DOM-Werte, die es mit
`evaluer` extrahiert. Sie nehmen das Modell nicht mehr beim Wort — Sie
beobachten denselben Zustand wie es.

```
 Browser (Headless-Chromium)
        │  Playwright steuert ihn — klicken, ausfüllen, navigieren
        ▼
 shot.py / rpa.py
        │  liest den resultierenden DOM-Zustand über parallele Sichten
        ├──▶ a11y_tree            Accessibility-Baum, Text
        ├──▶ evaluations          über `evaluer` extrahierte Werte
        └──▶ Sitzungsdatei        nur Cookies (--sauver-session)
        │
        ▼
 boussole + JSON auf stdout — der Zustand, wie der Betreiber ihn prüfen kann
        │
        ▼
 Sie (das Modell): lesen → analysieren → entscheiden → handeln → Schleife
```

### Was Sie delegieren

Dinoer lässt Sie **repetitive und kontrollintensive Überprüfungen**
delegieren:

- Prüfen, dass 20 Seiten einer Site nach einem Deployment korrekt antworten
- Bestätigen, dass ein Login-Formular auf der richtigen Oberfläche
  funktioniert
- Sicherstellen, dass ein Deployment die Struktur einer kritischen Ansicht
  nicht beschädigt hat
- Ein Admin-Panel über dieselbe Oberfläche steuern, die ein Mensch nutzen
  würde

Ohne Dinoer liegen diese Überprüfungen in Ihrer Verantwortung. Mit Dinoer
führt das Modell sie aus und meldet das Ergebnis — mit dem JSON-Beleg dazu.

### Was bei Ihnen bleibt

Bei Ihnen bleibt die **Sinnvalidierung auf hoher Ebene**: die Entscheidung,
ob das vom Modell präsentierte Ergebnis akzeptabel ist, Ihren Erwartungen
entspricht und mit dem übereinstimmt, was Ihre Nutzer sehen sollten. Diese
Entscheidung bleibt Ihre.

### Respektvolle Navigation (v1.15.0)

Dinoer verschleiert seine Identität nicht, um Bot-Erkennung zu umgehen.
`--stealth` entfernt automatische technische Markierungen
(`navigator.webdriver`), die Headless-Browser unabhängig von der Absicht
blockieren — es ändert weder die IP-Adresse noch die Identität des
Betreibers noch die Tatsache, dass der Lauf deklariert ist. Im Gegenzug
meldet jeder Lauf seinen eigenen Fußabdruck (`respect`: besuchte Seiten,
ausgeführte Aktionen, Dauer) und respektiert konfigurierbare
Höflichkeitsverzögerungen und harte Obergrenzen (`dinoer.conf
[navigation]`). Das Recht zu navigieren und die Pflicht, dies messbar zu
tun, werden als untrennbar behandelt — siehe `docs/RETOUR_EXPERIENCE.md`
FR-77/FR-78/FR-79 für den Praxiskontext, der dies geprägt hat.

**Lokale Ziele — die Höflichkeitsverzögerung ist keine Doktrin, sondern
ein Standardwert (v1.19.0):** Der mitgelieferte Wert
`min_action_delay_ms: 800` schützt einen unkonfigurierten Erstlauf gegen
das öffentliche Internet — gegen Ihre eigene Entwicklungs- oder
Produktionsmaschine ist er bedeutungslos. Setzen Sie ihn für lokales
Debugging in Ihrer lokalen `dinoer.conf` auf `0`; siehe `docs/MANUEL.md`
Abschnitt 3b.

### Wann Dinoer das richtige Werkzeug ist

| Anwendungsfall | Für Dinoer geeignet? |
|---|---|
| Strukturelle Validierung nach einem Deployment | ✓ Ja |
| Diagnose einer defekten Interaktion | ✓ Ja |
| Navigation und Formulareingabe (~30 s max.) | ✓ Ja |
| Delegation repetitiver Prüfungen | ✓ Ja |
| Lange Server-Operation (Klonen ~2–5 min) | ✗ Nein — Playwright-Timeout |
| Massenlöschung oder -mutation | ✗ Nein — direkten API-Aufruf bevorzugen |
| Workflow, der ein Rollback erfordert | ✗ Nein — Dinoer kann nichts rückgängig machen |

Für davon abgeratene Fälle siehe `docs/GUIDE_LLM.md`, Abschnitt „When NOT
to use Dinoer" (Friktionen FR-59 und FR-60 dokumentiert).

---

**Dieses Dokument ist für die Person geschrieben, die Dinoer betreibt.**

Es ergänzt `GUIDE_LLM.md` (für Modelle bestimmt) um konkrete Beispiele,
Schritt-für-Schritt-Anleitungen und Hinweise zu häufigen Stolperfallen.

---

## Demonstrations-Anwendungsfälle

Die folgenden Fälle veranschaulichen, wie eine Sitzung aus Agent plus
Dinoer in der Praxis aussehen kann. Sie sind dazu gedacht, dass Sie sie
gegen Ihren eigenen Kontext bewerten — nicht als Empfehlung, einen
bestimmten Fall zu übernehmen. Nur Fall 1 wird als lauffähiges Szenario
ausgeliefert; die anderen sind bewusst erzählend, und jeder erklärt unter
seiner eigenen Überschrift, warum.

### Fall 1 — lokale CSS/JS-Fehlersuche

Als reales, lauffähiges Szenario eingecheckt:
`scenarios/exemples/depannage_local.json`. Es diagnostiziert eine
Layoutverschiebung oder eine blockierte Interaktion auf einer lokal
bereitgestellten Oberfläche — eine schnelle Sonde, die `erreurs_js`/
`erreurs_console` und den Accessibility-Baum liest und dann die Korrektur
mit `rpa.py --replay-verifier` gegen eine vor der Regression erfasste
Referenz validiert. Direkt ausführen:

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/exemples/depannage_local.json \
  --guide-version 1.3
```

### Fall 2 — Hardwarekomponenten über Shops hinweg vergleichen

Ein Agent, der gebeten wird, Preis und Lagerbestand einer Komponente über
mehrere Online-Shops hinweg zu vergleichen, könnte Dinoer mit einem
separaten Werkzeug zur URL-Entdeckung (zum Beispiel einer lokalen
Suchinstanz) kombinieren, um Kandidatenseiten von Shops zu finden, dann
Dinoer im schreibgeschützten Modus mit `evaluer`-Aktionen nutzen, um
Preis/Lagerbestand/Spezifikationen von jeder Seite zu extrahieren, und
schließlich die Ergebnisse selbst vergleichen.

**Bewusst nicht als eingechecktes Szenario ausgeliefert:** Einen
bestimmten Shop in einem öffentlichen, versionierten Szenario zu nennen,
ist eine Entscheidung, die Ihnen gehört, kein Standard, den dieses Projekt
in Ihrem Namen treffen sollte. Es birgt auch ein reales
Fragilitätsrisiko — ein öffentliches Szenario, das auf eine namentlich
genannte kommerzielle Site zielt, kann Monate später scheitern, wenn sich
deren Anti-Bot-Haltung ändert (39 % der in `docs/RETOUR_EXPERIENCE.md`
FR-77 erfassten kommerziellen Sites gaben einen sofortigen Block zurück),
was das Beispiel eher diskreditiert als hilft. Wenn Sie diese Komposition
selbst aufbauen: Beachten Sie, dass jedes Werkzeug zur URL-Entdeckung, mit
dem Sie Dinoer kombinieren (eine lokale Suchinstanz oder sonstiges), keine
Dinoer-Komponente ist — es ist ein separates Teil, das der Agent
obendrauf komponiert.

### Fall 3 — technische Dokumentation erkunden und zusammenfassen (Single-Page-Apps)

Ein Agent, der beauftragt ist, einen Integrationsleitfaden für eine als
Single-Page-App gebaute Dokumentations-Site zu erstellen, könnte `rpa.py`
mit `attendre_reseau_calme` nutzen, um clientseitiges Routing sich setzen
zu lassen, den Accessibility-Baum extrahieren, um die Seitenstruktur zu
kartieren, dann Codeblöcke rekursiv mit `evaluer` durchlaufen, um ihren
exakten Inhalt zu ziehen, und schließlich das gesammelte Material zu einem
Leitfaden synthetisieren.

**Aus demselben Grund wie Fall 2 nicht als eingechecktes Szenario
ausgeliefert** — eine bestimmte Dokumentations-Site zu nennen (oder,
schlimmer, einen bestimmten Zahlungsanbieter, dessen Dokumentation zufällig
das funktionierende Beispiel ist) ist eine kommerzielle und
reputationsbezogene Festlegung, die dieses Projekt nicht standardmäßig
treffen sollte, und dasselbe WAF-Fragilitätsrisiko gilt für ein
öffentliches Szenario, das auf ein einziges reales Ziel festgenagelt ist.

### Fall 4 — ein selbstgehostetes Observability- oder Analytics-Dashboard konfigurieren

Ein Betreiber, der ein selbstgehostetes Monitoring- oder
Web-Analytics-Dashboard hinter einem Reverse-Proxy einrichtet, kann Dinoer
nutzen, um die Oberfläche selbst zu steuern — ein Dashboard erstellen,
eine Datenquelle verdrahten, eine Alarmregel setzen — genauso, wie jedes
andere Admin-Panel konfiguriert wird, statt Dateien für Schritte von Hand
zu bearbeiten, die die Oberfläche eigentlich übernehmen soll. Dies schließt
Ziele hinter einer HTTP-Basic-Auth-Herausforderung auf Netzwerkebene ein
(`--http-credentials`, v1.21.0) — bestätigt gegen eine echte,
Caddy-geschützte Admin-Oberfläche, nicht nur eine synthetische Fixture:
die gespeicherten Credentials beantworteten die Herausforderung beim
ersten Versuch.

**Nicht als eingechecktes Szenario ausgeliefert** — das Dashboard-Layout
und die Namen der Datenquellen sind spezifisch für die Infrastruktur eines
Betreibers, und ein synthetisches Äquivalent zu erfinden würde
duplizieren, was die lokale Fixture in Fall 1 bereits für strukturelle
Regression abdeckt — nicht für diese Art geführter, mehrstufiger
Konfigurationsarbeit.

### Fall 5 — eine Ticketing-Plattform durchgängig administrieren

Dinoer über mehrere Sitzungen hinweg eingesetzt, um eine echte,
selbstgehostete Ticketing-Installation zu konfigurieren und zu betreiben —
Event-Einrichtung, Ticketkategorien, eine eigene Domain und die
Scan-/Check-in-Werkzeuge am Veranstaltungstag — über dieselbe
Weboberfläche, die ein menschlicher Administrator nutzen würde. Unterwegs
traten reale Friktionen auf und wurden gelöst (Sitzungsverwaltung,
Dropdown-Eigenheiten, ein Berechtigungs-Prompt, der einen unbeaufsichtigten
Schritt blockierte) — keine reibungslose Erfolgsgeschichte, was Teil dessen
ist, was sie zu einem nützlichen Beispiel macht: Die Hindernisse waren
gewöhnliche Web-Automatisierungshindernisse, nichts Dinoer-Spezifisches.

**Nicht als eingechecktes Szenario ausgeliefert** — eine
Ticketing-Konfiguration berührt Abrechnungs- und Veranstaltungsortdetails,
die für den Betreiber spezifisch sind, dieselbe Begründung wie Fall 2.

### Fall 6 — einen regionalen Veranstaltungskalender verfolgen

Eine einfache semantische Sondennutzung: einen Agenten bitten, einen
lokalen Veranstaltungskalender auf bevorstehende Termine zu prüfen, ohne
vorab zu wissen, welche Seite die Antwort enthält. Der
schreibgeschützte Modus von Dinoer, kombiniert mit dem Accessibility-Baum,
lässt den Agenten in einer Handvoll Anfragen scannen und zurückmelden —
kein Vision-Modell für diese Art textgetriebener Aufgabe nötig. Eine
Sitzung produzierte auch ein sauberes, reales Beispiel für das dokumentierte
Falsch-positiv-Verhalten des WAF-Signals: eine Seite lud normal (reicher
Inhalt, kein Captcha, kein Interstitial), während `respect.waf_bloquants`
trotzdem auslöste — wegen einer nicht damit zusammenhängenden
Drittanbieter-Ressource auf der Seite, die einem Erkennungsschlüsselwort
entsprach — in etwa einer Minute gelöst, indem der bereits in derselben
Antwort vorhandene Accessibility-Baum gelesen wurde, genau wie es die
Regel „Signal, nie Verriegelung" des Leitfadens vorwegnimmt.

**Nicht als eingechecktes Szenario ausgeliefert** — eine bestimmte
regionale Veranstaltungs-Site ist kein stabiles, reproduzierbares
öffentliches Ziel, und eine namentlich zu nennen ist die Entscheidung des
Betreibers, kein Projektstandard.

### Fall 7 — realen Zugriff auf E-Commerce-Sites unter respektvoller Navigation testen

Eine wiederkehrende, ehrliche Beobachtung aus echten Sitzungen: respektvoll
eingesetzt (ratenbegrenzte Verzögerungen, Seiten-/Aktionsobergrenzen,
`--stealth` aktiv, kein Versuch, einen echten Block zu erzwingen), stellt
Dinoer bei einer Reihe von E-Commerce-Sites fest, dass ein großer Anteil
großer Plattformen einen glatten Block zurückgibt — HTTP 403, oder eine
Anfrage, die nie abschließt — unabhängig davon, wie höflich der Traffic
ist. Dies ist kein zu behebendes Dinoer-Manko: Anti-Bot-Haltung ist die
eigene Entscheidung der Site, und Dinoer versucht nicht, sie zu
überwinden (siehe „Respektvolle Navigation" oben). Praktisch: Für
Preisvergleichsaufgaben gegen große kommerzielle Plattformen einen
nennenswerten Anteil an Sackgassen erwarten, und ein Block-Signal
(`respect.waf_bloquants`) als Information zum Umfahren behandeln, nicht
als Fehler, gegen den erneut versucht werden sollte.

Eine Unterscheidung, die es sich zu merken lohnt: ein unsichtbarer
Verifizierungsbildschirm, der nie aufgelöst wird und nichts zum Handeln
bietet (keine Checkbox, keine Bildherausforderung), unterscheidet sich von
einem interaktiven CAPTCHA. Letzteres ehrlich zu beantworten ist legitim —
ein Agent, der für einen namentlich genannten Menschen von dessen eigener
IP aus operiert, ist nicht der „Roboter", auf den die Frage abzielt.
Ersteres bietet der Agentenseite schlicht keine Tür zum Öffnen, und es
gewaltsam zu umgehen (IP-Rotation, TLS-Fingerprint-Fälschung) liegt
außerhalb dessen, was Dinoer tut.

**Bewusst nicht als eingechecktes Szenario ausgeliefert, und bewusst ohne
Nennung der beteiligten Plattformen** — siehe die
WAF-Fragilitätsbegründung unter Fall 2: eine datierte
Block-/Kein-Block-Tabelle, die an namentlich genannte kommerzielle Sites
gebunden ist, veraltet und untergräbt ihren eigenen Punkt schneller, als
sie ihn veranschaulicht. `docs/RETOUR_EXPERIENCE.md` FR-77 dokumentiert
dasselbe Muster im Panel-Maßstab (39 % Sofort-Block-Rate).

---

## Voraussetzungen vor dem Start

```bash
# 1. Prüfen, dass Dinoer antwortet
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://example.com --a11y
# → muss {"succes": true, ...} zurückgeben

# 2. Prüfen, dass das verschlüsselte Verzeichnis gemountet ist (falls gocryptfs)
ls ~/Vaults/Dinoer/
# → muss .json-Dateien zeigen, nicht verschlüsselten Inhalt

# 3. Credentials für eine Domain prüfen
/opt/dinoer/venv/bin/python -c "
import sys; sys.path.insert(0, '/opt/dinoer')
from lib.repertoire_chiffre import lire_credential
print('OK' if lire_credential('target.local', 'password') else 'EMPTY')
"
```

---

## Credentials-Konfiguration pro Projekt

Jedes Projekt kann sein eigenes Credentials-Verzeichnis haben. Zwei
Methoden:

**Methode 1 — direkte Umgebungsvariable (einmalig):**

```bash
DINOER_SECRETS_DIR=~/Vaults/MyProject \
  /opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url …
```

**Methode 2 — projektspezifische `.dinoer.conf`-Datei (empfohlen für
wiederkehrende Projekte):**

```bash
# Datei im Projektwurzelverzeichnis erstellen
echo '{"secrets_dir": "../MyProject-secrets"}' > ~/git/MyProject/.dinoer.conf

# Dann jedem Aufruf voranstellen (oder zu Beginn der Shell-Sitzung exportieren)
export DINOER_CONF=~/git/MyProject/.dinoer.conf
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url …
```

Das `secrets_dir` in `.dinoer.conf` kann ein relativer Pfad sein — er wird
relativ zum Speicherort der Datei `.dinoer.conf` aufgelöst.

---

## Eine Seite erfassen und analysieren

```bash
# Seitenzustand lesen (schreibgeschützt)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y
# → gibt url_courante, titre_page, a11y_tree im JSON zurück
```

**Was Sie erhalten:**
- `boussole.url_courante` + `boussole.titre_page`: effektive URL und Titel
  nach der Navigation
- `a11y_tree`: Seitenstruktur als Text (Überschriften, Felder,
  Schaltflächen)
- `etat.pret_a_agir` + `etat.raisons`: wahrgenommene Friktionen, damit das
  Modell sie umgeht

---

## Ein Login-Formular automatisieren

**Schritt 1** — Die Credentials-Datei vorbereiten.

Die Credentials-Datei heißt `<hostname>.json`, wobei `hostname` das
Ergebnis von `urlparse(url).hostname` ist. Für `https://app.example.com/`
lautet die Datei `app.example.com.json`.

```json
{"username": "admin@example.com", "password": "my-secret"}
```

**Schritt 2** — Die Login-Seite erkunden.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/login/ --a11y
```

`a11y_tree` lesen, um die Feld-Selektoren zu identifizieren.

**Schritt 3** — Das Szenario schreiben.

```bash
cat > /tmp/login.json << 'EOF'
{
  "nom": "app_login",
  "url": "https://app.example.com/login/",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".user-logged-in"}
  ]
}
EOF
```

**Schritt 4** — Ausführen.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /tmp/login.json
```

---

## Mehrere Seiten in einem einzigen Aufruf validieren

Um N Seiten einer authentifizierten Site zu prüfen, ohne den Login jedes
Mal zu wiederholen:

```bash
cat > /tmp/audit.json << 'EOF'
{
  "nom": "audit_pages",
  "url": "https://app.example.com/login/",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".dashboard-main"},
    {"type": "naviguer",     "url": "https://app.example.com/dashboard/"},
    {"type": "attendre_navigation"},
    {"type": "naviguer",     "url": "https://app.example.com/settings/"},
    {"type": "attendre_navigation"}
  ]
}
EOF
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py --scenario /tmp/audit.json
```

---

## Einen Wert aus der Seite extrahieren

Um einen Textstring, einen Zähler oder einen beliebigen DOM-Wert zu lesen:

```bash
cat > /tmp/extract.json << 'EOF'
[{"type": "evaluer", "script": "document.title"}]
EOF
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --actions /tmp/extract.json
# → Ergebnis in evaluations[0].valeur
```

Für bereinigten dokumentarischen Text (Formulare und Rauschtags entfernt)
stattdessen `extraire_texte` verwenden — die Ausgabe ist eine
`titre`/`texte`/`url`/`date_capture`-Struktur, die ein
zusammenfassender Agent direkt konsumieren kann.

**Wichtig**: JS-Skripte immer in eine `--actions`-Datei schreiben, nie
inline mit `--action` (die Shell beschädigt verschachtelte
Anführungszeichen).

---

## Kontinuierliche strukturelle Überwachung einrichten (v1.18.0)

Dinoer hat keine visuelle Pipeline — Überwachung ist *strukturell*: Sie
prüft den Statuscode der Seite, DOM-Elementzahlen und
JS-Auswertungsergebnisse. Das ist günstiger als Bildvergleich und erfasst
eine andere Klasse von Regression (zum Beispiel ein verschwundenes
Formularfeld bei unverändertem Layout).

```bash
# 1. Einmalig eine strukturelle Referenz speichern
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --sauver-verifier-reference /opt/dinoer/references/my-scenario.ref.json

# 2. Ein Prüf-und-Alarm-Durchlauf
bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --reference /opt/dinoer/references/my-scenario.ref.json \
  --ntfy-topic dinoer-monitoring
```

Still bei Stabilität, ein `ntfy`-Push, wenn eine Regression erkannt wird.
Planen Sie es selbst mit cron — das Skript führt einen Durchlauf aus und
beendet sich, es läuft nicht in einer Schleife. `scripts/*.sh` wird nie
nach `/opt/dinoer/` deployt, daher läuft der Cron-Eintrag aus der
Git-Quelle, als Ihr eigener Benutzer (nicht das `dinoer`-Dienstkonto, das
`~/git/Dinoer/Dinoer/` nicht erreichen kann):

```bash
# crontab -e (Ihre eigene Crontab)
*/15 * * * * bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --reference /opt/dinoer/references/my-scenario.ref.json \
  --ntfy-topic dinoer-monitoring \
  >> /var/log/dinoer/cron-structural.jsonl 2>&1
```

---

## Häufige Stolperfallen

| Situation | Was zu tun ist |
|---|---|
| `FileNotFoundError` bei der Credentials-Datei | Prüfen, dass die JSON-Datei mit dem vollständigen FQDN benannt ist (`urlparse(url).hostname`) |
| `SecretsFermesError` (Exit 42) | Das verschlüsselte Verzeichnis mounten: `bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh` |
| Ungültiges JSON in der Ausgabe | `2>/dev/null \| tail -1` verwenden, um nur die JSON-Zeile zu extrahieren |
| Login gefolgt von Django-Redirect zum Dashboard | `naviguer` nicht in einer wiederaufgenommenen Django-Sitzung verwenden — die URL über `--url` übergeben |
| `<select>`-Formularfeld nicht ausgefüllt | `remplir` mit `selecteur` verwenden, dann auf die Option `cliquer`, oder über `evaluer` steuern |
| Klick hat keine Wirkung auf eine Schaltfläche außerhalb des sichtbaren Bereichs | `{"type":"defiler","selecteur":"#the-button"}` vor dem Klick hinzufügen |
| `auth_status: "active"` auch auf der Login-Seite | Positiver Selektor ist mehrdeutig (persistente Kopfzeile) — `--auth-indicator-negative .btn-login` hinzufügen |
| Web Components blockieren einen normalen Selektor | `cliquer_iframe`/`remplir_iframe` mit explizitem Selektor verwenden, oder über `evaluer` in die Shadow Root greifen |
| `respect.waf_bloquants` erscheint auf einer Seite, die tatsächlich nicht blockiert ist | Erkennung ist schlüsselwortbasiert (v1.16.0, verfeinert in v1.17.2) — als Signal behandeln, nicht als Urteil. Bleibt es auf einer bestätigt nicht blockierten Seite bestehen, `--ignorer-waf` hinzufügen |
| `cliquer` klickt auf das falsche Element einer Seite, die sich verändert hat | Reihenfolgestabile Selektoren bevorzugen, oder den Baum vor dem Klick mit einem frischen `--a11y`-Aufruf neu lesen |
| Ein langes RPA-Szenario schlägt auf halbem Weg fehl, und Sie wollen abgeschlossene Schritte nicht wiederholen | `--checkpoint DATEI` hinzufügen (v1.17.0) — denselben Befehl erneut starten, um fortzusetzen; DOM-Zustand bleibt nicht erhalten, nur Sitzung + Aktionsposition |
| Interaktive Elemente innerhalb eines iframes sind für den Baum unsichtbar | `cliquer_iframe`/`remplir_iframe` (v1.17.0) mit explizitem CSS-Selektor verwenden, oder `iframe_chemin` (v1.18.0) für ein in einem anderen verschachteltes iframe |
| Ihr Modell meldet `"erreur": "guide_non_lu"` / Exit 1 beim ersten Dinoer-Aufruf | Erwartet beim ersten Mal, dass ein Modell Dinoer auf dieser Maschine als dieser Betriebssystembenutzer nutzt (v1.18.0) — es muss `docs/GUIDE_LLM.md` lesen und einmalig `--guide-version` übergeben. Das ist beabsichtigt, kein Fehler — dem Modell sagen, den Leitfaden zu lesen, statt den Fehler zu umgehen |

---

## Dinoer deinstallieren

Das Skript `~/git/Dinoer/Dinoer/scripts/uninstall.sh` entfernt die
Installation sauber, in umgekehrter Reihenfolge zu `install.sh`.

```bash
# Zeigen, was entfernt würde, ohne etwas zu tun
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --dry-run

# Vollständige Deinstallation (interaktive Bestätigung)
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh

# Ohne Bestätigung (Kalttests, verkettete Neuinstallation)
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --confirme && bash ~/git/Dinoer/Dinoer/scripts/install.sh
```

**Was entfernt wird:**

| Element | Detail |
|---|---|
| `/opt/dinoer/` | Code, Python-venv, Konfiguration |
| `/var/log/dinoer/` | Vorgangsprotokolle |
| Systembenutzer `dinoer` | Exklusiv für Dinoer erstellt |
| Systemgruppe `dinoer` | Dasselbe |
| Gruppenmitgliedschaft | Ihr Konto wird aus der Gruppe `dinoer` entfernt |
| Git-Pre-Push-Hook | `core.hooksPath` im Quell-Repository deaktiviert |

**Was nie angerührt wird:**
- `~/Vaults/` — Ihre Credentials
- `~/git/Dinoer/` — Git-Quellen
- Playwright-Browser-Cache (`~/.cache/ms-playwright/`)

**Strukturierte Beweise (`/var/log/dinoer/preuves/`):** Enthält das
Verzeichnis Erfassungen, wird es standardmäßig mit einer Warnung
beibehalten. Zum Entfernen:

```bash
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --confirme --purge-preuves
```

---

## Die Vorgangshistorie einsehen

```bash
# Alle Vorgänge zu einem Ziel
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local

# Nur mutierende Vorgänge (Klicks, Formulareingabe)
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local --mutatif

# Ab einem Datum
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local \
  --depuis 2026-06-01
```
