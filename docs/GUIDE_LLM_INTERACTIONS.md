# Dinoer — Interactions guide (actions, selectors, dialogs, assertions)

<!-- notice-version: 1.3 -->
Version 1.3 — August 2026. This number counts revisions of this notice, not
releases of Dinoer. Notable in the current text: full rewrite for the public
repo — the previous vision/numbering surface was removed; real action
semantics re-documented from the dispatcher (`shot.py`) and schema
(`schema.json`). Prior (v1.0/v1.1): `actions_invalides` error code,
`--wait-until` for never-idle targets, `repli_js` second-level escalation on
`cliquer`.

Load this notice when: timeout on `cliquer`/`remplir`, CSS/showModal dialog,
strict mode violation, nth-match error, `evaluer` assertions, `attendre_*`
actions, DOM mutations, iframes.

---

## `actions_invalides` — malformed or schema-rejected actions file

`shot.py --actions FILE` (Mode B) fires this before Playwright launches when
the file is not valid JSON, or fails validation against
`scenarios/schema.json` (unknown action `type`, missing required key, wrong
value type). The `message` field carries the underlying JSON/schema error —
read it, it names the offending key. Fix the file and relaunch; this is a
build-time error, not a runtime one, so nothing was executed against the
target.

---

## The action surface (v1.23.0) — 18 verbs

All verbs verified against `schema.json` and the `shot.py` dispatcher.
**Dinoer targets with CSS selectors, the `a11y_tree`, and `evaluer` — there is
no element numbering, no coordinates, no image analysis.**

| Verb | Required | Optional | Notes |
|---|---|---|---|
| `naviguer` | `url` | | Full HTTP reload — avoid in SPAs |
| `cliquer` | `selecteur` | `force`, `repli_js` | see sections below |
| `remplir` | `selecteur`, `valeur` | `secret_cle` | `depuis_secrets` requires `secret_cle` |
| `attendre` | `selecteur` | | Wait for visible selector |
| `attendre_navigation` | — | | Wait for a pending navigation |
| `pause` | `ms` | | Prefer `attendre_selecteur_present` for DOM signals |
| `evaluer` | `script` | `attendu`/`contient`/`motif` | assertion keys rpa.py-only |
| `defiler` | — | `px` or `selecteur` | one of the two required |
| `attendre_mfa_ntfy` | `selecteur` | `timeout` (default 120) | MFA code via ntfy |
| `attendre_url` | `motif` | `attendre_changement` | partial match — pitfall below |
| `attendre_selecteur_present` | `selecteur` | | wait `state=visible` |
| `attendre_absence` | `selecteur` | `delai_initial_ms` | wait `state=detached` |
| `attendre_reseau_calme` | — | `timeout_ms` | 500 ms network silence |
| `nettoyer_overlay` | `selecteur` | | explicit `visibility:hidden`, no auto-detection |
| `declencher_scenario` | `scenario` | | inline sub-scenario, max depth 5 (rpa.py) |
| `extraire_texte` | — | | cleaned text under `extraction_texte` |
| `cliquer_iframe` / `remplir_iframe` | `selecteur` (+`valeur`), `iframe_selecteur` or `iframe_chemin` | `force`, `secret_cle` | cross-origin, see iframes |

RPA-only (validated by `rpa.py`, accepted but inert in `shot.py`): the
`evaluer` assertion keys `attendu`/`contient`/`motif`, and
`declencher_scenario`.

---

## Decision tree — how to target an element

1. Element present in the DOM with a stable attribute (`#id`, `[name]`,
   `[data-*]`, `[aria-label]`) → `cliquer { "selecteur": "…" }`
2. Element not yet visible, discover it via `a11y_tree` or `evaluer`, then use
   `attendre_selecteur_present` before `cliquer`
3. Element is in the DOM but CSS-hidden or behind `showModal()` →
   `cliquer { "selecteur": "…", "force": true }` (v1.11.0)
4. `force` fails (interactability/obstruction, not absence) → add
   `"repli_js": true` (v1.22.0), see below
5. Element not yet in the DOM → `evaluer` JS `.click()`

**Priority order for stable CSS selectors:**
1. `[data-testid=…]`, `[data-test=…]` — dedicated test attributes (v1.15.2,
   DeepSeek D2), deliberately stable across style/markup refactors; prefer
   them over `#id` even when both are present
2. `#id` — stable (avoid if generated randomly by framework)
3. `[name=…]`, `[aria-label=…]`, `[title*=…]`, `[data-*=…]` — other semantic
   attributes
4. `:has-text("…")` — last resort, breaks on i18n changes

```json
{"type": "cliquer", "selecteur": "[data-testid=\"btn-confirm\"]"}
```

---

## `force: true` on `cliquer` — bypass interactability checks (v1.11.0)

