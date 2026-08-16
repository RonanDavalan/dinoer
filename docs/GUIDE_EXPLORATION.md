# Dinoer — Exploration and mapping guide

Version 1.3 — August 2026 (v1.23.0) — surface realigned to the Dinoer
reconstruction: no screenshot, no Set-of-Mark; the map is drawn from
`a11y_tree` and `evaluer`.

**This document is for language models using Dinoer.**

It describes the "Exploration before Execution" protocol: how to map an unknown
interface soberly, then automate it without improvisation.

---

## The problem this guide solves

A model launched on an unknown interface without preparation navigates blind:
it fumbles, retries, burns tokens to rediscover what it could have
known from the start. This is the "headless chicken" problem.

The solution: **two distinct modes, two distinct objectives.**

---

## Exploration Mode — The first pass

**Objective**: draw the interface map, identify stable selectors.

**Rule**: read-only. No mutating action.

**Typical invocations:**

Read the page state and accessibility tree (read-only):
```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y
```

Read the page state, then extract a precise DOM value:
```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --actions /tmp/explore.json
```
where `/tmp/explore.json` holds read-only `evaluer` actions.

**What to extract:**
- `boussole.url_courante` + `boussole.titre_page` → confirmation of effective URL and page title
- `a11y_tree` → accessibility tree (fields, buttons, headings, structure)
- `evaluations` → values pulled from the DOM via `evaluer`
- `etat.pret_a_agir` + `etat.raisons` → frictions perceived before you act

**What to look for:**
1. Selectors for form fields (login, password, etc.)
2. Stable attributes (`name`, `id`, `aria-label`, `data-*`) over generated ones
3. Blocking elements (cookie banners, overlays, sticky headers)
4. Navigation behaviour (SPA or full HTTP reload?)
5. Presence of `<iframe>` elements (same or cross-origin) — note the frame's own CSS
   selector for `cliquer_iframe`/`remplir_iframe` (v1.17.0). Frame content is not
   reachable by selector from the top document — target it through the frame
   primitives.
6. If the page mutates frequently (live counters, async content insertion): plan
   on order-stable selectors, or re-read the tree with a fresh `--a11y` call
   right before the mutating action.

**Expected output**: a JSON scenario file in `scenarios/` or
`_CADRE/SPECIFICATIONS/PROCEDURES_LLM/instance/`.

---

## Writing the map — The JSON scenario

After exploration, the procedure is locked into a scenario file.

**Basic format:**
```json
{
  "nom": "pretix_login",
  "url": "https://target.local/control/login/",
  "intention": "Administrator login with stored credentials",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"},
    {"type": "attendre_selecteur_present", "selecteur": ".user-logged-in"}
  ]
}
```

**Selector priority (all CSS-based — there is no element numbering):**

| Priority | Selector | When to use |
|---|---|---|
| 1 | `[name=…]`, `[id=…]`, `[aria-label=…]`, `[data-*]` | Stable attribute, survives reloads |
| 2 | `input[type=password]`, `button[type=submit]` | Typed, unambiguous, survives translations |
| 3 | `:has-text("…")` | Last resort, fragile under translation |

**What to avoid:**
- Positional selectors (`:first-child`, `:nth-child`) — fragile
- Framework-generated random IDs
- Writing a fresh CSS selector from memory instead of reading it from the tree

---

## Execution Mode — Subsequent passes

**Objective**: replay the map without improvisation.

**Invocation:**
```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/pretix_login.json
```

**Zero fumbling.** The scenario was validated in exploration. If the scenario
fails, it is a signal: the interface has changed. Re-run exploration,
do not improvise in-line.

---

## Handling common obstacles

### Cookie banner / blocking overlay

In exploration, note the CSS class of the overlay. Add it to the scenario
with `nettoyer_overlay` **before** any action:

```json
{"type": "nettoyer_overlay", "selecteur": ".cookie-consent-banner, #gdpr-overlay"}
```

**Important:** `nettoyer_overlay` requires an explicit selector.

### Waiting in modern applications (SPAs)

Replace arbitrary `pause` with semantic wait primitives:

```json
{"type": "attendre_url",               "motif": "/dashboard"},
{"type": "attendre_selecteur_present", "selecteur": "[data-testid='user-menu']"},
{"type": "attendre_absence",           "selecteur": ".loading-spinner"},
{"type": "attendre_reseau_calme",      "timeout_ms": 10000}
```

`attendre_url` matches a **substring** (FR-55 pitfall): always pair it with
`attendre_selecteur_present` after a submit so a partial match on the login URL
does not short-circuit your wait. After a form submission, wait on a selector
that only exists post-login — never on the URL alone.

### Django application with sudo redirects

Django applications (Pretix, Django admin) redirect some protected URLs
via a sudo middleware. Mandatory sequence in a single Mode A call:
`login → reauth → target` without intermediate session.

Never use `naviguer` in a resumed session on Django — it redirects
to the dashboard (REX friction #50). Pass the URL directly via `--url`.

---

## Semantic memory — Linking scenario and documentation

**Separation of concerns:**
Dinoer provides the **mechanics** (`/opt/dinoer/skills/`, `journal.py --exporter-skill`).
The **semantic memory** of validated scenarios belongs to the project using Dinoer,
in its own `_CADRE/SPECIFICATIONS/PROCEDURES_LLM/`.

For each validated scenario, create a `SKILL_<name>.md` file in the `_CADRE/`
of the **user project** (not in Dinoer's `_CADRE/`):

**`SKILL_pretix_login.md`** (in your project's _CADRE):
```markdown
---
skill: pretix-login
scenario: pretix_login.json
cible: __HOST_SERVICE__
type: skill-rejoue
derniere-validation: YYYY-MM-DD
---

Administrator Pretix login with stored credentials.
Prerequisites: encrypted directory mounted, `__HOST_SERVICE__.json` file present.
```

The file is indexed by the project's RAG. The agent finds the skill by
semantic search, reads the `scenario:` key, executes with `rpa.py --scenario`.

The reference template is `SKILL_TEMPLATE.md` in `_CADRE/SPECIFICATIONS/PROCEDURES_LLM/`.

---

## Exploration checklist

Before writing a scenario:

- [ ] `shot.py --a11y` run on the target URL to verify URL, title and structure (boussole)
- [ ] `evaluer` probes run for the values the task actually needs (prices, counts, states)
- [ ] If `<iframe>` elements are present: note their CSS selector for `cliquer_iframe`/`remplir_iframe`
- [ ] Stable selectors noted (attributes `name`, `id`, `aria-label`)
- [ ] Blocking overlays spotted and their CSS selectors noted
- [ ] SPA or full-HTTP behaviour determined (`boussole.url_courante` vs `a11y_tree` heading)
- [ ] If auth_indicator needed: test `--auth-indicator <sel>` [+ `--auth-indicator-negative <sel>` if selector is ambiguous]
- [ ] Credentials verified for this domain (`urlparse(url).hostname`)
- [ ] JSON scenario written and saved in `scenarios/`
- [ ] `SKILL_<name>.md` file created in the user project's `_CADRE/` (not in Dinoer's `_CADRE/`)