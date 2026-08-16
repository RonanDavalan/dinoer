# Dinoer — Operator guide

Version 1.11 — August 2026 (v1.0.0) — surface realigned to the Dinoer
reconstruction: no screenshot, no Set-of-Mark, no `watch.py`; the agent
reads the accessibility tree and drives Playwright actions on CSS selectors.

*Also available in French, German and Spanish under `docs/fr/`, `docs/de/` and `docs/es/`.*

---

## Why Dinoer — what you actually delegate

### The problem Dinoer solves

When you work with an LLM on a web application, a perception asymmetry occurs:
the model reads code, runs commands, observes textual output — but it does not see
the interface your users see. You do.

This asymmetry creates a specific form of anxiety: you don't know whether what
the model describes matches what you would see in a browser. To be sure, you must
either trust it at its word, or verify it yourself.

Dinoer solves this problem by giving the model the same structured view you
would get in a browser: the accessibility tree, read through a real headless
Chromium, plus the DOM values it extracts with `evaluer`. You no longer take
the model at its word — you observe the same state it does.

```
 Browser (headless Chromium)
        │  Playwright drives it — click, fill, navigate
        ▼
 shot.py / rpa.py
        │  reads the resulting DOM state through parallel views
        ├──▶ a11y_tree            accessibility tree, text
        ├──▶ evaluations          values extracted via `evaluer`
        └──▶ session file         cookies only (--sauver-session)
        │
        ▼
 boussole + JSON on stdout — the state, as the operator can audit it
        │
        ▼
 You (the model): read → analyse → decide → act → loop
```

### What you delegate

Dinoer lets you delegate **repetitive and control-prone verification**:

- Checking that 20 pages of a site respond correctly after a deployment
- Confirming that a login form works on the right interface
- Ensuring a deployment did not break a critical view's structure
- Driving an admin panel through the same interface a human would use

Without Dinoer, these verifications are your responsibility. With Dinoer, the model
performs them and reports the result — with the JSON evidence to back it up.

### What you keep

You keep **high-level sense validation**: deciding whether the result
the model presents is acceptable, consistent with your expectations, and in line
with what your users should see. That decision remains yours.

### Respectful Navigation (v1.15.0)

Dinoer does not disguise its identity to bypass bot detection. `--stealth`
removes automatic technical markers (`navigator.webdriver`) that block
headless browsers regardless of intent — it does not change the operator's
IP, identity, or the fact that the run is declared. In exchange, every run
reports its own footprint (`respect`: pages visited, actions executed,
duration) and respects configurable courtesy delays and hard caps
(`dinoer.conf [navigation]`). The right to navigate and the duty to navigate
measurably are treated as inseparable — see `docs/RETOUR_EXPERIENCE.md`
FR-77/FR-78/FR-79 for the field context that shaped this.

**Local targets — the courtesy delay is not a doctrine, it is a default
(v1.19.0):** the shipped `min_action_delay_ms: 800` protects
an unconfigured first run against the public internet — it is meaningless
against your own development/production machine. Set it to `0` in your local
`dinoer.conf` for local debugging; see `docs/MANUEL.md` section 3b.

### When Dinoer is the right tool

| Use case | Dinoer suitable? |
|---|---|
| Structural validation after deployment | ✓ Yes |
| Diagnosing a broken interaction | ✓ Yes |
| Navigation and form input (~30 s max) | ✓ Yes |
| Delegating repetitive checks | ✓ Yes |
| Long server operation (cloning ~2–5 min) | ✗ No — Playwright timeout |
| Bulk deletion or mutation | ✗ No — prefer a direct API call |
| Workflow requiring rollback | ✗ No — Dinoer cannot undo |


---

**This document is written for the person operating Dinoer.**

It complements `GUIDE_LLM.md` (intended for models) with concrete examples,
step-by-step procedures, and reminders on common stumbling points.

---

## Demonstration use cases

The cases below illustrate what an agent-plus-Dinoer session can look like in
practice. They are meant for you to evaluate against your own context, not as
a recommendation to adopt any specific one. Only Case 1 ships as a runnable
scenario; the others are narrative on purpose, and each explains why under its
own heading.

### Case 1 — local CSS/JS troubleshooting

Committed as a real, runnable scenario:
`scenarios/exemples/depannage_local.json`. It diagnoses a layout
shift or a blocked interaction on a locally-served interface — a fast probe
reading `erreurs_js`/`erreurs_console` and the accessibility tree, then
validating the fix with `rpa.py --replay-verifier` against a reference
captured before the regression. Run it directly:

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/exemples/depannage_local.json \
  --guide-version 1.6