Playwright refuses to click an element if it or an ancestor is CSS-hidden
(`display:none`, `visibility:hidden`), overlapping, or inside a `showModal()`
dialog. `force: true` keeps you in the same verb:

```json
{"type": "cliquer", "selecteur": "#dialog-confirm button[type=submit]", "force": true}
```

| Situation | Action |
|---|---|
| Element visible, no obstruction | `cliquer` without `force` |
| Element in DOM but CSS-hidden or obstructed | `cliquer` with `"force": true` |
| `force` still fails (interactability/obstruction) | add `"repli_js": true` |
| Element not yet in the DOM | `evaluer` JS `.click()` |

---

## `repli_js` on `cliquer` — second-level escalation (v1.22.0)

Distinct from `force: true`, not a replacement. `force` bypasses Playwright's
own interactability check; `repli_js` is a second level, tried **only after a
native click (with or without `force`) still fails** on an
interactability/obstruction error — this is exactly the FN14 case below,
where `force: true` alone was confirmed insufficient on a script-opened
`<dialog>`.

```json
{"type": "cliquer", "selecteur": "#dialog-confirm button[type=submit]", "force": true, "repli_js": true}
```

On failure Dinoer retries with `page.eval_on_selector(selecteur, "el => el.click()")`
— the same JS click you would otherwise write by hand in `evaluer`, built into
`cliquer` itself. `boussole.repli_js_utilise: true` appears only when the
escalation actually ran (never just because the flag is set — same discipline
as `stealth_actif`).

**Incompatible with `--no-evaluer`:** `repli_js` executes JS, which
`--no-evaluer` forbids on the run. A scenario combining both is rejected at
validation (`arguments_incompatibles`, exit 2) before any browser launch —
never a silent no-op.

---

## `--wait-until` — initial navigation on a never-idle target (v1.22.0)

**Symptom:** `shot.py --url <target>` fails with `TimeoutError` on the initial
navigation, and raising `--timeout` changes nothing — 45 s fails exactly like
10 s. **Cause:** by default Dinoer waits for `networkidle` (500 ms of network
silence). A page that polls continuously — live-stats panel, dashboard with
refreshing counters, router admin UI — never produces that silence. This is
not a duration problem: the target will never "finish".

```bash
# shot.py — direct reconnaissance
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url http://<target>/ --wait-until load --a11y

# rpa.py — same flag, propagated to shot.py
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario ./login.json --wait-until load
```

A scenario can also carry it as a root property:

```json
{"url": "http://target.local/", "wait_until": "load", "actions": [...]}
```

The CLI flag wins over the scenario property — it carries a value, two values
do not add up.

| Value | Waits for | Use when |
|---|---|---|
| `networkidle` | 500 ms of network silence | default — unchanged, keep it unless it fails |
| `load` | `load` event (page and sub-resources) | continuous polling / live stats |
| `domcontentloaded` | HTML parsed, sub-resources pending | very heavy page, you only need the DOM |

