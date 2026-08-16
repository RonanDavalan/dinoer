# Dinoer — Betriebshandbuch

**Version 1.0.0 — August 2026**

Dieses Dokument beantwortet eine Frage: **wie man X mit Dinoer macht**.

> **Wenn Sie Nutzer sind** — keine Befehle nötig. Sagen Sie Ihrem Modell, was Sie auf einer
> Website, einer Webanwendung oder einer Administrationsoberfläche besuchen, beobachten
> oder erreichen möchten. Das Modell liest dieses Handbuch und übersetzt Ihre Absicht in
> die richtigen Aktionen.
>
> **Wenn Sie ein Sprachmodell sind** — dies sind Ihre Befehle. Führen Sie sie direkt aus.

Keine Architekturbeschreibungen. Befehle, die funktionieren.

---

## Inhaltsverzeichnis

1. [Installation prüfen](#1-installation-prüfen)
2. [Eine Seite lesen](#2-eine-seite-lesen)
3. [Respektvolle Navigation (v1.15.0)](#3-respektvolle-navigation-v1150)
4. [Verschlüsseltes Verzeichnis und Credentials](#4-verschlüsseltes-verzeichnis-und-credentials)
5. [Ein RPA-Szenario schreiben und ausführen](#5-ein-rpa-szenario-schreiben-und-ausführen)
6. [Aktionen — vollständige Referenz](#6-aktionen--vollständige-referenz)
7. [Häufige Hindernisse behandeln](#7-häufige-hindernisse-behandeln)
8. [Überwachung — strukturelle Prüfungen](#8-überwachung--strukturelle-prüfungen)
9. [Vorgangsprotokoll](#9-vorgangsprotokoll)
10. [CLI-Flags — Referenz](#10-cli-flags--referenz)
11. [Exit-Codes und Ausgabe](#11-exit-codes-und-ausgabe)

---

## 1. Installation prüfen

```bash
# Günstigste mögliche Prüfung — kein Playwright, keine URL, sofort exit 0 (v1.18.0+)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --version
# → {"outil": "shot.py", "version": "1.0.0"}
```

```bash
# Vollständiger Test in einem Befehl (~3 s)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://example.com --a11y --guide-version 1.3
```

Erwartetes Ergebnis: JSON auf stdout mit `"succes": true`.

**`--guide-version` (v1.18.0+):** `shot.py` und `rpa.py` verweigern die
Ausführung ohne diesen Nachweis — außer ein lokaler Marker aus einem
vorherigen akzeptierten Aufruf existiert bereits
(`~/.config/dinoer/guide_state.json`). Der Wert ist das
`<!-- notice-version: X.Y -->` in Zeile 3 von `docs/GUIDE_LLM.md` — nicht
die Dinoer-Releasenummer. Lesen Sie den aktuellen Wert, statt einem hier
zitierten Wert zu vertrauen: `grep notice-version
/opt/dinoer/docs/GUIDE_LLM.md`. Siehe `docs/GUIDE_LLM.md`, Abschnitt
„Mandatory pre-flight", für den vollständigen Mechanismus und das
Fehlerformat, falls Sie ihn überspringen.

**Sobald der Marker existiert, wird `--guide-version` wieder optional** —
jedes andere Befehlsbeispiel in diesem Handbuch lässt es absichtlich weg,
da ein Marker aus einem beliebigen früheren erfolgreichen Aufruf sie
bereits abdeckt, solange sich `notice-version` von `docs/GUIDE_LLM.md`
seither nicht geändert hat.

```bash
# Installierte Version prüfen
grep "__version__" /opt/dinoer/shot.py
# → __version__ = "1.0.0"

# Prüfen, dass playwright-stealth verfügbar ist (v1.15.0)
/opt/dinoer/venv/bin/python -c "import playwright_stealth; print('stealth OK')"

# Prüfen, dass das verschlüsselte Verzeichnis gemountet ist
ls ~/Vaults/__PROJET__/Dinoer/
# → muss .json-Dateien zeigen, keine leere Liste
```

Gibt `ls ~/Vaults/...` eine leere Liste oder einen Fehler zurück:
→ mounten: `bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh`

### 1a. Installation aus der Quelle (heute der einzige Kanal)

**Es wird noch kein `.deb`-Paket angeboten** — die Paketierung ist bewusst
zurückgestellt, bis sich das Produkt stabilisiert hat. Installation aus
einem Git-Clone:

```bash
git clone https://github.com/RonanDavalan/dinoer.git ~/git/Dinoer/Dinoer
cd ~/git/Dinoer/Dinoer
bash scripts/install.sh
```

`scripts/install.sh` erstellt den Systembenutzer und die Systemgruppe
`dinoer`, das Python-venv, stellt den Code unter `/opt/dinoer/` bereit,
installiert Chromium und führt einen Funktionstest aus (`shot.py --a11y`
gegen eine echte URL). Wenn Sie beabsichtigen, den eigenen Code von Dinoer
zu ändern, bearbeiten Sie dieses Repository und deployen Sie mit
`scripts/deploy.sh`.

Die Konfiguration liegt unter `/opt/dinoer/dinoer.conf` (JSON); der
Schlüssel für das verschlüsselte Secrets-Verzeichnis ist `secrets_dir`.
Projektspezifische Überschreibung über die Umgebungsvariable
`DINOER_CONF` oder `~/.dinoer.conf`.

Deinstallation:

```bash
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --dry-run   # Vorschau, keine Änderungen
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh             # interaktive Bestätigung
```

---

## 2. Eine Seite lesen

### 2a. Schnelles Lesen — Text und Struktur, kein Bild

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y
```

Liefert zurück: `a11y_tree` (Accessibility-Baum — die textuelle Struktur
der Seite), `boussole` (effektive URL, Titel, HTTP-Status). Damit den
Titel lesen, die URL prüfen oder die Seite kartieren, bevor interagiert
wird.

### 2b. Bereinigter Seitentext

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ \
  --action '{"type": "extraire_texte"}'
```

Liefert `extraction_texte` mit `titre`, `texte` (Rauschtags entfernt:
`script`, `style`, `nav`, `header`, `footer`, `aside`, `noscript`), `url`,
`date_capture`. Dies ist Dinoers Text der Seite — nie ein Screenshot.

### 2c. Zuerst die boussole lesen

Jede Ausgabe enthält ein `boussole`-Objekt — vor allem anderen lesen:

```json
"boussole": {
  "url_courante": "https://target.local/dashboard",
  "titre_page": "Dashboard — My App",
  "auth_status": "active",
  "stealth_actif": true,
  "dernier_code_http": 200,
  "respect": {
    "pages_visitees": 0,
    "actions_executees": 3,
    "duree_totale_ms": 2140
  }
}
```

Stimmt `boussole.url_courante` nicht mit Ihrer Erwartung überein: vor
jeder mutierenden Aktion anhalten und untersuchen.

### 2d. `etat` für eine Go/No-Go-Entscheidung lesen (v1.16.0)

Jeder erfolgreiche Lauf enthält ein `etat`-Objekt an der JSON-Wurzel — es
vor jeder mutierenden Aktion lesen, statt `auth_status`,
`respect.plafond_atteint`, `erreurs_js` und `erreurs_console` selbst
manuell abzugleichen:

```json
"etat": {
  "pret_a_agir": true,
  "niveau_confiance": "eleve",
  "raisons": ["aucun signal de friction détecté"]
}
```

Ist `pret_a_agir` `false`: `raisons` auf die Ursache lesen (inaktive
Authentifizierung, Sitzungsdrift, erreichte Navigationsobergrenze oder ein
erkannter WAF-Block), bevor fortgefahren wird.

`etat` prüft nicht, ob URL oder Seiteninhalt Ihrer geschäftlichen
Erwartung entsprechen — dafür `evaluer` mit
`attendu`/`contient`/`motif` (Abschnitt 5d) verwenden.

---

## 3. Respektvolle Navigation (v1.15.0)

### 3a. Stealth-Modus `--stealth`

Manche Sites blockieren Headless-Browser bei
`navigator.webdriver=true`, ohne die Absicht zu prüfen. `--stealth`
entfernt diese automatische technische Markierung.

```bash
# direkt shot.py
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y --stealth

# Über rpa.py
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/my-scenario.json --stealth
```

Wenn aktiv: `boussole.stealth_actif = true` in der JSON-Ausgabe.

**Was `--stealth` verändert:** `navigator.webdriver` wurden entfernt, Plugins, Sprachen und die Plattform wurden normalisiert.
**Was `--stealth` nicht verändert:** Die IP-Adresse, Identität oder Navigationsabsicht des Nutzers.

### 3b. Höflichkeitsverzögerungen und Obergrenzen

Konfiguriert in `/opt/dinoer/dinoer.conf` (Abschnitt `[navigation]`).
Standardwerte sind auch ohne Konfigurationsdatei aktiv (v1.19.0 — D-10):

```json
{
  "secrets_dir": "~/Vaults/__PROJET__/Dinoer",
  "navigation": {
    "min_action_delay_ms": 800,
    "max_pages_par_run": 10,
    "max_actions_par_run": 30
  }
}
```

`min_action_delay_ms`: Mindestverzögerung (ms) zwischen jeder Aktion.
Mitgelieferter Standardwert: 800 ms.

**Lokale Entwicklung — auf `0` setzen:** Der Standardwert von 800 ms
schützt einen unaufmerksamen Betreiber bei seinem *ersten,
unkonfigurierten* Lauf gegen das öffentliche Internet — er hat keinen
Schutzzweck gegen Ihre eigene Entwicklungsmaschine. Den Schlüssel
explizit in Ihrer lokalen `dinoer.conf` setzen. Den Standardwert von
800 ms (oder höher) für jedes über das öffentliche Internet erreichte
Ziel beibehalten.

Die Obergrenzen `max_pages_par_run` und `max_actions_par_run` stoppen den
Lauf bei Überschreitung sauber — die Ausgabe-JSON enthält dann:

```json
"respect": {
  "pages_visitees": 10,
  "actions_executees": 10,
  "duree_totale_ms": 12400,
  "plafond_atteint": "max_pages_par_run"
}
```

### 3c. Wirkungsmetriken

Jeder Lauf gibt `respect` zurück (JSON-Wurzel und innerhalb von
`boussole`):

| Schlüssel | Bedeutung |
|---|---|
| `pages_visitees` | Anzahl ausgeführter Navigationen vom Typ `naviguer` |
| `actions_executees` | Gesamtzahl ausgeführter Szenario-Aktionen |
| `duree_totale_ms` | Gesamtdauer des Laufs |
| `plafond_atteint` | `"max_pages_par_run"` oder `"max_actions_par_run"` bei vorzeitigem Stopp |
| `indice_agressivite` | Verhältnis mutierender Aktionen zur Gesamtzahl — bei offener Exploration unter 0,3 halten |
| `waf_bloquants` | Anzahl als WAF-blockiert markierter Navigationen |

### 3d. Stealth-Benchmark — quantitativ (v1.17.1)

Konkrete Fingerprint-Signale zählen statt visuell zu vergleichen —
dies ist die Methode, mit der der API-Kompatibilitätsfix für
`playwright-stealth` in v1.17.0 verifiziert wurde
(`docs/RETOUR_EXPERIENCE.md` FR-79):

```bash
# Ohne Stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://bot.sannysoft.com --timeout 20000 \
  --actions '[{"type":"evaluer","script":"navigator.webdriver"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.failed\").length"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.passed\").length"}]'

# Mit Stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://bot.sannysoft.com --stealth --timeout 20000 \
  --actions '[{"type":"evaluer","script":"navigator.webdriver"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.failed\").length"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.passed\").length"}]'
```

Die drei Werte in `evaluations[].valeur` lesen: `navigator.webdriver`
sollte von `true` zu `false` wechseln, `td.failed` sollte gegen `0`
fallen. Referenzmessung (v1.17.0-Fix, Sitzung 47): 12 fehlgeschlagen → 0
fehlgeschlagen.

### 3e. WAF-Erkennungssignal (v1.16.0, verfeinert in v1.17.2)

Dinoer markiert einen wahrscheinlichen WAF-Block passiv — HTTP 403/429
oder eine Übereinstimmung eines Titel-/HTML-Schlüsselworts
(`Cloudflare`, `CAPTCHA`, `checking your browser` usw.). Dies ist ein
Signal, nie eine Ausnahme — der Lauf wird normal abgeschlossen:

```json
"respect": {
  "waf_bloquants": 1
}
```

Ist es vorhanden und `> 0`: `etat.niveau_confiance` ist `"faible"` und
`etat.pret_a_agir` ist `false`. Entscheiden Sie selbst, ob Sie mit
`--stealth` erneut versuchen, das Ziel wechseln oder stoppen — Dinoer
bricht den Lauf nicht für Sie ab.

Seit v1.17.2 stimmen generische Herstellernamen (`Cloudflare`,
`Akamai`) nur mit dem Seitentitel überein — der Abgleich mit dem
vollständigen HTML führte zuvor zu Falsch-positiven bei gewöhnlichen
CDN-Ressourcenreferenzen. Bleibt ein Falsch-positiv bestehen,
degradiert `--ignorer-waf` `niveau_confiance`, ohne `pret_a_agir: false`
zu erzwingen (`boussole.waf_ignore_actif: true` protokolliert die
Außerkraftsetzung). Die Erkennung ist schlüsselwortbasiert und kann
Falsch-positive auf Seiten erzeugen, die legitim über Blockierung/
Erkennung diskutieren — als schnelles Signal behandeln, nicht als
sicheres Urteil.

---

## 4. Verschlüsseltes Verzeichnis und Credentials

### 4a. Struktur

Die Credentials leben in einem verschlüsselten Verzeichnis — einem
gocryptfs-Volume — mit einer `.json`-Datei pro Domain.

```
~/Vaults/__PROJET__/Dinoer/
  ├── app.example.com.json         ← Credentials für https://app.example.com/
  ├── admin.example.com.json       ← Credentials für https://admin.example.com/
  └── operations.jsonl             ← Vorgangsprotokoll (v1.15.0)
```

Format der Credentials-Datei:

```json
{
  "username": "admin@example.com",
  "password": "my-password"
}
```

Der Dateiname = `urlparse(url).hostname`. Für
`https://app.example.com/login/` `app.example.com.json` erstellen.
Das Verzeichnis wird über `DINOER_CONF` → `~/.dinoer.conf` →
`/opt/dinoer/dinoer.conf`, Schlüssel `secrets_dir`, aufgelöst.

### 4b. Ein Formular ausfüllen — die absolute Regel

**VERBOTEN — legt das Passwort in der Shell und `/proc` offen:**

```bash
PASS=$(jq -r '.password' ~/Vaults/.../file.json)   # NIEMALS
curl -d "password=$PASS" https://...                 # NIEMALS
```

**KORREKT — Credentials innerhalb von Playwright aufgelöst:**

```json
{"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
{"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"}
```

Werte gelangen nie durch die Shell, die Bash-History, Prozessprotokolle
oder eine Datei.

### 4c. Die Credentials-Datei für einen Lauf wählen

```bash
# Standard-Credentials-Verzeichnis (definiert in dinoer.conf > secrets_dir)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url https://target.local/ --a11y

# Explizite Credentials-Datei (--secrets)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y \
  --secrets /path/to/mounted/directory/creds.json

# Projektspezifisches Credentials-Verzeichnis über .dinoer.conf
export DINOER_CONF=~/git/MyProject/.dinoer.conf
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url https://target.local/ --a11y
```

Inhalt von `~/git/MyProject/.dinoer.conf`:

```json
{"secrets_dir": "../MyProject-secrets"}
```

Der Pfad wird relativ zum Speicherort von `.dinoer.conf` aufgelöst.

**Inhalt der `--secrets`-Datei — `origines_autorisees` seit dem
05.08.2026 zwingend** (breaking change, keine Übergangsfrist): eine
Datei ohne diesen Schlüssel wird vor jedem Lesevorgang zurückgewiesen.

```json
{"username": "operator", "password": "secret", "origines_autorisees": ["target.local"]}
```

`origines_autorisees` listet die Hostnamen, gegen die diese Datei
verwendet werden darf — dasselbe Format wie
`domaine_depuis_url()`: Kleinbuchstaben, kein Schema, kein Port. Ein
Lesevorgang gegen eine Seite, deren Domain nicht in der Liste steht,
wird verweigert (`SecretsOrigineNonAutoriseeError`).

### 4d. TOTP / MFA

Zwei aktive Pfade, beide innerhalb von Playwright aufgelöst (nie ein
eingetippter Code):

```json
{"type": "remplir", "selecteur": "input[name=otp]", "valeur": "depuis_secrets_totp"}
```

Liest den Schlüssel `totp_cle` (Base32-Seed) aus der Credentials-Datei
und berechnet den aktuellen TOTP-Code.

Um den Code über ntfy zu erhalten (Workflow ohne menschliches
Eingreifen):

```json
{"type": "attendre_mfa_ntfy", "selecteur": "input[name=otp]", "timeout": 120}
```

`selecteur` ist der CSS-Selektor des OTP-Felds. Die ntfy-Basis-URL
kommt aus `DINOER_NTFY_URL` (Umgebungsvariable) oder dem Schlüssel
`ntfy.url` von `dinoer.conf`.

### 4e. Integritätsprüfsumme (opt-in, v1.15.0)

Um eine Credentials-Datei gegen stille FUSE-Korruption zu schützen, ein
`checksum`-Feld hinzufügen:

```bash
# Prüfsumme erzeugen
/opt/dinoer/venv/bin/python -c "
import json, hashlib
creds = json.load(open('my_credentials.json'))
fields = {k: creds[k] for k in sorted(['username','password']) if k in creds}
print('sha256:' + hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest())
"
```

Den zurückgegebenen Wert zur Credentials-Datei hinzufügen:

```json
{
  "username": "admin@example.com",
  "password": "my-password",
  "checksum": "sha256:a3f2c1..."
}
```

Stimmt die Prüfsumme nicht überein, wirft `shot.py`
`SecretsChecksumError` (Exit 42) mit einer expliziten Meldung. Ohne den
Schlüssel `checksum`: unverändertes Verhalten (striktes Opt-in).

### 4f. Verschlüsseltes Verzeichnis geschlossen — was zu tun ist

```
SecretsFermesError: Le répertoire chiffré Dinoer est initialisé mais non monté.
```

```bash
# Das verschlüsselte Verzeichnis mounten
bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh

# Das Mounten prüfen
ls ~/Vaults/__PROJET__/Dinoer/
# → muss JSON-Dateien zeigen
```

### 4g. HTTP Basic Auth — `--http-credentials` (v1.21.0)

Für Ziele hinter einer HTTP-Basic-Auth-Herausforderung auf
Netzwerkebene (RFC 7617) — der Wall, den ein Reverse-Proxy wie Caddy,
nginx oder Traefik errichtet, bevor überhaupt eine Seite gerendert
wird, häufig vor selbstgehosteten Admin-Oberflächen. Dies ist ein
anderer Mechanismus als die formularbasierte Authentifizierung oben
(4a–4f), die vollständig unterstützt und unberührt bleibt.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://internal.example/ \
  --http-credentials --secrets ~/Vaults/__PROJET__/Dinoer/internal_example.json
```

Credentials-Datei — dasselbe einfache
`username`/`password`-Paar, das bereits für den häufigen Fall genutzt
wird (ein einziger Credential-Satz für das Ziel):

```json
{"username": "admin", "password": "my-password"}
```

Die dedizierten Schlüssel `http_username`/`http_password` werden
zuerst versucht und nur benötigt, wenn dasselbe Ziel *sowohl* einen
Basic-Auth-Wall auf Netzwerkebene *als auch* ein eigenes,
separates Anwendungs-Login hat (zwei verschiedene Credential-Paare in
derselben Datei) — Dinoer fällt automatisch auf
`username`/`password` zurück, wenn die dedizierten Schlüssel fehlen.

Bestätigt im Produktivbetrieb gegen ein echtes, Caddy-geschütztes
Ziel: der sichere Standardwert (`send: "unauthorized"` — Credentials
werden erst nach einem echten 401 gesendet, nie vorbeugend) löste die
Herausforderung beim ersten Versuch. `boussole.http_credentials_actif:
true` bestätigt einen echten Erfolg, nicht nur, dass das Flag
übergeben wurde; `boussole.http_auth_requise: true` markiert einen
ungelösten 401 getrennt von einem WAF-Block.

---

## 5. Ein RPA-Szenario schreiben und ausführen

### 5a. 3-Schritte-Protokoll

**Schritt 1 — Die Seite erkunden (schreibgeschützt)**

```bash
# Schnelle Ansicht — Accessibility-Baum
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y

# Vollständiges Lesen — Baum + bereinigter Text
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y \
  --action '{"type": "extraire_texte"}'

# Angereichertes DOM-Inventar (Frameworks, stabile data-Attribute)
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/diagnostic_dom.json \
  --url https://target.local/
```

**Worauf zu achten ist:**
- Stabile Attribute: `name`, `id`, `aria-label`, `data-testid`
- Blockierende Overlays (Cookie-Banner, Modals)
- SPA oder vollständiges HTTP-Reload

**Schritt 2 — Das Szenario schreiben**

```json
{
  "nom": "login_app",
  "url": "https://app.example.com/login/",
  "intention": "Administrator login with stored credentials",
  "actions": [
    {"type": "nettoyer_overlay", "selecteur": ".cookie-banner"},
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".user-avatar"}
  ]
}
```

**Schritt 3 — Ausführen**

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/login_app.json
```

### 5b. Vollständiges Szenario: einloggen und zwischen Seiten navigieren

```json
{
  "nom": "audit_pages",
  "url": "https://app.example.com/login/",
  "intention": "Reading after deployment",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".dashboard-main"},
    {"type": "naviguer", "url": "https://app.example.com/settings/"},
    {"type": "attendre_navigation"},
    {"type": "evaluer", "script": "document.title", "contient": "Settings"},
    {"type": "naviguer", "url": "https://app.example.com/users/"},
    {"type": "attendre_navigation"},
    {"type": "evaluer", "script": "document.querySelectorAll('.user-row').length", "attendu": 12}
  ]
}
```

### 5c. Daten aus dem DOM extrahieren

```json
{
  "nom": "extract_counters",
  "url": "https://app.example.com/dashboard/",
  "actions": [
    {"type": "evaluer", "script": "document.title"},
    {"type": "evaluer", "script": "document.querySelectorAll('.user-row').length"},
    {"type": "evaluer", "script": "window.location.href"}
  ]
}
```

Ergebnis in `evaluations[]`:

```json
"evaluations": [
  {"index": 0, "script": "document.title", "valeur": "Dashboard — My App"},
  {"index": 1, "script": "...", "valeur": 42},
  {"index": 2, "script": "...", "valeur": "https://app.example.com/dashboard/"}
]
```

### 5d. Assertions bei evaluer (nur rpa.py)

Drei sich gegenseitig ausschließende Schlüssel — einer pro Aktion:

```json
{"type": "evaluer", "script": "document.querySelectorAll('.row').length", "attendu": 3}
{"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
{"type": "evaluer", "script": "window.location.href", "motif": "/dashboard$"}
```

| Schlüssel | Vergleich | Gültige Typen |
|---|---|---|
| `attendu` | strikte Gleichheit `==` | str, int, bool |
| `contient` | Teilstring `in` | nur str |
| `motif` | `re.search()` Python | nur str |

Schlägt die Assertion fehl: rpa.py stoppt sofort (Exit 1), bevor eine
folgende mutierende Aktion ausgeführt wird.

### 5e. Unterszenarien (declencher_scenario)

Ein Login als wiederverwendbares Unterszenario definieren:

```json
{
  "nom": "login_app",
  "url": "https://app.example.com/login/",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".user-avatar"}
  ]
}
```

Dieses Unterszenario aus einem anderen Szenario aufrufen:

```json
{
  "nom": "full_audit",
  "url": "https://app.example.com/login/",
  "actions": [
    {"type": "declencher_scenario", "scenario": "login_app"},
    {"type": "naviguer", "url": "https://app.example.com/report/"}
  ]
}
```

Maximale Tiefe: 5 Verschachtelungsebenen. `declencher_scenario` wird
von `rpa.py` flach ausgerollt, bevor die Aktionen `shot.py` erreichen.

### 5f. Vor jeder Mutation prüfen, auf der richtigen Seite zu sein

Immer eine Absicherung als erste Aktion in Szenarien hinzufügen, die
löschen oder ändern:

```json
{"type": "evaluer", "script": "window.location.href", "contient": "/dashboard"},
{"type": "evaluer", "script": "document.querySelector('.alert-danger')?.textContent ?? null", "attendu": null}
```

Schlägt die Absicherung fehl: rpa.py stoppt, bevor die Löschung
ausgeführt wird.

### 5g. Eine Sitzung fortsetzen (persistierte Cookies)

```bash
# Erster Aufruf — authentifizieren und die Sitzung speichern
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/login/ \
  --actions /tmp/login.json \
  --sauver-session /tmp/dinoer/session.json

# Folgeaufrufe — die Sitzung wiederverwenden (kein erneuter Login)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/dashboard/ \
  --reprendre-session /tmp/dinoer/session.json
```

**Sitzungsdrift-Signal:** Ist die Sitzung abgelaufen,
`boussole.session_derive: true` im JSON. In diesem Fall: den
vollständigen Login ohne `--reprendre-session` neu starten.

### 5h. Strukturelle Nicht-Regression — `--replay-verifier` (v1.17.0)

```bash
# Erster Lauf — die strukturelle Referenz speichern
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/dashboard.json \
  --sauver-verifier-reference /tmp/dashboard.ref.json

# Folgeläufe — vergleichen
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/dashboard.json \
  --replay-verifier /tmp/dashboard.ref.json
```

Vergleicht `http_status`, `dom_stats` und `evaluer`-Ergebnisse mit der
gespeicherten Referenz. Urteil auf stderr:

```json
{"type_comparaison": "replay_verifier", "verdict": "stable", "diffs": []}
```

Exit 1 bei `verdict: "regression"`, mit `diffs`, das jedes
abweichende Feld auflistet (`reference` vs. `obtenu`). Die beiden Flags
schließen sich gegenseitig aus.

### 5i. Ein langes Szenario nach einem Fehler fortsetzen — `--checkpoint` (v1.17.0)

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/long_audit.json \
  --checkpoint /tmp/long_audit.checkpoint.json
```

Schlägt das Szenario auf halbem Weg fehl, wird die Checkpoint-Datei mit
der Anzahl abgeschlossener Aktionen und einer Sitzungsdatei geschrieben.
**Denselben Befehl erneut starten**, um fortzusetzen: bereits
abgeschlossene Aktionen werden übersprungen. Bei vollem Erfolg wird die
Checkpoint-Datei automatisch gelöscht.

Ein durch eine Navigationsobergrenze (`max_actions_par_run`/
`max_pages_par_run`) gestoppter Lauf wird seit v1.17.2 genauso
behandelt wie ein teilweiser Fehler — der Checkpoint wird mit dem
tatsächlichen Fortschritt aktualisiert, nicht gelöscht.

Der DOM-Zustand (offene Modals, halb ausgefüllte Formulare) bleibt
über eine Fortsetzung hinweg nie erhalten — nur Cookies/`localStorage`
und die Position in der Aktionsliste. Sich nicht darauf verlassen,
dass `--checkpoint` mitten in einem einzelnen mehrstufigen Formular
fortsetzt; es setzt nur an Aktionsgrenzen fort.

### 5j. Elemente innerhalb eines iframes ansprechen (v1.17.0)

Innerhalb eines iframes (gleicher Ursprung oder Cross-Origin) existiert
keine Elementnummerierung — direkt per CSS-Selektor ansprechen:

```json
{"type": "cliquer_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "button.valider"},
{"type": "remplir_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`remplir_iframe` unterstützt `valeur: "depuis_secrets"` genau wie
`remplir` (Abschnitt 4b) — nie ein Credential im Klartext im Szenario.
Verweigert das Zielelement die Interaktion (z. B. ein
`contenteditable`-Bereich im schreibgeschützten Zustand), `"force":
true` zu `cliquer_iframe` hinzufügen — dieselbe Semantik wie `cliquer`
(Abschnitt 7e).

Um den inneren Selektor zu finden: `evaluer` auf dem Inhalt des
iframes nutzen, wenn er gleichen Ursprungs ist
(`document.querySelector('iframe').contentDocument...`), oder bei
Cross-Origin das eigene Markup/die eigene Dokumentation der
Zielanwendung konsultieren.

### 5k. Verschachtelte iframes — `iframe_chemin` (v1.18.0)

Ein iframe innerhalb eines anderen iframes: `iframe_selecteur` durch
`iframe_chemin` ersetzen, ein geordnetes Array — ein CSS-Selektor pro
Verschachtelungsebene, von außen nach innen.

```json
{"type": "cliquer_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "button.valider"},
{"type": "remplir_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`iframe_selecteur` (einzelner Frame) und `iframe_chemin`
(verschachtelter Abstieg) schließen sich gegenseitig aus — genau einer
ist pro Aktion erforderlich. Für ein einstufiges iframe weiterhin
`iframe_selecteur` verwenden (Abschnitt 5j).

---

## 6. Aktionen — vollständige Referenz

| Typ | Erforderliche Parameter | Optionale Parameter | Hinweise |
|---|---|---|---|
| `naviguer` | `url` | — | Vollständiges HTTP-Reload. Wird in `respect.pages_visitees` gezählt |
| `cliquer` | `selecteur` | `force` (bool), `repli_js` (bool) | `force: true` umgeht CSS-verborgene Elemente oder showModal. `repli_js: true` versucht bei fehlgeschlagenem nativem Klick erneut über JS (v1.22.0) — mit `--no-evaluer` abgelehnt (Exit 2, vor dem Start) |
| `remplir` | `selecteur`, `valeur` | `secret_cle` | `valeur: "depuis_secrets"` erfordert `secret_cle`; `"depuis_secrets_totp"` für TOTP |
| `evaluer` | `script` | `attendu`, `contient`, `motif` | Im Browser ausgeführtes JS. Assertions nur für rpa.py |
| `defiler` | `px` oder `selecteur` | — | Vertikales Scrollen in Pixeln (`px`) oder Scrollen zum Element (`selecteur`) |
| `pause` | `ms` | — | Feste Verzögerung in ms. `attendre_selecteur_present` für DOM-Signale bevorzugen |
| `attendre` | `selecteur` | — | Wartet, dass der CSS-Selektor im DOM vorhanden ist (`state=attached`) |
| `attendre_navigation` | — | — | Wartet auf `networkidle` (Ende der Netzwerkanfragen) |
| `attendre_url` | `motif` | `attendre_changement` (bool) | URL-Teilstring-Abgleich. `attendre_changement: true` wartet zuerst auf eine echte Navigation (siehe die FR-55-Falle) |
| `attendre_selecteur_present` | `selecteur` | — | Wartet, dass das Element sichtbar ist (`state=visible`) |
| `attendre_absence` | `selecteur` | `delai_initial_ms` | Wartet auf Entfernung des Elements aus dem DOM (`state=detached`) |
| `attendre_reseau_calme` | — | `timeout_ms` | 500 ms Netzwerkstille. `timeout_ms`: maximale Dauer, bevor aufgegeben wird |
| `attendre_mfa_ntfy` | `selecteur` | `timeout` | Wartet auf einen TOTP-Code über ntfy, füllt ihn in das Feld |
| `nettoyer_overlay` | `selecteur` | — | Verbirgt blockierende Overlays (Cookie-Banner, Modal) — expliziter Selektor, keine automatische Erkennung |
| `declencher_scenario` | `scenario` | — | Fügt die Aktionen eines Unterszenarios ein. Maximale Tiefe: 5 (rpa.py) |
| `extraire_texte` | — | — | Bereinigter Seitentext aus dem gerenderten DOM — `extraction_texte` (`titre`, `texte`, `url`, `date_capture`) |
| `cliquer_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur` | `force` (bool) | Klick innerhalb eines iframes (v1.17.0). `iframe_chemin` für verschachtelte iframes (v1.18.0, Abschnitt 5k) |
| `remplir_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur`, `valeur` | `secret_cle` | Ausfüllen innerhalb eines iframes (v1.17.0). `valeur: "depuis_secrets"` unterstützt |

---

## 7. Häufige Hindernisse behandeln

### 7a. Cookie-Banner / blockierendes Overlay

```json
{"type": "nettoyer_overlay", "selecteur": ".cookie-consent-banner, #gdpr-overlay"}
```

**Vor** jeder anderen Lese-/Interaktionsaktion platzieren. Das Overlay
maskiert Elemente im Accessibility-Baum.

### 7b. Element außerhalb des sichtbaren Bereichs

Dorthin scrollen (nach Betrag oder nach Selektor), dann handeln:

```json
{"type": "defiler", "selecteur": "#the-button"},
{"type": "cliquer", "selecteur": "#the-button"}
```

oder

```json
{"type": "defiler", "px": 600},
{"type": "cliquer", "selecteur": "button[data-testid='load-more']"}
```

### 7c. SPA (React, Vue, Angular) — navigieren ohne Reload

Nach einem Klick, der die Ansicht in einer SPA ändert, weiß Playwright
nicht, wann die Navigation abgeschlossen ist.

```json
{"type": "cliquer", "selecteur": "a[href*='/dashboard']"},
{"type": "attendre_url", "motif": "/dashboard"},
{"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
```

Nie annehmen, dass ein Klick die Navigation ohne DOM-Signal
abgeschlossen hat. Nach einem Submit `attendre_url` mit
`attendre_selecteur_present` kombinieren (Teilstring-Abgleich-Falle,
siehe `docs/GUIDE_LLM_INTERACTIONS.md`).

### 7d. CSS-Dialog oder showModal()

`TimeoutError` bei `cliquer`, obwohl das Element im DOM sichtbar ist =
CSS-verborgenes Element oder innerhalb eines Dialogs.

```json
{"type": "cliquer", "selecteur": "#dialog-confirm button[type=submit]", "force": true}
```

Reicht `force: true` nicht aus (Interaktionsfähigkeits-/Obstruktionsfehler):
`repli_js: true` zur selben Aktion hinzufügen (v1.22.0), oder auf JS
zurückgreifen:

```json
{"type": "evaluer", "script": "document.querySelector('#dialog-confirm button[type=submit]').click()"}
```

### 7e. Lange Operation (Spinner, Batch-Job)

`pause` nicht verwenden, um eine feste Dauer abzuwarten. Auf das
DOM-Signal warten:

```json
{"type": "cliquer", "selecteur": "button[data-testid='run-job']"},
{"type": "attendre_absence", "selecteur": ".spinner", "delai_initial_ms": 500},
{"type": "attendre_selecteur_present", "selecteur": ".result-container"}
```

Liefert die Operation kein DOM-Signal, den Zustand mit `evaluer`
abfragen und fortfahren, sobald der Beleg vorliegt.

### 7f. Obergrenze erreicht (v1.15.0)

Ist `respect.plafond_atteint` in der Ausgabe vorhanden, wurde der Lauf
gestoppt, bevor das Szenario abgeschlossen war. Verbleibende Aktionen
wurden nicht ausgeführt.

Optionen:
1. `max_pages_par_run` oder `max_actions_par_run` in `dinoer.conf`
   erhöhen
2. Das Szenario auf mehrere Läufe aufteilen
3. Einen Teilabschnitt mit `--checkpoint` fortsetzen

### 7g. `<select>`-Formularfeld

`remplir` (`.fill()`) funktioniert nicht bei `<select>`. Einen
JS-Setter über `evaluer` verwenden:

```json
{"type": "evaluer", "script": "(() => { const s = document.querySelector('select[name=role]'); s.value='admin'; s.dispatchEvent(new Event('change',{bubbles:true})); })()"}
```

### 7h. Von WAF blockierte Site (sofortiger 403)

```bash
# Mit Stealth versuchen
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y --stealth
```

Bleibt 403 mit `--stealth` bestehen: Die Site nutzt TLS-Fingerprinting
(JA3/JA4) oder fortgeschrittene Verhaltensanalyse (Cloudflare
Enterprise). `playwright-stealth` umgeht diese Schutzmaßnahmen nicht.
Siehe `docs/RETOUR_EXPERIENCE.md` FR-77/FR-78/FR-79 für den Kontext.

Dinoer markiert auch passiv einen wahrscheinlichen Block — siehe
Abschnitt 3e (`respect.waf_bloquants`).

### 7i. Initiale Navigation schließt nie ab — `--wait-until` (v1.22.0)

Symptom: `TimeoutError` bei der initialen Navigation, und das Erhöhen
von `--timeout` ändert nichts (45 s scheitert genauso wie 10 s).
Ursache: Standardmäßig wartet Dinoer auf `networkidle` — 500 ms
Netzwerkstille. Eine Seite, die kontinuierlich abfragt (Live-Statistiken,
automatisch aktualisierende Zähler, Router-Admin-Panels), erzeugt diese
Stille nie, sodass kein Timeout-Wert je groß genug sein kann.

```bash
# shot.py — direkte Erkundung
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url http://target.local/ --wait-until load --a11y

# rpa.py — an shot.py weitergereicht, sodass Szenarien dieselben Ziele erreichen
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario ./admin_login.json --wait-until load
```

Ein Szenario kann es stattdessen als Wurzeleigenschaft tragen und
dadurch in sich geschlossen bleiben:

```json
{"url": "http://target.local/", "wait_until": "load", "actions": [...]}
```

Das CLI-Flag hat Vorrang vor der Szenario-Eigenschaft.

| Wert | Wartet auf | Verwenden, wenn |
|---|---|---|
| `networkidle` | 500 ms Netzwerkstille | Standard — beibehalten, sofern kein Fehlschlag |
| `load` | `load`-Ereignis (Seite und Unterressourcen) | kontinuierliches Abfragen / Live-Statistiken |
| `domcontentloaded` | HTML geparst, Unterressourcen noch ausstehend | sehr schwere Seite, nur der DOM wird benötigt |

Gilt nur für die initiale Navigation — die Aktion `naviguer` ist
unberührt. `boussole.wait_until` meldet den Wert nur, wenn er vom
Standard abweicht.

---

## 8. Überwachung — strukturelle Prüfungen

In Dinoer existiert keine bildbasierte Überwachung (kein visueller
Diff). Strukturelle Prüfungen sind textbasiert und CI-freundlich.

### 8a. Kontinuierliche strukturelle Überwachung — `scripts/monitor-verifier.sh` (v1.18.0)

Überwacht *Struktur* (`http_status`, `dom_stats`, `evaluations`) —
null Bild, null LLM-Aufruf, aufgebaut auf `--replay-verifier`
(Abschnitt 5h).

```bash
# Erster Lauf — die strukturelle Referenz erstellen
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/sillage_login.json \
  --sauver-verifier-reference /opt/dinoer/references/sillage_login.ref.json

# Ein Prüf-und-Alarm-Durchlauf — kein Daemon, wiederholt über cron ausführen.
# scripts/*.sh wird nie nach /opt/dinoer/ deployt, läuft also aus der
# Git-Quelle, als Ihr eigener Benutzer.
bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/sillage_login.json \
  --reference /tmp/ref_sillage.json \
  --ntfy-topic dinoer-monitoring
```

```bash
# crontab -e (Ihre eigene Crontab)
*/15 * * * * bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/sillage_login.json \
  --reference /opt/dinoer/references/sillage_login.ref.json \
  --ntfy-topic dinoer-monitoring \
  >> /var/log/dinoer/cron-structural.jsonl 2>&1
```

Stabil → Stille. Regression → eine `ntfy`-Benachrichtigung mit dem
Diff. Jeder Aufruf ist ein isolierter Prozess — kein Daemon, kein
Speicherleck-Risiko, und die Obergrenzen der respektvollen Navigation
werden bei jedem Durchlauf sauber zurückgesetzt.

**Bekannte Schuld (v1.23.0):** Das Skript ruft `rpa.py --no-capture
--replay-verifier` auf, aber `--no-capture` ist kein `rpa.py`-Flag
mehr. Es ist semantisch redundant (Dinoer hat keinen Bildpfad), lässt
das Skript aber derzeit an argparse scheitern. Nicht darauf verlassen,
wie es dasteht, bis korrigiert.

**Nuance des Guide-Read-Locks:** Wird es unter einem separaten
Betriebssystembenutzer aufgerufen (z. B. ein Systemdienstkonto), muss
dieser Benutzer `--guide-version` einmalig validiert haben
(`~<home>/.config/dinoer/guide_state.json`).

---

## 9. Vorgangsprotokoll

Das Protokoll ist `/var/log/dinoer/operations.jsonl`. Liegt der
konfigurierte Protokollpfad innerhalb des verschlüsselten Verzeichnisses
und ist es nicht gemountet, werden Einträge zu einem lokalen Fallback
umgeleitet (degradiertes Schreiben, 700/600), statt im Klartext auf dem
rohen Host geschrieben zu werden.

```bash
# Die letzten 10 Einträge lesen
tail -n 10 /var/log/dinoer/operations.jsonl | python3 -m json.tool

# Nach Ziel filtern (journal.py-Werkzeug)
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com

# Nur mutierende Vorgänge filtern
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --mutatif

# Ab einem Datum
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --depuis 2026-07-01

# Nur fehlgeschlagene Läufe (v1.20.0) — resultat != success
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --erreurs
```

Felder in jedem Eintrag:

| Feld | Bedeutung |
|---|---|
| `ts` | ISO-8601-Zeitstempel |
| `version` | Dinoer-Version |
| `mode` | `shot.py` oder `rpa.py` |
| `cible_url` | Ziel-URL |
| `scenario` | Pfad der Szenariodatei (RPA-Modus) |
| `source_scenario` | nur der Dateiname des Szenarios, kein Pfad (v1.18.0) |
| `resultat` | `"succes"` oder `"echec"` |
| `mutatif` | `true`, wenn mindestens eine Schreibaktion |
| `respect` | das Navigationskonto des Laufs |
| `evaluations` | bereinigte `{script, valeur_retournee}`-Werte |
| `duree_ms` | Dauer in ms |
| `intention` | über `--intention` oder das Szenariofeld `intention` übergebenes Label |

### 9a. Log-Rotation (G-36)

Dinoer liefert keine logrotate-Konfiguration —
`/var/log/dinoer/operations.jsonl` wächst unbegrenzt, bis der
Administrator eine installiert. `lib/journal.py` öffnet und schließt
die Datei bei jedem Schreibvorgang (kein persistenter Dateideskriptor
über Läufe hinweg), genau damit das **Standard**-Verhalten von
logrotate (aktuelle Datei umbenennen, eine neue erstellen) ohne jede
besondere Option korrekt funktioniert: Der nächste Schreibvorgang
öffnet den Pfad erneut und findet die neue Inode.

**Kein `copytruncate`** zu einer Dinoer-logrotate-Konfiguration
hinzufügen — es ist hier unnötig und führt ein Zeitfenster für
Schreibverlust wieder ein. Beispiel `/etc/logrotate.d/dinoer`:

```
/var/log/dinoer/operations.jsonl {
    weekly
    rotate 8
    compress
    delaycompress
    missingok
    notifempty
    create 0640 dinoer dinoer
}
```

`journal.py` (der Leser) folgt rotierten Dateien bereits transparent
(`operations.jsonl`, `.1`, `.2.gz`, …) — nach der Rotation ist kein
weiterer Schritt nötig.

---

## 10. CLI-Flags — Referenz

### shot.py

| Flag | Standard | Beschreibung |
|---|---|---|
| `--version` | — | Gibt die installierte Version aus und beendet sich sofort — kein Playwright, kein weiteres Argument erforderlich (v1.18.0) |
| `--guide-version X.Y` | — | Nachweis, `docs/GUIDE_LLM.md` gelesen zu haben — erforderlich, außer ein gültiger lokaler Marker existiert bereits (v1.18.0, Abschnitt 1) |
| `--url URL` | erforderlich | zu erfassende URL |
| `--actions DATEI` | — | JSON-Datei mit sequenziellen Aktionen |
| `--action JSON` | — | Einzelne Aktion als Inline-JSON — sorgfältig quoten, bei JS-lastigen Aktionen `--actions DATEI` bevorzugen |
| `--attendre-selecteur SEL` | — | Vor Abschluss des Laufs auf einen Selektor warten |
| `--timeout MS` | 10000 | Playwright-Timeout pro Aktion (ms) |
| `--wait-until WERT` | `networkidle` | `networkidle`\|`load`\|`domcontentloaded` — nur initiale Navigation (v1.22.0, Abschnitt 7i) |
| `--largeur PX` | 1280 | Viewport-Breite |
| `--hauteur PX` | 720 | Viewport-Höhe |
| `--a11y` | aus | Accessibility-Baum im JSON einschließen |
| `--stealth` | aus | playwright-stealth-Modus (v1.15.0) |
| `--secrets DATEI` | — | expliziter Pfad zu einer Credentials-Datei |
| `--auth-indicator SEL` | — | CSS-Selektor, der nur in authentifizierter Sitzung vorhanden ist |
| `--auth-indicator-negative SEL` | — | erfordert `--auth-indicator`; CSS-Selektor, der nur außerhalb der authentifizierten Sitzung vorhanden ist |
| `--ignorer-waf` | aus | Ein erkannter WAF-Block degradiert `niveau_confiance`, erzwingt aber nicht mehr allein `pret_a_agir: false` (v1.17.2, Abschnitt 3e) |
| `--http-credentials` | aus | Löst HTTP-Basic-Auth-Credentials aus der Credentials-Datei auf, begrenzt auf den Ursprung des Ziels (v1.21.0, Abschnitt 4g) |
| `--ignore-tls-errors` | aus | Ungültiges TLS auf kontrollierten LAN-/Dev-Zielen akzeptieren — nie im öffentlichen Internet (v1.15.1) |
| `--no-evaluer` | aus | Verweigert die Aktion **evaluer** (und `repli_js`) für den gesamten Lauf — empfohlen bei sensiblen Formularen (v1.15.1) |
| `--no-filtre-evaluer` | aus | Deaktiviert die stdout-Neutralisierung von **evaluer**-Rückgabewerten, URLs und Fehlermeldungen — nur für explizite Debug-Läufe; deaktiviert wird `boussole.filtre_evaluer_actif: false` gesetzt (v1.23.0) |
| `--intention TEXT` | — | im Protokoll erfasstes geschäftliches Label |
| `--sauver-session DATEI` | — | speichert Cookies nach den Aktionen |
| `--reprendre-session DATEI` | — | setzt eine gespeicherte Sitzung fort |
| `--source-scenario NAME` | — | intern (rpa.py-Verrohrung für das Protokoll — nicht für direkte Aufrufe) |
| `--chainage JSON` | — | intern (rpa.py-Verrohrung für das Protokoll — nicht für direkte Aufrufe) |

### rpa.py

Reicht alle relevanten shot.py-Flags weiter, plus:

| Flag | Beschreibung |
|---|---|
| `--version` | gibt die installierte Version aus und beendet sich sofort (v1.18.0) |
| `--guide-version X.Y` | Nachweis, `docs/GUIDE_LLM.md` gelesen zu haben — unabhängig geprüft, dieselbe Regel wie shot.py (v1.18.0) |
| `--scenario DATEI` | Pfad zu JSON- oder YAML-Szenario (erforderlich) |
| `--url URL` | überschreibt die Szenario-URL, ohne die Datei zu ändern |
| `--stealth` | an shot.py weitergereicht |
| `--wait-until` | an shot.py weitergereicht (v1.22.0, Abschnitt 7i) |
| `--ignorer-waf` | an shot.py weitergereicht (v1.17.2, Abschnitt 3e) |
| `--http-credentials` | an shot.py weitergereicht; auch als Szenario-Wurzeleigenschaft `"http_credentials": true` setzbar (v1.21.0, Abschnitt 4g) |
| `--auth-indicator-negative` | erfordert einen `auth_indicator` (CLI oder Szenario-Wurzeleigenschaft) |
| `--sauver-verifier-reference DATEI` | speichert die strukturelle Referenz für `--replay-verifier` (v1.17.0, Abschnitt 5h) |
| `--replay-verifier DATEI` | vergleicht den Lauf mit einer strukturellen Referenz, Exit 1 bei Regression (v1.17.0, Abschnitt 5h) |
| `--checkpoint DATEI` | setzt ein langes Szenario nach einem Fehler mitten im Lauf fort (v1.17.0, Abschnitt 5i) |

### campagne.py (Recherche-Pipeline)

| Flag | Beschreibung |
|---|---|
| `--manifeste DATEI` | Kampagnen-Manifest (JSON) — erfordert `id_campagne` + `cibles` |
| `--id-campagne ID` | Kampagnen-Kennung (im Manifest und der Extraktion verwendet) |
| `--extraire-cible ANFRAGE` | gezielte Extraktion auf einem bereits gesammelten Korpus, ohne Synthese |
| `--desactiver-cache` | den Suchcache umgehen |
| `--purger-cache` | den gesamten Suchcache leeren |
| `--purger-cache-avant-jours N` | Cache-Einträge älter als N Tage leeren |

Zieltypen im Manifest: `query`, `url`, `produit`, `table_reference`.
Artefakte: das geteilte `/var/log/dinoer/operations.jsonl` + eine
kampagnenspezifische `collecte.jsonl`. Vollständiges Detail:
`campagne.py --help`.

---

## 11. Exit-Codes und Ausgabe

### Exit-Codes

| Code | Ursache | Was zu tun ist |
|---|---|---|
| 0 | Erfolg | — |
| 1 | Playwright-Fehler, fehlgeschlagene Aktion, rpa.py Assertion, `action_secret_en_clair` | Lesen Sie `erreur` im JSON. Sehen Sie sich `GUIDE_LLM_INTERACTIONS.md` an. |
| 1 | `guide_non_lu` – Fehlende/falsche `--guide-version`, kein gültiger Marker (v1.18.0) | Wird vor dem Start von Playwright ausgelöst. Lesen Sie `docs/GUIDE_LLM.md`, starten Sie neu mit `--guide-version X.Y` (Abschnitt 1). |
| 2 | Inkompatible Argumente, `arguments_incompatibles`, `url_scheme_interdit`, `chemin_sensible_refuse` | Lesen Sie `message` – es benennt den Konflikt. |
| 3 | Modul `playwright` nicht gefunden | Aufrufen über `/opt/dinoer/venv/bin/python`. |
| 42 | `SecretsFermesError` – Verschlüsseltes Verzeichnis nicht gemountet oder ungültige Prüfsumme | Mounten Sie es, oder überprüfen Sie die Anmeldedatei. |
| 43 | `SecretsNonConfigureError` – Kein `secrets_dir` konfiguriert | Konfigurieren Sie `secrets_dir` in `dinoer.conf` (`undo` ein fehlendes Beispiel: erstellen Sie `/opt/dinoer/dinoer.conf`). |

### Struktur der Ausgabe-JSON

```json
{
  "succes": true,
  "http_status": 200,
  "url_finale": "https://target.local/dashboard",
  "erreurs_js": [],
  "erreurs_console": [],
  "duree_ms": 2400,
  "horodatage": "2026-07-01T12:00:00+02:00",
  "dom_stats": {"boutons": 14, "inputs": 9, "listes_deroulantes": 2, "formulaires": 1, "liens": 41, "dialogues": 0},
  "a11y_tree": "...",
  "evaluations": [],
  "extraction_texte": null,
  "latences_actions": [
    {"index": 0, "type": "naviguer", "latence_ms": 842},
    {"index": 1, "type": "cliquer", "latence_ms": 63}
  ],
  "respect": {
    "pages_visitees": 0,
    "actions_executees": 3,
    "duree_totale_ms": 2400,
    "indice_agressivite": 0.33
  },
  "etat": {
    "pret_a_agir": true,
    "niveau_confiance": "eleve",
    "raisons": ["aucun signal de friction détecté"]
  },
  "boussole": {
    "utilisateur": "operator",
    "ip_locale": "__IP_LAN__",
    "repertoire": "/opt/dinoer",
    "operation_id": "a1b2c3d4e5f6",
    "url_courante": "https://target.local/dashboard",
    "titre_page": "Dashboard — My App",
    "dernier_code_http": 200,
    "stealth_actif": true,
    "auth_status": "active",
    "respect": { "pages_visitees": 0, "actions_executees": 3, "duree_totale_ms": 2400, "indice_agressivite": 0.33 }
  },
  "dinoer_meta": {
    "version_shot": "1.0.0",
    "horodatage_iso": "2026-08-12T14:23:11+02:00",
    "hostname_executant": "operator-host",
    "utilisateur_executant": "operator",
    "profil_actif": "operateur.exemple.yaml",
    "url_au_moment_capture": "https://target.local/dashboard"
  }
}
```

`operation_id` (v1.16.0) ist immer vorhanden und identifiziert diesen
Lauf eindeutig — er benennt das Isolationsverzeichnis unter
`/tmp/dinoer/<operation_id>/` und stimmt mit dem `operation_id`-Feld
des Eintrags dieses Laufs im Vorgangsprotokoll überein (Abschnitt 9).
`etat` (v1.16.0) ist nur auf dem Erfolgspfad vorhanden.
`latences_actions` (v1.20.0) ist immer vorhanden (leere Liste ohne
Aktionen), ein Eintrag pro tatsächlich abgesetzter Aktion — siehe
`GUIDE_LLM_MONITORING.md`, wie es `respect.duree_totale_ms` ergänzt.

Bedingte Schlüssel (fehlen, wenn inaktiv): `dom_stats`, `a11y_tree`,
`evaluations`, `extraction_texte`, `auth_status`, `stealth_actif`,
`session_derive`, `respect.plafond_atteint`, `respect.waf_bloquants`,
`respect.indice_agressivite` (vorhanden, sobald mindestens eine Aktion
lief), `boussole.repli_js_utilise`, `boussole.wait_until`,
`boussole.http_credentials_actif`, `boussole.http_auth_requise`,
`boussole.tls_errors_ignored`, `boussole.waf_ignore_actif`,
`boussole.filtre_evaluer_actif`, `boussole.champs_rediges`,
`actions_executees_avant_echec`, `pages_visitees_avant_echec` (nur
Fehler-JSON, v1.17.0). Siehe `GUIDE_LLM_MONITORING.md` für die
vollständige Aktivierungstabelle.

### Fehler — Format

```json
{
  "succes": false,
  "erreur": "secrets_fermes",
  "message": "Le répertoire chiffré Dinoer est initialisé mais non monté.",
  "code_sortie_recommande": 42,
  "boussole": { "url_courante": "", "titre_page": "" }
}
```

---

## Referenzpfade

| Pfad | Rolle |
|---|---|
| `/opt/dinoer/` | Produktivinstallation |
| `/opt/dinoer/venv/bin/python` | für jeden Aufruf zu verwendendes Python |
| `/opt/dinoer/dinoer.conf` | Maschinenkonfiguration (secrets_dir, navigation, ntfy) |
| `/opt/dinoer/scenarios/` | RPA-Szenarien (einschließlich `diagnostic_dom.json`) |
| `/opt/dinoer/docs/` | Dokumentation |
| `/opt/dinoer/references/` | Referenzen für `--sauver-verifier-reference` / Replay |
| `/tmp/dinoer/<operation_id>/` | temporäre Sitzungsdaten für einen Lauf, isoliert nach `operation_id` (v1.16.0, beim Neustart gelöscht) |
| `~/Vaults/__PROJET__/Dinoer/` | Credentials + Protokoll (gocryptfs-Volume) |
| `~/git/Dinoer/Dinoer/` | Git-Quellen (hier bearbeiten, dann `deploy.sh`) |
| `/var/log/dinoer/operations.jsonl` | persistentes Vorgangsprotokoll (`journal.py`) |

Nach Änderung der Quellen deployen:

```bash
bash ~/git/Dinoer/Dinoer/scripts/deploy.sh
```