```

### Case 2 — comparing hardware components across shops

An agent asked to compare a component's price and stock across several
online shops could compose Dinoer with a separate URL-discovery tool (a
local search instance, for example) to find candidate shop pages, then use
Dinoer in read-only mode with `evaluer` actions to extract
price/stock/specifications from each page, and finally compare the
results itself.

**Not shipped as a committed scenario, deliberately:** naming a specific
shop in a public, versioned scenario is a decision that belongs to you, not
a default this project should make on your behalf. It also carries a real
fragility risk — a public scenario targeting a named commercial site can
fail months later when that site's anti-bot posture changes (39% of the
commercial sites sampled in `docs/RETOUR_EXPERIENCE.md` FR-77 returned an
immediate block), which discredits the example more than it helps. If you
build this composition yourself, note that any URL-discovery tool you pair
Dinoer with (a local search instance or otherwise) is not a Dinoer
component — it is a separate piece the agent composes on top.

### Case 3 — exploring and summarising technical documentation (single-page apps)

An agent tasked with producing an integration guide for a documentation
site built as a single-page app could use `rpa.py` with
`attendre_reseau_calme` to let client-side routing settle, extract the
accessibility tree to map the page structure, then walk code
blocks recursively with `evaluer` to pull their exact content, and finally
synthesise the collected material into a guide.

**Not shipped as a committed scenario, for the same reason as Case 2** —
naming a specific documentation site (or, worse, a specific payment
provider whose documentation happens to be the working example) is a
commercial and reputational commitment this project should not make by
default, and the same WAF-fragility risk applies to a public scenario
pinned to one real target.

### Case 4 — configuring a self-hosted observability or analytics dashboard

An operator setting up a self-hosted monitoring or web-analytics dashboard
behind a reverse proxy can use Dinoer to drive the interface itself —
creating a dashboard, wiring a data source, setting an alert rule — the
same way any other admin panel gets configured, instead of hand-editing
files for steps the UI is meant to handle. This includes targets sitting
behind a network-level HTTP Basic Auth challenge (`--http-credentials`,
v1.21.0) — confirmed against a real Caddy-protected admin interface, not
just a synthetic fixture: the stored credentials answered the
challenge on the first attempt.

**Not shipped as a committed scenario** — the dashboard layout and data
source names are specific to one operator's infrastructure, and inventing
a synthetic equivalent would duplicate what the local fixture in Case 1
already covers for structural regression, not for this kind of guided,
multi-step configuration work.

### Case 5 — administering a ticketing platform end-to-end

Dinoer used across several sessions to configure and operate a real
self-hosted ticketing installation — event setup, ticket categories, a
custom domain, and the day-of scan/check-in tooling — through the same web
interface a human administrator would use. Real friction was encountered
and resolved along the way (session handling, dropdown quirks, a
permission prompt blocking an unattended step) — not a friction-free
success story, which is part of what makes it a useful example: the
obstacles were ordinary web-automation obstacles, not something specific
to Dinoer.

**Not shipped as a committed scenario** — a ticketing configuration touches
billing and venue specifics unique to the operator, same reasoning as
Case 2.

### Case 6 — tracking a regional events calendar

A simple semantic-probe usage: asking an agent to check a local events
calendar for upcoming happenings, without knowing in advance which page
holds the answer. Dinoer's read-only mode combined with the accessibility
tree lets the agent scan and report back in a handful of requests — no
vision model needed for this kind of text-driven task. One session also
produced a clean, real example of the WAF signal's documented
false-positive behaviour: a page loaded normally (rich content, no
captcha, no interstitial) while `respect.waf_bloquants` still fired,
because of an unrelated third-party resource on the page matching a
detection keyword — resolved in about a minute by reading the accessibility
tree already present in the same response, exactly as the guide's "signal,
never a lock" rule anticipates.

**Not shipped as a committed scenario** — a specific regional events site
is not a stable, reproducible public target, and naming one publicly is
the operator's call, not a project default.

### Case 7 — testing real-world access to e-commerce sites under Respectful Navigation

A recurring, honest observation from actual sessions: used respectfully
(rate-limited delays, page/action caps, `--stealth` active, no attempt to
force access past a real block), Dinoer run against a range of e-commerce
sites finds that a large share of major platforms return an outright
block — HTTP 403, or a request that never completes — regardless of how
courteous the traffic is. This is not a Dinoer shortcoming to fix:
anti-bot posture is the site's own choice, and Dinoer does not attempt to
defeat it (see "Respectful Navigation" above). Practically: for
shopping-comparison tasks against large commercial platforms, expect a
meaningful share of dead ends, and treat a block signal
(`respect.waf_bloquants`) as information to route around, not an error
to retry against.

A distinction worth keeping in mind: an invisible verification screen that
never resolves and presents nothing to act on (no checkbox, no image
challenge) is different from an interactive CAPTCHA. The latter is
legitimate to answer honestly — an agent operating for a named human, from
that human's own IP, is not the "robot" the question is aimed at. The
former simply offers no door to open from the agent's side, and forcing
past it (IP rotation, TLS fingerprint spoofing) falls outside what Dinoer
does.

**Not shipped as a committed scenario, and deliberately not naming the
platforms involved** — see the WAF-fragility reasoning under Case 2: a
dated block/no-block table tied to named commercial sites goes stale and
undermines its own point faster than it illustrates it. `docs/RETOUR_EXPERIENCE.md`
FR-77 documents the same pattern at panel scale (39% immediate block rate).

---

## Prerequisites before starting

```bash
# 1. Verify Dinoer responds
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://example.com --a11y
# → must return {"succes": true, ...}