Applies to the **initial navigation only** — the `naviguer` action is
unaffected (it already uses Playwright's `load` default). `boussole.wait_until`
reports the value only when it differs from the default. When the initial
navigation raises, Dinoer still reports a proof of failure, but that path
yields neither `a11y_tree` nor bookkeeping for acting — getting the navigation
to genuinely succeed is what gives you a map to act on.

---

## CSS-hidden and JS-controlled containers — the timeout trap

`Playwright: Locator.click: Timeout Xms exceeded` on an element you can see in
the DOM does **not** mean the selector is wrong. It means Playwright refuses
to click because the element (or one of its ancestors) is hidden via CSS or JS.

**Two solutions — prefer `force` first:**

```json
// Solution 1 — force: true (v1.11.0, preferred when element is in the DOM)
{"type": "cliquer", "selecteur": "[data-testid='btn-confirm']", "force": true}

// Solution 2 — evaluer JS (fallback when force fails or element absent)
{"type": "evaluer", "script": "document.querySelector('[data-testid=\"btn-confirm\"]').click()"}
```

This rule covers all hidden-container patterns (REX #61–63, FR-57, FN10–FN14):
- CSS `display:none → block` dialogs (app confirmation modals)
- `showModal()` native `<dialog>` elements
- CSS toggle-switch hidden `<input type="checkbox">`
- Button that opens a CSS modal (FN10): the trigger button itself may time out

**FN12 — Batch deletion dialog (native `<dialog open>`):**
```json
{"type": "evaluer", "script": "Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()==='Appliquer')?.click()"},
{"type": "pause", "ms": 1000},
{"type": "evaluer", "script": "Array.from(document.querySelectorAll('dialog[open] button')).find(b=>b.textContent.includes('Supprimer'))?.click()"}
```

**FN13 — Batch checkboxes — prefer a single `evaluer` over multiple `cliquer`:**
```json
{"type": "evaluer", "script": "(function(){ var cibles=['v1','v2']; Array.from(document.querySelectorAll('input[type=checkbox]')).filter(cb=>cibles.includes(cb.value)).forEach(cb=>{cb.checked=true;cb.dispatchEvent(new Event('change',{bubbles:true}));}); })()"}
```

**FN14 — `force: true` insufficient in a `<dialog>` opened by script (root cause unconfirmed):**
on a `<dialog>` opened via `evaluer` (`showModal()`), `cliquer` with `force: true`
on an inner element failed repeatedly with "Element is not visible". Root cause
not settled: a genuine limitation of `force` in this specific context, or a
timing race. Not generalized — a single-session observation. If `force: true`
fails on an element inside a script-opened `<dialog>`, do not keep retrying —
switch to `evaluer` JS for the whole sequence:
```json
{"type": "evaluer", "script": "(function(){ document.getElementById('dialog-supp-X').showModal(); var cb=document.querySelector('#confirm-checkbox'); cb.checked=true; cb.dispatchEvent(new Event('change',{bubbles:true})); document.querySelector('#btn-submit').click(); })()"}
```
Since v1.22.0, `repli_js: true` covers the simple single-click case without a
hand-written `evaluer` script. The manual `evaluer` form remains necessary for
multi-step sequences (opening the dialog, checking a box, then clicking).

**Conditional button with JS guard — silent no-op on `cliquer` (REX #62):**
```json
[
  {"type": "evaluer", "script": "document.querySelector('[data-testid=\"select-action\"]').value = 'delete'"},
  {"type": "cliquer", "selecteur": "[data-testid='btn-apply']"},
  {"type": "attendre_selecteur_present", "selecteur": "dialog#dialog-batch[open]"}
]
```

---

## `attendre_url` — partial-match pitfall (FR-55)

`attendre_url` matches a **substring** (`wait_for_url` wrapped as `** motif **`
glob). `/control/` matches `/control/login/` immediately, without waiting for
the post-login navigation. **Always pair it with a selector wait after a
submit** — either `attendre_selecteur_present` on a post-login element, or
`"attendre_changement": true` to wait for a real navigation before testing the
pattern:

```json
{"type": "cliquer", "selecteur": "button[type=submit]"},
{"type": "attendre_url", "motif": "/dashboard", "attendre_changement": true},
{"type": "attendre_selecteur_present", "selecteur": ".user-logged-in"}
```

---

## `evaluer` — DOM/JS introspection

Use when you need to read a value from the page:

```json
{"type": "evaluer", "script": "document.title"}
{"type": "evaluer", "script": "window.MyApp?.version ?? null"}
{"type": "evaluer", "script": "document.querySelectorAll('.row').length"}
```

Output appended to `evaluations[]` in JSON result:
```json
"evaluations": [{"index": 0, "script": "document.title", "valeur": "My App — home"}]
```

Non-JSON-serializable values fall back to `str(value)` with
`"serialisation": "str"`. Never inject user input or URL parameters into the
script.

**Security restriction — `--no-evaluer` (v1.15.1):** `evaluer` executes
arbitrary JavaScript in the browser context. In production scenarios involving
authentication forms, financial data, or any sensitive interface, the operator
may disable this action entirely by passing `--no-evaluer` to shot.py or
rpa.py. When active, any `evaluer` action raises an error and the run aborts —
an operator-level decision you cannot bypass.

**What this means for you:** if you use `evaluer` to read a value, you are
responsible for ensuring your script does not extract sensitive data
(passwords, tokens, cookies, session identifiers). Do not write scripts that
return `document.cookie`, `localStorage`, or any authentication token — even
if the intent is diagnostic. These values would appear in `evaluations[]` in
the JSON output.

---

## Assertions on `evaluer` — three keys (rpa.py only)

Three mutually exclusive assertion keys — choose one per action:

| Key | Comparison | Valid return types |
|---|---|---|
| `attendu` | Strict equality (`==`) | Any (str, int, bool) |
| `contient` | Substring (`in`) | `str` only |
| `motif` | Python `re.search()` regex | `str` only |

```json
{"type": "evaluer", "script": "document.querySelectorAll('.row').length", "attendu": 3}
{"type": "evaluer", "script": "document.title", "contient": "User management"}
{"type": "evaluer", "script": "window.location.href", "motif": "view=dashboard$"}
```

Error on wrong type: return value not `str` with `contient`/`motif` → exit 1
with an explicit message. Use `attendu` for int and bool. Error on conflict:
two assertion keys on the same action → exit 1. `shot.py` ignores all
assertion keys (they are rpa.py-only).

---

## Verify you are on the right page (pattern — item F)

Always end a navigation with a semantic assertion, not just a generic
`attendre_selecteur_present`:

```json
// With <title>
{"type": "evaluer", "script": "document.title", "contient": "User management"}

// Without <title> — use h1
{"type": "evaluer",
 "script": "document.querySelector('h1')?.textContent.trim() ?? ''",
 "contient": "User management"}
```

On error pages (404/500) the title is the error template's — `contient` fails
cleanly with exit 1. No extra code needed.

---

## `attendre_*` family — wait primitives

| Verb | Waits for | Notes |
|---|---|---|
| `attendre` | selector present in DOM (`state=attached`) | `wait_for_selector` without `state=visible` |
| `attendre_navigation` | `networkidle` | use after a click that navigates |
| `attendre_selecteur_present` | selector visible (`state=visible`) | preferred over `pause` |
| `attendre_absence` | selector `state=detached` | `delai_initial_ms` to skip a flash that would loop |
| `attendre_reseau_calme` | 500 ms of network silence | `timeout_ms` = max wait before abort (distinct from the internal 500 ms) |
| `attendre_mfa_ntfy` | TOTP code arriving over ntfy | fills the field itself; `timeout` secs, default 120 |

`attendre_mfa_ntfy` takes a `selecteur` (the field to fill with the received
code) — there is no element numbering in Dinoer.

---

## `nettoyer_overlay` — hide fixed overlays before reading

`visibility:hidden !important` on every element matching the selector — an
explicit CSS selector is **required** (`{"type":"nettoyer_overlay","selecteur":".cookie-banner"}`);
there is no auto-detection. Use it before `a11y_tree`/`extraire_texte` when a
fixed banner clutters the page state.

---

## Iframes — cross-origin primitive (v1.17.0)

Same-Origin Policy blocks JS injection from reaching into a cross-origin
iframe's content. Playwright's `frame_locator()` bypasses this via CDP —
Dinoer exposes it through two scoped actions:

```json
{"type": "cliquer_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "button.valider"}
{"type": "remplir_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`remplir_iframe` supports `depuis_secrets`/`depuis_secrets_totp` exactly like
`remplir` — never a plaintext credential in a scenario.

**On failure:** Playwright's own interactability rules still apply inside the
frame — `"force": true` is available on `cliquer_iframe`, matching `cliquer`.

**Nested iframes — `iframe_chemin` (v1.18.0):** an ordered array of CSS
selectors, one per nesting level; chains `frame_locator()` once per element:

```json
{"type": "cliquer_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "button.valider"}
```

**`iframe_selecteur` and `iframe_chemin` are mutually exclusive — exactly one
required.** Passing both, or neither, is a schema error. For a single-level
iframe keep `iframe_selecteur`; `iframe_chemin` is strictly for multi-level
descent. No hard-coded depth limit — but expect resolution time to grow with
each level, and treat a very long chain as a signal to look for a shorter path
first (same-origin frames may be reachable via `evaluer`
`contentDocument` directly).

---

## Selectors — pitfalls and patterns

- **Domain names in link selectors — strict mode violation (FN5):** a domain
  like `example.fr` typically appears in multiple `<a>` elements (header,
  clone link, breadcrumb) → strict mode refusal. Never use domain names as
  link text selectors — navigate by direct URL instead.

- **`:nth-match` chaining rule (FN6):**
```json
// WRONG — "nth-match engine expects non-empty selector list and an index argument"
// (does not exist as written; wrap the full expression)
// CORRECT
{"type": "cliquer", "selecteur": ":nth-match(button:has-text(\"Texte\"), 2)"}
```

- Playwright extended selectors supported: `:has-text("…")`, `:visible`,
  `:nth-match(N)`. Avoid relational pseudo-selectors (`:left-of`,
  `:right-of`, `:near`) — version-sensitive.

---

## Reconnaissance before mutation (bloquant)

Before writing any mutating action on a feature **never previously tested with
Dinoer**:

```bash
# Step 1 — Accessible map + DOM state
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url <target_url> --a11y

# Step 2 — DOM inventory via scenario
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/diagnostic_dom.json \
  --url <target_url>

# Step 3 — Read eval results, extract selectors
# Step 4 — Write complete operational scenario in one pass
# Step 5 — Execute once via rpa.py
```

**Forbidden:** launching a mutating action without completing steps 1–3.

No `actions_v2.json`/`_v3.json` in `/tmp/` without the Stop-and-Search step
(see the main guide).

---

## Error recovery — Stop-and-Search rule (bloquant)

If an action returns `succes: false` or a Playwright error, you must:

1. Re-read the relevant section of this notice
2. Declare the analysis: cause identified, rule violated
3. Propose the correction
4. Stop until validated