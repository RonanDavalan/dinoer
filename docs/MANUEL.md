# Dinoer — Operational manual

**Version 1.0.0 — August 2026**

This document answers one question: **how to do X with Dinoer**.

> **If you are a user** — no commands needed. Tell your model what you want to visit,
> observe, or accomplish on a website, a web application, or an administration interface.
> The model reads this manual and translates your intent into the right actions.
>
> **If you are a language model** — these are your commands. Execute them directly.

No architectural descriptions. Commands that work.

---

## Table of contents

1. [Verify the installation](#1-verify-the-installation)
2. [Read a page](#2-read-a-page)
3. [Respectful navigation (v1.15.0)](#3-respectful-navigation-v1150)
4. [Encrypted directory and credentials](#4-encrypted-directory-and-credentials)
5. [Write and run an RPA scenario](#5-write-and-run-an-rpa-scenario)
6. [Actions — complete reference](#6-actions--complete-reference)
7. [Handle common obstacles](#7-handle-common-obstacles)
8. [Monitoring — structural checks](#8-monitoring--structural-checks)
9. [Operation log](#9-operation-log)
10. [CLI flags — reference](#10-cli-flags--reference)
11. [Exit codes and output](#11-exit-codes-and-output)

---

## 1. Verify the installation

```bash
# Cheapest possible check — no Playwright, no URL, exit 0 immediately (v1.18.0+)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --version
# → {"outil": "shot.py", "version": "1.0.0"}
```

```bash
# Full test in one command (~3 s)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://example.com --a11y --guide-version 1.3
```

Expected result: JSON on stdout with `"succes": true`.

**`--guide-version` (v1.18.0+):** `shot.py` and `rpa.py` refuse to run
without it — unless a local marker from a previous accepted call already
exists (`~/.config/dinoer/guide_state.json`). The value is the
`<!-- notice-version: X.Y -->` on line 3 of `docs/GUIDE_LLM.md` — not the
Dinoer release number. Read the current one rather than trusting any value
quoted here: `grep notice-version /opt/dinoer/docs/GUIDE_LLM.md`. See
`docs/GUIDE_LLM.md` section "Mandatory pre-flight" for the full mechanism and
the error format if you skip it.

**Once the marker exists, `--guide-version` becomes optional again** — every
other command example in this manual omits it deliberately, since a marker
from any earlier successful call already covers them, as long as
`docs/GUIDE_LLM.md`'s `notice-version` has not changed since.

```bash
# Verify the installed version
grep "__version__" /opt/dinoer/shot.py
# → __version__ = "1.0.0"

# Verify playwright-stealth is available (v1.15.0)
/opt/dinoer/venv/bin/python -c "import playwright_stealth; print('stealth OK')"

# Verify the encrypted directory is mounted
ls ~/Vaults/__PROJET__/Dinoer/
# → must show .json files, not an empty list
```

If `ls ~/Vaults/...` returns an empty list or an error:
→ mount it: `bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh`

### 1a. Installing

Two channels, mutually exclusive on one machine.

**`.deb` package** — the normal path if you want to use Dinoer as-is:

```bash
sudo apt install ./dinoer_1.0.0-1_all.deb
```

Package, sources and checksums are published on
[dinoer.davalan.fr](https://dinoer.davalan.fr/en/guides/downloads/).
Configuration lives at `/etc/dinoer/dinoer.conf` (JSON, commented sample
installed beside it as `dinoer-sample.conf`).

**Git clone** — if you intend to modify Dinoer's own code:

```bash
git clone https://github.com/RonanDavalan/dinoer.git ~/git/Dinoer/Dinoer
cd ~/git/Dinoer/Dinoer
bash scripts/install.sh
```

`scripts/install.sh` creates the `dinoer` system user and group, the Python
venv, deploys the code to `/opt/dinoer/`, installs Chromium, and runs a smoke
test (`shot.py --a11y` against a real URL). Deploy further edits with
`scripts/deploy.sh`.

Configuration lives at `/opt/dinoer/dinoer.conf` (JSON) on this channel; the
encrypted secrets directory key is `secrets_dir`. Per-project override via the
`DINOER_CONF` environment variable or `~/.dinoer.conf`.

Uninstall:
```bash
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --dry-run   # preview, no changes made
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh             # interactive confirmation
```

---

## 2. Read a page

### 2a. Fast read — text and structure, no image

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y
```

Returns: `a11y_tree` (accessibility tree — the page's textual structure),
`boussole` (effective URL, title, HTTP status). Use this to read the title,
verify the URL, or map the page before interacting.

### 2b. Cleaned page text

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ \
  --action '{"type": "extraire_texte"}'
```

Returns `extraction_texte` with `titre`, `texte` (noise tags stripped:
`script`, `style`, `nav`, `header`, `footer`, `aside`, `noscript`), `url`,
`date_capture`. This is Dinoer's text of the page — no screenshot, ever.

### 2c. Read the boussole first

Every output contains a `boussole` object — read it before everything else:

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

If `boussole.url_courante` does not match what you expect: stop and investigate
before any mutating action.

### 2d. Read `etat` for a go/no-go decision (v1.16.0)

Every successful run includes an `etat` object at the JSON root — read it
before any mutating action instead of manually cross-checking `auth_status`,
`respect.plafond_atteint`, `erreurs_js`, and `erreurs_console` yourself:

```json
"etat": {
  "pret_a_agir": true,
  "niveau_confiance": "eleve",
  "raisons": ["aucun signal de friction détecté"]
}
```

If `pret_a_agir` is `false`: read `raisons` for the cause (inactive
authentication, session drift, navigation cap reached, or a detected WAF
block) before proceeding.

`etat` does not check whether the URL or page content matches your business
expectation — use `evaluer` with `attendu`/`contient`/`motif` (section 5d)
for that.

---

## 3. Respectful navigation (v1.15.0)

### 3a. Stealth mode `--stealth`

Some sites block headless browsers on `navigator.webdriver=true`
without examining the intent. `--stealth` removes this automatic technical marker.

```bash
# direct shot.py
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y --stealth

# Via rpa.py
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/my-scenario.json --stealth
```

When active: `boussole.stealth_actif = true` in the JSON output.

**What `--stealth` changes:** `navigator.webdriver` removed, plugins, languages, and platform normalized.
**What `--stealth` does not change:** the operator's IP, identity, or navigation intent.

### 3b. Courtesy delays and caps

Configured in `/opt/dinoer/dinoer.conf` (section `[navigation]`). Defaults
are active even without a config file (v1.19.0 — D-10):

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

`min_action_delay_ms`: minimum delay (ms) between each action. Shipped
default: 800 ms.

**Local development — set it to `0`:** the 800 ms default protects a
distracted operator on their *first, unconfigured* run against the public
internet — it has no protective purpose against your own development machine.
Set the key explicitly in your local `dinoer.conf`. Keep the 800 ms default
(or raise it) for any target reached over the public internet.

The `max_pages_par_run` and `max_actions_par_run` caps cleanly stop the run
if exceeded — the output JSON then contains:

```json
"respect": {
  "pages_visitees": 10,
  "actions_executees": 10,
  "duree_totale_ms": 12400,
  "plafond_atteint": "max_pages_par_run"
}
```

### 3c. Impact metrics

Each run returns `respect` (JSON root and inside `boussole`):

| Key | Meaning |
|---|---|
| `pages_visitees` | Number of `type: naviguer` navigations executed |
| `actions_executees` | Total number of scenario actions executed |
| `duree_totale_ms` | Total run duration |
| `plafond_atteint` | `"max_pages_par_run"` or `"max_actions_par_run"` if early stop |
| `indice_agressivite` | Ratio of mutating actions over total — keep under 0.3 during open-ended exploration |
| `waf_bloquants` | Number of navigations flagged as WAF-blocked |

### 3d. Stealth benchmark — quantitative (v1.17.1)

Prefer counting concrete fingerprint signals over comparing by eye — this is
the method used to verify the v1.17.0 `playwright-stealth` API-compatibility
fix (`docs/RETOUR_EXPERIENCE.md` FR-79):

```bash
# Without stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://bot.sannysoft.com --timeout 20000 \
  --actions '[{"type":"evaluer","script":"navigator.webdriver"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.failed\").length"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.passed\").length"}]'

# With stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://bot.sannysoft.com --stealth --timeout 20000 \
  --actions '[{"type":"evaluer","script":"navigator.webdriver"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.failed\").length"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.passed\").length"}]'
```

Read the three values in `evaluations[].valeur`: `navigator.webdriver` should
go from `true` to `false`, `td.failed` should drop toward `0`. Reference
measurement (v1.17.0 fix, session 47): 12 failed → 0 failed.

### 3e. WAF detection signal (v1.16.0, refined v1.17.2)

Dinoer flags a probable WAF block passively — HTTP 403/429, or a title/HTML
keyword match (`Cloudflare`, `CAPTCHA`, `checking your browser`, etc.). This
is a signal, never an exception — the run completes normally:

```json
"respect": {
  "waf_bloquants": 1
}
```

When present and `> 0`: `etat.niveau_confiance` is `"faible"` and
`etat.pret_a_agir` is `false`. Decide yourself whether to retry with
`--stealth`, change target, or stop — Dinoer does not abort the run for you.

Since v1.17.2, generic vendor names (`Cloudflare`, `Akamai`) only match the
page title — matching the full HTML previously false-positived on ordinary
CDN resource references. If a false positive persists, `--ignorer-waf`
degrades `niveau_confiance` without forcing `pret_a_agir: false`
(`boussole.waf_ignore_actif: true` records the override). The detection
is keyword-based and can produce false positives on pages that legitimately
discuss blocking/detection — treat it as a fast signal, not a certain verdict.

---

## 4. Encrypted directory and credentials

### 4a. Structure

The credentials live in an encrypted directory — a gocryptfs volume — containing one `.json` file per domain.

```
~/Vaults/__PROJET__/Dinoer/
  ├── app.example.com.json         ← credentials for https://app.example.com/
  ├── admin.example.com.json       ← credentials for https://admin.example.com/
  └── operations.jsonl             ← operation log (v1.15.0)
```

Credentials file format:
```json
{
  "username": "admin@example.com",
  "password": "my-password"
}
```

The file name = `urlparse(url).hostname`. For `https://app.example.com/login/`, create `app.example.com.json`.
The directory is resolved from `DINOER_CONF` → `~/.dinoer.conf` → `/opt/dinoer/dinoer.conf`, key `secrets_dir`.

### 4b. Filling a form — the absolute rule

**FORBIDDEN — exposes the password in the shell and `/proc`:**
```bash
PASS=$(jq -r '.password' ~/Vaults/.../file.json)   # NEVER
curl -d "password=$PASS" https://...                 # NEVER
```

**CORRECT — credentials resolved inside Playwright:**
```json
{"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
{"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"}
```

Values never pass through the shell, bash history, process logs, or any file.

### 4c. Choosing the credentials file for a run

```bash
# Default credentials directory (defined in dinoer.conf > secrets_dir)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url https://target.local/ --a11y

# Explicit credentials file (--secrets)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y \
  --secrets /path/to/mounted/directory/creds.json

# Per-project credentials directory via .dinoer.conf
export DINOER_CONF=~/git/MyProject/.dinoer.conf
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url https://target.local/ --a11y
```

Content of `~/git/MyProject/.dinoer.conf`:
```json
{"secrets_dir": "../MyProject-secrets"}
```
The path is resolved relative to the location of `.dinoer.conf`.

**`--secrets` file content — `origines_autorisees` mandatory since
05/08/2026** (breaking change, no compatibility period): a file missing this
key is refused before any read.

```json
{"username": "operator", "password": "secret", "origines_autorisees": ["target.local"]}
```

`origines_autorisees` lists the hostnames this file may be used against —
same lowercase, no-scheme, no-port format as `domaine_depuis_url()`. A read
against a page whose domain is not in the list is refused
(`SecretsOrigineNonAutoriseeError`).

### 4d. TOTP / MFA

Two live paths, both resolved inside Playwright (never a typed code):

```json
{"type": "remplir", "selecteur": "input[name=otp]", "valeur": "depuis_secrets_totp"}
```
Reads the `totp_cle` key (base32 seed) from the credentials file and computes the current TOTP code.

To receive the code via ntfy (workflow without human intervention):
```json
{"type": "attendre_mfa_ntfy", "selecteur": "input[name=otp]", "timeout": 120}
```
`selecteur` is the CSS selector of the OTP field. The ntfy base URL comes
from `DINOER_NTFY_URL` (env) or the `ntfy.url` key of `dinoer.conf`.

### 4e. Integrity checksum (opt-in, v1.15.0)

To protect a credentials file against silent FUSE corruption, add a `checksum` field:

```bash
# Generate the checksum
/opt/dinoer/venv/bin/python -c "
import json, hashlib
creds = json.load(open('my_credentials.json'))
fields = {k: creds[k] for k in sorted(['username','password']) if k in creds}
print('sha256:' + hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest())
"
```

Add the returned value to the credentials file:
```json
{
  "username": "admin@example.com",
  "password": "my-password",
  "checksum": "sha256:a3f2c1..."
}
```

If the checksum does not match, `shot.py` raises `SecretsChecksumError` (exit 42) with an explicit message.
Without the `checksum` key: behaviour unchanged (strict opt-in).

### 4f. Encrypted directory closed — what to do

```
SecretsFermesError: Le répertoire chiffré Dinoer est initialisé mais non monté.
```

```bash
# Mount the encrypted directory
bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh

# Verify the mount
ls ~/Vaults/__PROJET__/Dinoer/
# → must show JSON files
```

### 4g. HTTP Basic Auth — `--http-credentials` (v1.21.0)

For targets behind a network-level HTTP Basic Auth challenge (RFC 7617) —
the wall a reverse proxy like Caddy, nginx, or Traefik raises before any
page renders, common in front of self-hosted admin interfaces. This is a
different mechanism from the form-based authentication above
(4a-4f), which remains fully supported and unaffected.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://internal.example/ \
  --http-credentials --secrets ~/Vaults/__PROJET__/Dinoer/internal_example.json
```

Credentials file — the plain `username`/`password` pair already used for the
common case (a single set of credentials for the target):
```json
{"username": "admin", "password": "my-password"}
```

Dedicated `http_username`/`http_password` keys are tried first and only
needed when the same target has *both* a network-level Basic Auth wall
*and* its own separate application login (two different credential pairs
in the same file) — Dinoer falls back to `username`/`password`
automatically when the dedicated keys are absent.

Confirmed in production against a real Caddy-protected target: the safe
default (`send: "unauthorized"` — credentials sent only after a genuine
401, never preventively) resolved the challenge on the first attempt.
`boussole.http_credentials_actif: true` confirms a real success, not just
the flag being passed; `boussole.http_auth_requise: true` flags an
unresolved 401 distinctly from a WAF block.

---

## 5. Write and run an RPA scenario

### 5a. 3-step protocol

**Step 1 — Explore the page (read-only)**

```bash
# Quick view — accessibility tree
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y

# Full read — tree + cleaned text
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y \
  --action '{"type": "extraire_texte"}'

# Enriched DOM inventory (frameworks, stable data-attrs)
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/diagnostic_dom.json \
  --url https://target.local/
```

**What to note:**
- Stable attributes: `name`, `id`, `aria-label`, `data-testid`
- Blocking overlays (cookie banners, modals)
- SPA or full HTTP reload

**Step 2 — Write the scenario**

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

**Step 3 — Execute**

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/login_app.json
```

### 5b. Full scenario: log in and navigate between pages

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

### 5c. Extract data from the DOM

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

Result in `evaluations[]`:
```json
"evaluations": [
  {"index": 0, "script": "document.title", "valeur": "Dashboard — My App"},
  {"index": 1, "script": "...", "valeur": 42},
  {"index": 2, "script": "...", "valeur": "https://app.example.com/dashboard/"}
]
```

### 5d. Assertions on evaluer (rpa.py only)

Three mutually exclusive keys — one per action:

```json
{"type": "evaluer", "script": "document.querySelectorAll('.row').length", "attendu": 3}
{"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
{"type": "evaluer", "script": "window.location.href", "motif": "/dashboard$"}
```

| Key | Comparison | Valid types |
|---|---|---|
| `attendu` | strict equality `==` | str, int, bool |
| `contient` | substring `in` | str only |
| `motif` | `re.search()` Python | str only |

If the assertion fails: rpa.py stops immediately (exit 1) before any subsequent mutating action.

### 5e. Sub-scenarios (declencher_scenario)

Define a login as a reusable sub-scenario:

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

Call this sub-scenario from another scenario:
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

Maximum depth: 5 nesting levels. `declencher_scenario` is flattened by
`rpa.py` before the actions reach `shot.py`.

### 5f. Verify you are on the right page before any mutation

Always add a guard as the first action in scenarios that delete or modify:

```json
{"type": "evaluer", "script": "window.location.href", "contient": "/dashboard"},
{"type": "evaluer", "script": "document.querySelector('.alert-danger')?.textContent ?? null", "attendu": null}
```

If the guard fails: rpa.py stops before the deletion is executed.

### 5g. Resume a session (persisted cookies)

```bash
# First invocation — authenticate and save the session
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/login/ \
  --actions /tmp/login.json \
  --sauver-session /tmp/dinoer/session.json

# Subsequent invocations — reuse the session (no re-login)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/dashboard/ \
  --reprendre-session /tmp/dinoer/session.json
```

**Session drift signal:** if the session has expired, `boussole.session_derive: true` in the JSON.
In that case: restart the full login without `--reprendre-session`.

### 5h. Structural non-regression — `--replay-verifier` (v1.17.0)

```bash
# First run — save the structural reference
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/dashboard.json \
  --sauver-verifier-reference /tmp/dashboard.ref.json

# Subsequent runs — compare
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/dashboard.json \
  --replay-verifier /tmp/dashboard.ref.json
```

Compares `http_status`, `dom_stats`, and `evaluer` results against the saved
reference. Verdict on stderr:

```json
{"type_comparaison": "replay_verifier", "verdict": "stable", "diffs": []}
```

Exit 1 on `verdict: "regression"`, with `diffs` listing each mismatched
field (`reference` vs `obtenu`). The two flags are mutually exclusive.

### 5i. Resume a long scenario after failure — `--checkpoint` (v1.17.0)

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/long_audit.json \
  --checkpoint /tmp/long_audit.checkpoint.json
```

If the scenario fails partway through, the checkpoint file is written with
the count of completed actions and a session file. **Relaunch the exact same
command** to resume: already-completed actions are skipped. On full success,
the checkpoint file is deleted automatically.

A run stopped by a navigation cap (`max_actions_par_run`/`max_pages_par_run`)
is treated the same way as a partial failure since v1.17.2 — the checkpoint
is updated with the actual progress, not deleted.

DOM state (open modals, half-filled forms) is never preserved across a
resume — only cookies/`localStorage` and the action-list position are. Do
not rely on `--checkpoint` to resume mid-way through a single multi-step
form; it resumes at action boundaries only.

### 5j. Target elements inside an iframe (v1.17.0)

No element numbering exists inside an iframe (same-origin or cross-origin) —
target it by CSS selector directly:

```json
{"type": "cliquer_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "button.valider"},
{"type": "remplir_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`remplir_iframe` supports `valeur: "depuis_secrets"` exactly like `remplir`
(section 4b) — never a plaintext credential in the scenario. If the target
element refuses interaction (e.g. a `contenteditable` region in a read-only
state), add `"force": true` to `cliquer_iframe` — same semantics as `cliquer`
(section 7e).

To find the inner selector: use `evaluer` on the iframe's content if it is
same-origin (`document.querySelector('iframe').contentDocument...`), or
consult the target application's own markup/documentation if cross-origin.

### 5k. Nested iframes — `iframe_chemin` (v1.18.0)

An iframe inside another iframe: replace `iframe_selecteur` with
`iframe_chemin`, an ordered array — one CSS selector per nesting level, from
outermost to innermost.

```json
{"type": "cliquer_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "button.valider"},
{"type": "remplir_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`iframe_selecteur` (single frame) and `iframe_chemin` (nested descent) are
mutually exclusive — exactly one required per action. For a single-level
iframe, keep using `iframe_selecteur` (section 5j).

---

## 6. Actions — complete reference

| Type | Required params | Optional params | Notes |
|---|---|---|---|
| `naviguer` | `url` | — | Full HTTP reload. Counted in `respect.pages_visitees` |
| `cliquer` | `selecteur` | `force` (bool), `repli_js` (bool) | `force: true` bypasses CSS-hidden elements or showModal. `repli_js: true` retries through JS if the native click still fails (v1.22.0) — rejected with `--no-evaluer` (exit 2, before launch) |
| `remplir` | `selecteur`, `valeur` | `secret_cle` | `valeur: "depuis_secrets"` requires `secret_cle`; `"depuis_secrets_totp"` for TOTP |
| `evaluer` | `script` | `attendu`, `contient`, `motif` | JS executed in the browser. Assertions for rpa.py only |
| `defiler` | `px` or `selecteur` | — | Vertical scroll in pixels (`px`) or scroll to element (`selecteur`) |
| `pause` | `ms` | — | Fixed delay in ms. Prefer `attendre_selecteur_present` for DOM signals |
| `attendre` | `selecteur` | — | Waits for the CSS selector to be present in the DOM (`state=attached`) |
| `attendre_navigation` | — | — | Waits for `networkidle` (end of network requests) |
| `attendre_url` | `motif` | `attendre_changement` (bool) | URL substring match. `attendre_changement: true` waits for a real navigation first (see the FR-55 pitfall) |
| `attendre_selecteur_present` | `selecteur` | — | Waits for element to be visible (`state=visible`) |
| `attendre_absence` | `selecteur` | `delai_initial_ms` | Waits for element removal from DOM (`state=detached`) |
| `attendre_reseau_calme` | — | `timeout_ms` | 500 ms of network silence. `timeout_ms`: max duration before giving up |
| `attendre_mfa_ntfy` | `selecteur` | `timeout` | Waits for a TOTP code via ntfy, fills it into the field |
| `nettoyer_overlay` | `selecteur` | — | Hides blocking overlays (cookie banner, modal) — explicit selector, no auto-detection |
| `declencher_scenario` | `scenario` | — | Inlines a sub-scenario's actions. Max depth: 5 (rpa.py) |
| `extraire_texte` | — | — | Cleaned page text from the rendered DOM — `extraction_texte` (`titre`, `texte`, `url`, `date_capture`) |
| `cliquer_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur` | `force` (bool) | Click inside an iframe (v1.17.0). `iframe_chemin` for nested iframes (v1.18.0, section 5k) |
| `remplir_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur`, `valeur` | `secret_cle` | Fill inside an iframe (v1.17.0). `valeur: "depuis_secrets"` supported |

---

## 7. Handle common obstacles

### 7a. Cookie banner / blocking overlay

```json
{"type": "nettoyer_overlay", "selecteur": ".cookie-consent-banner, #gdpr-overlay"}
```

Place **before** any other reading/interaction action. The overlay masks
elements in the accessibility tree.

### 7b. Element outside the viewport

Scroll to it (by amount or by selector), then act:

```json
{"type": "defiler", "selecteur": "#the-button"},
{"type": "cliquer", "selecteur": "#the-button"}
```
or
```json
{"type": "defiler", "px": 600},
{"type": "cliquer", "selecteur": "button[data-testid='load-more']"}
```

### 7c. SPA (React, Vue, Angular) — navigate without reload

After a click that changes the view in an SPA, Playwright does not know when navigation is complete.

```json
{"type": "cliquer", "selecteur": "a[href*='/dashboard']"},
{"type": "attendre_url", "motif": "/dashboard"},
{"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
```

Never assume a click has completed navigation without a DOM signal. After a
submit, pair `attendre_url` with `attendre_selecteur_present` (partial-match
pitfall, see `docs/GUIDE_LLM_INTERACTIONS.md`).

### 7d. CSS dialog or showModal()

`TimeoutError` on `cliquer` when the element is visible in the DOM = CSS-hidden element
or inside a dialog.

```json
{"type": "cliquer", "selecteur": "#dialog-confirm button[type=submit]", "force": true}
```

If `force: true` is insufficient (interactability/obstruction error): add
`repli_js: true` to the same action (v1.22.0), or fall back to JS:
```json
{"type": "evaluer", "script": "document.querySelector('#dialog-confirm button[type=submit]').click()"}
```

### 7e. Long operation (spinner, batch job)

Do not use `pause` to wait for a fixed duration. Wait for the DOM signal:

```json
{"type": "cliquer", "selecteur": "button[data-testid='run-job']"},
{"type": "attendre_absence", "selecteur": ".spinner", "delai_initial_ms": 500},
{"type": "attendre_selecteur_present", "selecteur": ".result-container"}
```

If the operation provides no DOM signal, poll state with `evaluer` and
proceed when the evidence is present.

### 7f. Cap reached (v1.15.0)

If `respect.plafond_atteint` is present in the output, the run was stopped
before the scenario completed. Remaining actions were not executed.

Options:
1. Increase `max_pages_par_run` or `max_actions_par_run` in `dinoer.conf`
2. Split the scenario into multiple runs
3. Resume a partial section with `--checkpoint`

### 7g. `<select>` form field

`remplir` (`.fill()`) does not work on `<select>`. Use a JS setter via
`evaluer`:
```json
{"type": "evaluer", "script": "(() => { const s = document.querySelector('select[name=role]'); s.value='admin'; s.dispatchEvent(new Event('change',{bubbles:true})); })()"}
```

### 7h. Site blocked by WAF (immediate 403)

```bash
# Try with stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y --stealth
```

If 403 persists with `--stealth`: the site uses TLS fingerprinting (JA3/JA4) or advanced
behavioural analysis (Cloudflare Enterprise). `playwright-stealth` does not bypass these protections.
See `docs/RETOUR_EXPERIENCE.md` FR-77/FR-78/FR-79 for context.

Dinoer also flags a likely block passively — see section 3e (`respect.waf_bloquants`).

### 7i. Initial navigation never completes — `--wait-until` (v1.22.0)

Symptom: `TimeoutError` on the initial navigation, and raising `--timeout`
changes nothing (45 s fails exactly like 10 s). Cause: by default Dinoer waits
for `networkidle` — 500 ms of network silence. A page that polls continuously
(live statistics, auto-refreshing counters, router admin panels) never
produces that silence, so no timeout value can ever be large enough.

```bash
# shot.py — direct reconnaissance
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url http://target.local/ --wait-until load --a11y

# rpa.py — propagated to shot.py, so scenarios reach the same targets
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario ./admin_login.json --wait-until load
```

A scenario can carry it as a root property instead, staying self-contained:

```json
{"url": "http://target.local/", "wait_until": "load", "actions": [...]}
```

The CLI flag takes precedence over the scenario property.

| Value | Waits for | Use when |
|---|---|---|
| `networkidle` | 500 ms of network silence | default — keep it unless it fails |
| `load` | `load` event (page and sub-resources) | continuous polling / live statistics |
| `domcontentloaded` | HTML parsed, sub-resources still pending | very heavy page, DOM is all you need |

Applies to the initial navigation only — the `naviguer` action is unaffected.
`boussole.wait_until` reports the value only when it differs from the default.

---

## 8. Monitoring — structural checks

No image-based monitoring exists in Dinoer (no visual diff). Structural
checks are text-based and CI-friendly.

### 8a. Continuous structural monitoring — `scripts/monitor-verifier.sh` (v1.18.0)

Monitors *structure* (`http_status`, `dom_stats`, `evaluations`) — zero image,
zero LLM call, built on `--replay-verifier` (section 5h).

```bash
# First run — create the structural reference
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/sillage_login.json \
  --sauver-verifier-reference /opt/dinoer/references/sillage_login.ref.json

# One check-and-alert pass — not a daemon, run it repeatedly via cron.
# scripts/*.sh is never deployed to /opt/dinoer/, so it runs from the git
# source, as your own user.
bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/sillage_login.json \
  --reference /tmp/ref_sillage.json \
  --ntfy-topic dinoer-monitoring
```

```bash
# crontab -e (your own crontab)
*/15 * * * * bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/sillage_login.json \
  --reference /opt/dinoer/references/sillage_login.ref.json \
  --ntfy-topic dinoer-monitoring \
  >> /var/log/dinoer/cron-structural.jsonl 2>&1
```

Stable → silence. Regression → one `ntfy` notification with the diff. Each
invocation is an isolated process — no daemon, no memory-leak risk, and
Respectful Navigation caps reset cleanly on every pass.

**Known debt (v1.23.0):** the script calls `rpa.py --no-capture
--replay-verifier`, but `--no-capture` is no longer an `rpa.py` flag. It is
semantically redundant (Dinoer has no image path), but it currently makes the
script fail at argparse. Do not rely on it as-is until corrected.

**Guide-read lock nuance:** if invoked under a distinct OS user (e.g. a
system service account), that user needs `--guide-version` validated once
(`~<home>/.config/dinoer/guide_state.json`).

---

## 9. Operation log

The log is `/var/log/dinoer/operations.jsonl`. If the configured journal path
sits inside the encrypted directory and it is not mounted, entries are
redirected to a local fallback (degraded write, 700/600) rather than written
in clear text on the raw host.

```bash
# Read the last 10 entries
tail -n 10 /var/log/dinoer/operations.jsonl | python3 -m json.tool

# Filter by target (journal.py tool)
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com

# Filter mutating operations only
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --mutatif

# From a date
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --depuis 2026-07-01

# Failed runs only (v1.20.0) — result != success
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --erreurs
```

Fields in each entry:

| Field | Meaning |
|---|---|
| `ts` | ISO 8601 timestamp |
| `version` | Dinoer version |
| `mode` | `shot.py` or `rpa.py` |
| `cible_url` | Target URL |
| `scenario` | Scenario file path (RPA mode) |
| `source_scenario` | Scenario file name only, no path (v1.18.0) |
| `resultat` | `"succes"` or `"echec"` |
| `mutatif` | `true` if at least one write action |
| `respect` | The run's navigation ledger |
| `evaluations` | Sanitised `{script, valeur_retournee}` values |
| `duree_ms` | Duration in ms |
| `intention` | Label passed via `--intention` or scenario `intention` field |

### 9a. Log rotation (G-36)

Dinoer does not ship a logrotate configuration — `/var/log/dinoer/operations.jsonl`
grows unbounded until the administrator installs one. `lib/journal.py` opens
and closes the file on every write (no persistent file descriptor across
runs), specifically so the **default** logrotate behaviour (rename the
current file, create a fresh one) works correctly without any special
option: the next write reopens the path and finds the new inode.

**Do not add `copytruncate`** to a Dinoer logrotate config — it is
unnecessary here and reintroduces a write-loss window. Example
`/etc/logrotate.d/dinoer`:

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

`journal.py` (the reader) already follows rotated files transparently
(`operations.jsonl`, `.1`, `.2.gz`, …) — no extra step needed after rotation.

---

## 10. CLI flags — reference

### shot.py

| Flag | Default | Description |
|---|---|---|
| `--version` | — | Prints installed version and exits immediately — no Playwright, no other argument required (v1.18.0) |
| `--guide-version X.Y` | — | Proof of reading `docs/GUIDE_LLM.md` — required unless a valid local marker already exists (v1.18.0, section 1) |
| `--url URL` | required | URL to capture |
| `--actions FILE` | — | JSON file of sequential actions |
| `--action JSON` | — | Single action as inline JSON — quote carefully, prefer `--actions FILE` for JS-heavy actions |
| `--attendre-selecteur SEL` | — | Wait for a selector before finishing the run |
| `--timeout MS` | 10000 | Per-action Playwright timeout (ms) |
| `--wait-until VALUE` | `networkidle` | `networkidle`\|`load`\|`domcontentloaded` — initial navigation only (v1.22.0, section 7i) |
| `--largeur PX` | 1280 | Viewport width |
| `--hauteur PX` | 720 | Viewport height |
| `--a11y` | off | Include accessibility tree in JSON |
| `--stealth` | off | playwright-stealth stealth mode (v1.15.0) |
| `--secrets FILE` | — | Explicit path to a credentials file |
| `--auth-indicator SEL` | — | CSS selector present only in authenticated session |
| `--auth-indicator-negative SEL` | — | Requires `--auth-indicator`; CSS selector present only outside authenticated session |
| `--ignorer-waf` | off | A detected WAF block degrades `niveau_confiance` but no longer forces `pret_a_agir: false` on its own (v1.17.2, section 3e) |
| `--http-credentials` | off | Resolves HTTP Basic Auth credentials from the credentials file, scoped to the target's origin (v1.21.0, section 4g) |
| `--ignore-tls-errors` | off | Accept invalid TLS on controlled LAN/dev targets — never on public internet (v1.15.1) |
| `--no-evaluer` | off | Refuses the **evaluer** action (and `repli_js`) for the whole run — recommended against sensitive forms (v1.15.1) |
| `--no-filtre-evaluer` | off | Disables stdout neutralisation of **evaluer** return values, URLs and error messages — explicit debug runs only; when disabled, `boussole.filtre_evaluer_actif: false` is set (v1.23.0) |
| `--intention TEXT` | — | Business label recorded in the log |
| `--sauver-session FILE` | — | Saves cookies after actions |
| `--reprendre-session FILE` | — | Resumes a saved session |
| `--source-scenario NAME` | — | Internal (rpa.py plumbing for the journal — not for direct calls) |
| `--chainage JSON` | — | Internal (rpa.py plumbing for the journal — not for direct calls) |

### rpa.py

Propagates all relevant shot.py flags, plus:

| Flag | Description |
|---|---|
| `--version` | Prints installed version and exits immediately (v1.18.0) |
| `--guide-version X.Y` | Proof of reading `docs/GUIDE_LLM.md` — checked independently, same rule as shot.py (v1.18.0) |
| `--scenario FILE` | Path to JSON or YAML scenario (required) |
| `--url URL` | Overrides scenario URL without modifying the file |
| `--stealth` | Propagated to shot.py |
| `--wait-until` | Propagated to shot.py (v1.22.0, section 7i) |
| `--ignorer-waf` | Propagated to shot.py (v1.17.2, section 3e) |
| `--http-credentials` | Propagated to shot.py; also settable as scenario root property `"http_credentials": true` (v1.21.0, section 4g) |
| `--auth-indicator-negative` | Requires an `auth_indicator` (CLI or scenario root property) |
| `--sauver-verifier-reference FILE` | Saves structural reference for `--replay-verifier` (v1.17.0, section 5h) |
| `--replay-verifier FILE` | Compares run against a structural reference, exit 1 on regression (v1.17.0, section 5h) |
| `--checkpoint FILE` | Resumes a long scenario after a mid-run failure (v1.17.0, section 5i) |

### campagne.py (research pipeline)

| Flag | Description |
|---|---|
| `--manifeste FILE` | Campaign manifest (JSON) — requires `id_campagne` + `cibles` |
| `--id-campagne ID` | Campaign identifier (used in the manifest and extraction) |
| `--extraire-cible DEMANDE` | Targeted extraction on an already-collected corpus, without synthesis |
| `--desactiver-cache` | Bypass the search cache |
| `--purger-cache` | Purge the whole search cache |
| `--purger-cache-avant-jours N` | Purge cache entries older than N days |

Target types in the manifest: `query`, `url`, `produit`, `table_reference`.
Artefacts: the shared `/var/log/dinoer/operations.jsonl` + a per-campaign
`collecte.jsonl`. Full detail: `campagne.py --help`.

---

## 11. Exit codes and output

### Exit codes

| Code | Cause | What to do |
|---|---|---|
| 0 | Success | — |
| 1 | Playwright error, failed action, rpa.py assertion, `action_secret_en_clair` | Read `erreur` in JSON. See `GUIDE_LLM_INTERACTIONS.md` |
| 1 | `guide_non_lu` — missing/wrong `--guide-version`, no valid marker (v1.18.0) | Fires before Playwright launches. Read `docs/GUIDE_LLM.md`, relaunch with `--guide-version X.Y` (section 1) |
| 2 | Incompatible arguments, `arguments_incompatibles`, `url_scheme_interdit`, `chemin_sensible_refuse` | Read `message` — it names the conflict |
| 3 | `playwright` module not found | Invoke via `/opt/dinoer/venv/bin/python` |
| 42 | `SecretsFermesError` — encrypted directory not mounted, or invalid checksum | Mount it, or verify the credentials file |
| 43 | `SecretsNonConfigureError` — no `secrets_dir` configured | Configure `secrets_dir` in `dinoer.conf` (`undo` a missing sample: create `/opt/dinoer/dinoer.conf`) |

### Output JSON structure

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

`operation_id` (v1.16.0) is always present and identifies this run uniquely —
it names the isolation directory under `/tmp/dinoer/<operation_id>/` and
matches the `operation_id` field of this run's entry in the operations log
(section 9). `etat` (v1.16.0) is present on the success path only.
`latences_actions` (v1.20.0) is always present (empty list if no actions),
one entry per action that actually dispatched — see `GUIDE_LLM_MONITORING.md`
for how it complements `respect.duree_totale_ms`.

Conditional keys (absent when inactive): `dom_stats`, `a11y_tree`,
`evaluations`, `extraction_texte`, `auth_status`, `stealth_actif`,
`session_derive`, `respect.plafond_atteint`, `respect.waf_bloquants`,
`respect.indice_agressivite` (present whenever at least one action ran),
`boussole.repli_js_utilise`, `boussole.wait_until`,
`boussole.http_credentials_actif`, `boussole.http_auth_requise`,
`boussole.tls_errors_ignored`, `boussole.waf_ignore_actif`,
`boussole.filtre_evaluer_actif`, `boussole.champs_rediges`,
`actions_executees_avant_echec`, `pages_visitees_avant_echec` (failure JSON
only, v1.17.0). See `GUIDE_LLM_MONITORING.md` for the exhaustive activation
table.

### Error — format

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

## Reference paths

| Path | Role |
|---|---|
| `/opt/dinoer/` | Production installation |
| `/opt/dinoer/venv/bin/python` | Python to use for every invocation |
| `/opt/dinoer/dinoer.conf` | Machine configuration (secrets_dir, navigation, ntfy) |
| `/opt/dinoer/scenarios/` | RPA scenarios (including `diagnostic_dom.json`) |
| `/opt/dinoer/docs/` | Documentation |
| `/opt/dinoer/references/` | `--sauver-verifier-reference` / replay references |
| `/tmp/dinoer/<operation_id>/` | Temporary session data for one run, isolated by `operation_id` (v1.16.0, cleared on reboot) |
| `~/Vaults/__PROJET__/Dinoer/` | Credentials + log (gocryptfs volume) |
| `~/git/Dinoer/Dinoer/` | Git sources (edit here, then `deploy.sh`) |
| `/var/log/dinoer/operations.jsonl` | Persistent operation log (`journal.py`) |

Deploy after modifying sources:
```bash
bash ~/git/Dinoer/Dinoer/scripts/deploy.sh
```