# 2. Verify the encrypted directory is mounted (if gocryptfs)
ls ~/Vaults/__PROJET__/Dinoer/
# → must show .json files, not encrypted content

# 3. Verify credentials for a domain
/opt/dinoer/venv/bin/python -c "
import sys; sys.path.insert(0, '/opt/dinoer')
from lib.repertoire_chiffre import lire_credential
print('OK' if lire_credential('target.local', 'password') else 'EMPTY')
"
```

---

## Credentials configuration per project

Each project can have its own credentials directory. Two methods:

**Method 1 — Direct environment variable (one-shot):**
```bash
DINOER_SECRETS_DIR=~/Vaults/MyProject \
  /opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url …
```

**Method 2 — Project `.dinoer.conf` file (recommended for recurring projects):**
```bash
# Create the file at the project root
echo '{"secrets_dir": "../MyProject-secrets"}' > ~/git/MyProject/.dinoer.conf

# Then prefix each invocation (or export at the start of the shell session)
export DINOER_CONF=~/git/MyProject/.dinoer.conf
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url …
```

The `secrets_dir` in `.dinoer.conf` can be a relative path — it is resolved
relative to the location of the `.dinoer.conf` file.

---

## Capturing a page and analysing it

```bash
# Read the page state (read-only)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y
# → returns url_courante, titre_page, a11y_tree in the JSON
```

**What you get:**
- `boussole.url_courante` + `boussole.titre_page`: effective URL and title after navigation
- `a11y_tree`: page structure in text (headings, fields, buttons)
- `etat.pret_a_agir` + `etat.raisons`: frictions perceived, for the model to route around

---

## Automating a login form

**Step 1** — Prepare the credentials file.

The credentials file is named `<hostname>.json` where `hostname` = result of
`urlparse(url).hostname`. For `https://app.example.com/`, the file is
`app.example.com.json`.

```json
{"username": "admin@example.com", "password": "my-secret"}
```

**Step 2** — Explore the login page.
```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/login/ --a11y
```
Read `a11y_tree` to identify the field selectors.

**Step 3** — Write the scenario.
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

**Step 4** — Execute.
```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /tmp/login.json
```

---

## Validating multiple pages in a single invocation

To check N pages of an authenticated site without replaying the login each time:

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

## Extracting a value from the page

To read a text string, a counter, or any DOM value:

```bash
cat > /tmp/extract.json << 'EOF'
[{"type": "evaluer", "script": "document.title"}]
EOF
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --actions /tmp/extract.json
# → result in evaluations[0].valeur
```

For cleaned documentary text (forms and noise tags stripped), use
`extraire_texte` instead — the output is a `titre`/`texte`/`url`/`date_capture`
structure a summarising agent can consume directly.

**Important**: always write JS scripts to an `--actions` file,
never inline with `--action` (the shell corrupts nested quotes).

---

## Setting up continuous structural monitoring (v1.18.0)

Dinoer has no visual pipeline — monitoring is *structural*: it checks the
page's status code, DOM element counts and JS evaluation results. This is
cheaper than image diffing and catches a different class of regression (a
disappeared form field with unchanged layout, for instance).

```bash
# 1. Save a structural reference, once
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --sauver-verifier-reference /opt/dinoer/references/my-scenario.ref.json

# 2. One check-and-alert pass
bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --reference /opt/dinoer/references/my-scenario.ref.json \
  --ntfy-topic dinoer-monitoring
```

Silent when stable, one `ntfy` push when a regression is detected. Schedule
it yourself with cron — the script does one pass and exits, it does not loop.
On the git-clone channel, `scripts/*.sh` is never deployed to `/opt/dinoer/`,
so the cron entry below runs from the git source, as your own user (not the
`dinoer` service account, which cannot reach `~/git/Dinoer/Dinoer/`). On the
`.deb` channel, the three wrapped scripts are installed under
`/opt/dinoer/scripts/` and reachable via the `dinoer-*` commands instead —
corrected 15/08/2026, this section predates that channel's real
construction:

```bash
# crontab -e (your own crontab)
*/15 * * * * bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --reference /opt/dinoer/references/my-scenario.ref.json \
  --ntfy-topic dinoer-monitoring \
  >> /var/log/dinoer/cron-structural.jsonl 2>&1
```

---

## Common pitfalls

| Situation | What to do |
|---|---|
| `FileNotFoundError` on the credentials file | Check that the JSON file is named with the full FQDN (`urlparse(url).hostname`) |
| `SecretsFermesError` (exit 42) | Mount the encrypted directory: `bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh` |
| Invalid JSON in output | Use `2>/dev/null \| tail -1` to extract only the JSON line |
| Login followed by Django redirect to dashboard | Do not use `naviguer` in a resumed Django session — pass the URL via `--url` |
| `<select>` form field not filled | Use `remplir` with `selecteur`, then `cliquer` on the option, or drive it via `evaluer` |
| Click has no effect on out-of-viewport button | Add `{"type":"defiler","selecteur":"#the-button"}` before the click |
| `auth_status: "active"` even on the login page | Positive selector is ambiguous (persistent header) — add `--auth-indicator-negative .btn-login` |
| Web Components block a normal selector | Use `cliquer_iframe`/`remplir_iframe` with an explicit selector, or reach inside the shadow root via `evaluer` |
| `respect.waf_bloquants` appears on a page that is not actually blocked | Detection is keyword-based (v1.16.0, refined v1.17.2) — treat as a signal, not a verdict. If it persists on a page you've confirmed is not blocked, add `--ignorer-waf` |
| `cliquer` clicks the wrong element on a page that mutated | Prefer order-stable selectors, or re-read the tree with a fresh `--a11y` call before clicking |
| A long RPA scenario fails partway through and you don't want to replay completed steps | Add `--checkpoint FILE` (v1.17.0) — relaunch the same command to resume; DOM state is not preserved, only session + action position |
| Interactive elements inside an iframe are invisible to the tree | Use `cliquer_iframe`/`remplir_iframe` (v1.17.0) with an explicit CSS selector, or `iframe_chemin` (v1.18.0) for an iframe nested inside another |
| Your model reports `"erreur": "guide_non_lu"` / exit 1 on its first Dinoer call | Expected the first time a model uses Dinoer on this machine as this OS user (v1.18.0) — it must read `docs/GUIDE_LLM.md` and pass `--guide-version` once. This is deliberate, not a bug — tell the model to read the guide rather than working around the error |

---

## Uninstalling Dinoer

The `~/git/Dinoer/Dinoer/scripts/uninstall.sh` script removes the installation cleanly, in the reverse
order of `install.sh`.

```bash
# See what will be removed, without doing anything
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --dry-run

# Full uninstall (interactive confirmation)
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh

# Without confirmation (cold tests, chained reinstall)
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --confirme && bash ~/git/Dinoer/Dinoer/scripts/install.sh
```

**What is removed:**

| Item | Detail |
|---|---|
| `/opt/dinoer/` | Code, Python venv, configuration |
| `/var/log/dinoer/` | Operation logs |
| `dinoer` system user | Created exclusively for Dinoer |
| `dinoer` system group | Same |
| Group membership | Your account is removed from the `dinoer` group |
| git pre-push hook | `core.hooksPath` disabled in the source repository |

**What is never touched:**
- `~/Vaults/` — your credentials
- `~/git/Dinoer/` — git sources
- Playwright browser cache (`~/.cache/ms-playwright/`)

**Structured evidence (`/var/log/dinoer/preuves/`):** if the directory contains
captures, it is preserved by default with a warning. To remove it:

```bash
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --confirme --purge-preuves
```

---

## Consulting the operation history

```bash
# All operations on a target
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local

# Mutating operations only (clicks, form input)
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local --mutatif

# From a date
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local \
  --depuis 2026-06-01
```