# Development journal — Dinoer

History of decisions and discoveries by session, in reverse chronological order.

---

## 2026-08-15/16 — Download page redesign, package version fixed, eight rounds of cross-model audit

Direct continuation of Lot D/the 1.0.0 packaging work (previous entries).
Three threads, in the order they actually happened.

**1. Download page rebuilt, several times, on direct feedback.** The
header's version link pointed at a checksums page instead of a real
download page (`guides/checksums/`, `translationKey: "checksums"`) — moved
to a dedicated root page per language (`/telechargements/`, `/downloads/`,
`/descargas/`, `translationKey: "download-page"`), generated fresh by
`deploy-site.sh` from the actually-published artifacts, never hand-edited.
Went through several corrections on direct signal from Ronan, each one a
real fix, not polish for its own sake: redundant "Paquet"/"Sources"
sub-headings dropped (the logo already says it), a paragraph removed then
restored after Ronan pointed out nothing had been asked to be deleted,
checksums collapsed into `<details>` instead of one dominant code block, a
genuine CSS bug found from a screenshot (Debian logo rendering at its raw
108×144 intrinsic size, the same `height="32"`-ignored-by-global-CSS defect
already fixed once for the header but never replicated here), and finally
a duplicate "Verification" card removed once Ronan pointed out it repeated
the guide's own card verbatim. A note was written in Diwall's own
`_CADRE/MEMOIRE/` so the same design, once Ronan is satisfied with it, can
be ported there without re-deriving it from scratch.

**2. `shot.py`/`rpa.py`/`journal.py` `__version__` reset 1.23.0 → 1.0.0.**
Same principle already applied to the package version itself: a version
number is a factual claim about release history, and `1.23.0` was Diwall's
number, inherited literally, asserting 22 Dinoer releases that never
happened. `campagne.py` stayed at `0.1.0` — a real, honest number for
genuinely new code, not a stale inheritance, confirmed explicitly by Ronan
when a later audit re-raised it.

**3. Eight rounds of independent LLM audits (DeepSeek, GLM 5.2, OpenCode,
across several passes each), every finding checked against the real code
or site before acting — several were false positives (a prior audit's
claim about `mutatif` being undocumented was wrong when checked; tonight,
"broken" links in the fr/de/es journal pages turned out to be unlinked
prose, not dead hrefs).** What survived verification, roughly by severity:

- `scripts/verifier-coherence.sh` — the tool meant to catch exactly this
  class of drift — had never actually been ported from Diwall: `../Diwall`
  path, `DIWALL_*` env vars, a version regex anchored on `^diwall (`,
  `watch.py` in three iteration lists. It silently checked nothing real.
  Ported for real; running it now correctly (and only) flags
  `GUIDE_LLM.md`'s real line-budget overflow and `GUIDE.md`'s stale version
  header — both fixed. `GUIDE_LLM.md` trimmed from 376 to exactly 250
  lines: version history collapsed to the current entry, the
  `campagne.py`-specific extraction-recipe/synthesis-relevance sections
  moved to `GUIDE_LLM_MONITORING.md` where the routing table already said
  they lived, prose tightened elsewhere without cutting any safety fact.
- `scripts/monitor-verifier.sh` called `rpa.py --no-capture` — confirmed by
  direct run that this crashed every real invocation
  (`unrecognized arguments: --no-capture`) — already flagged as "known
  debt" in two docs but never fixed in the script itself, until now.
- `dinoer.conf.d/` — read by `lib/profil_operateur.py` for the
  operator-profile mechanism — was never deployed by either channel
  (`deploy.sh` nor `debian/dinoer.install`). Wired into both, verified with
  a real package rebuild and a real upgrade-in-place on `ada`.
- Several docs described removed/nonexistent capabilities as if current:
  `--mode`, `--so`m, `watch.py --comparer-pixel`/`--sauver-reference`, a
  `sillage_login.json` example file that doesn't exist (real files:
  `example_login.json`), `state=attached` for `attendre` where the real
  Playwright default is `visible`, `boussole.session_derive` documented as
  a boolean where the code emits an object, `a11y_tree`/`evaluations`
  claimed always-present where both are conditional, journal `outil`
  claimed to include `"rpa.py"` where only `shot.py`/`campagne.py` ever
  write it, a checksum recipe hashing only two of the four real
  `_CHAMPS_CHECKSUM` fields, `/tmp/dinoer/<operation_id>/` claimed as the
  evidence directory where the real path is
  `preuves/<AAAA-MM>/<operation_id>/`.
- The site itself asserted "Git clone only, no `.deb` yet" in four places
  written before the first real `.deb` release the same week
  (`guides/_index.md` in all four languages, `static/instructions.md` —
  the machine entry point, `static/llms.txt`, an `.htaccess` comment) —
  all stale, none resynced when the package shipped. Also removed: a
  leftover `index.html` at the site repo root, the original single-page
  Diwall prototype, dead since the Hugo rebuild.
- Translation debt: `docs/{fr,de,es}/README.md` still described a
  Git-clone-only install path, were missing the entire "Positioning"
  section, and omitted `lib/selection_candidats.py` from the architecture
  diagram — resynced through the real local pipeline (`traduire.py`,
  Ollama), not by hand, with the couple of pipeline-rejected segments
  hand-corrected as the declared last step only.

Nine to eleven commits total across `Dinoer/Dinoer` and
`dinoer.davalan.fr` this session — see
`_CADRE/MEMOIRE/ADDENDUM_2026_08_15.md` for the exact hash-by-hash record.

---

## 2026-08-14 (very late) — Lot D: the public site rebuilt for what Dinoer actually is

Ronan green-lit Lot D directly ("no QCM, no planning, go all the way"),
skipping the audit-then-write split the repositioning plan had scoped —
scope judged self-evident enough from the already-closed A1-A4/B1-B3 work
to execute in one pass.

**What the site still was, verified by reading it rather than assumed:**
Diwall's own site, unmodified beyond a title-and-link find/replace — Set-of-
Mark, a local/remote vision model, PNG captures on every page, a `.deb`
release channel with checksums/downloads/version pages, and Diwall's own
pre-fork development log and French-language field notes presented as if
they were Dinoer's history. None of it is true of Dinoer: the perception
layer was fully removed 09/08/2026, there is no packaged release
(`README.md` says so explicitly), and Dinoer's own history starts at the
25/07/2026 fork.

**Rebuilt from what the code and this repository's own docs actually say**,
not from the old copy renamed: homepage and positioning drawn from
`README.md`/`GUIDE_LLM.md` (traceable synthesis of a locked corpus, not
discovery-breadth competition — the 14/08 verdict, cited with its evidence
rather than restated as opinion); a new "Running a research campaign" guide
and use case documenting `campagne.py` for the first time on the site (the
manifest format, the two-field reordering fix, `--extraire-cible`,
`opencode.jsonc`); architecture/limits pages grounded in the real 14/08
findings (the SearXNG discovery gap, the JS-banner escalation-heuristic
bug, the twelve-`websearch`-call leak and its residual `bash curl` gap);
perception pages rewritten around "text, never pixels, in any mode" instead
of demoting screenshots to optional. JSON examples throughout are real
output, captured live against `https://example.com` and the repository's
own shipped example scenarios (`sondage_fast.json`, `diagnostic_dom.json`)
in a disposable venv — not invented, and none of the private fields
(hostname, real username, LAN IP) were published. Pages with no Dinoer
equivalent were removed rather than reworded: package downloads/checksums,
page-watching (`watch.py` doesn't exist), packaged versions, the local-
diagnostic use case, and Diwall's own field notes/dev log.

**Two real, previously undetected bugs found by verifying instead of
presuming, per the guide's own non-presumption rule:**
- `scripts/i18n/site_i18n.py::RACINE_SITE` still pointed at Diwall's own
  site checkout — the shared translation tooling under
  `~/git/Dinoer/scripts/i18n/` had never been repointed at this site,
  meaning `traduire-site.py` would have silently translated the *other*
  project's site. Fixed.
- `--shadow-dom` and other flags implied by the consolidated spec
  (`24_PHASE4_BOUCLE_AGENTIQUE.md`) do not exist in `shot.py`/`rpa.py`
  (checked by grep, not assumed either way) — the site was written to
  match the verified flag set, not the spec's broader claim. Spec drift
  flagged for a future documentation pass, not corrected here (code-doc
  drift, not site-doc drift).

**Translation:** delegated to the local GPU pipeline
(`translategemma:12b-it-q4_K_M` via Ollama, `traduire-site.py`), per
Ronan's explicit instruction not to spend model tokens translating by
hand. `PAGES_PROTEGEES`/`CORPS_NON_TRADUIT` in `site_i18n.py` — both
keyed to the old Diwall-era hand-reviewed copy — were cleared rather than
carried over, since every English source page changed. Reviewed the
output against the same non-presumption discipline as the English content:
~35 silently-untranslated paragraphs across fr/de/es (segmentation edges
the pipeline's own reject filters didn't catch) fixed by hand, plus three
real mistranslations that inverted meaning — French "elle a fusionné
correctement" read as "correctly merged" where the source said "correctly
excluded", German "Diners" for "Dinoer's" (phonetic slip), Spanish "el
modelo... está autorizado a **modificar**" for "is allowed to **leave**"
the corpus (the opposite claim, on the page about corpus containment).

**Commit** (the public site's own git checkout, a separate repository not
tracked here): `56e74fe`. Its directory renamed to lowercase per the
casing `~/git/Dinoer/scripts/preflight-publication.sh` already expected.
`deploy-site.sh` rewritten to drop the Diwall packaging/PDF
pipeline (no artifacts to serve) and fix its Diwall-repo paths; verified
end to end in simulation mode (`bash deploy-site.sh`, no `--publier`):
preflight clean after one documented exception added (mirrors the
already-judged `ronan-davalan-ereputation-2026-08-14` non-leak, now also
present in the site's generated journal copy), Hugo build clean (zero
broken internal links, checked mechanically across all four languages),
dry-run rsync produced the expected file list.

**Not done, deliberately out of scope for Lot D:** no attempt to verify or
create the `Davalan:~/dinoer/` remote hosting path `deploy-site.sh`
assumes by convention (never confirmed to exist); no Matomo site ID
configured (would mix Dinoer's traffic into Diwall's own analytics under
the shared instance if guessed); actual publication (`--publier`) not run —
matches Lot D's original scope (site reconstruction), not C1 (the
publication decision, reserved for Ronan).

---

## 2026-08-14 (late) — B1-B3 of the repositioning plan executed; two real deploy bugs found by a real cold-install test

PHASE_EXECUTION greenlit by Ronan for B1-B3 of the repositioning plan (see
previous entry): rewrite `README.md`/`docs/MANUEL.md` for the narrower
positioning, fix `preflight-publication.sh`, run a real cold install test.

**B1 — `README.md` repositioned.** A new "Positioning: what Dinoer competes
on, and what it doesn't" section states plainly, with the 14/08 real test as
evidence, that Dinoer does not compete with generalist search assistants on
discovery breadth/volume/price, and scopes its actual verified value
(traceable, reproducible synthesis of a locked corpus) precisely. The
existing "outperformed Perplexity" claim (from the unrelated 11-12/08
territorial-events campaign) was narrowed to the one task it was actually
measured on, with a pointer to the new section so it no longer reads as a
general claim. `docs/MANUEL.md` needed no change — pure command reference,
no positioning claims found in it.

**B2 — `preflight-publication.sh` : the documented smoke-test debt (stale
`--som`/`watch.py`/`diwall` group) turned out already fixed**, not by this
session — the script's smoke-test section already tests `--a11y`/
`extraire_texte` with no `watch.py`/`--som`/group-`diwall` residue (comment
dated 11/08/2026). The governance note describing this as outstanding debt
(`A_COMMUNICATION.md` §7) is now stale and needs correcting in a future
PHASE_DOCUMENTATION. Running the script for real did find one genuine,
currently-blocking leak: a campaign slug
(`ronan-davalan-ereputation-2026-08-14`) matched the "tenant nominal"
pattern in `docs/JOURNAL.md`. Not a real leak (the campaign's own subject
consented to being its test subject — already judged so in
`ADDENDUM_2026_08_14.md`), so a documented exception was added to
`EXCEPTIONS` rather than rewording the journal text. Preflight now passes
clean (`OK — aucune fuite, smoke test réussi`).

**B3 — real cold install test, run on a real machine of the fleet (not the
main development/production machine, which has never had `/opt/dinoer/`)**: existing leftover
`/opt/dinoer/` backed up, `dinoer` user+group removed, directory purged,
fresh source deployed, `scripts/install.sh` run end to end. Found two real
bugs no code review had caught:

- **`scripts/deploy.sh`'s `CODE_FILES` list was missing `campagne.py` and
  nine `lib/*.py` modules** (`lib/sanitisation.py`,
  `lib/searxng.py`, `lib/fetch_leger.py`, `lib/synthese.py`,
  `lib/extraction.py`, `lib/selection_candidats.py`,
  `lib/tables_reference.py`, `lib/cache_recherche.py`,
  `lib/validation_scenario.py`) — a fresh install crashed on the very first
  `shot.py` invocation (`ModuleNotFoundError: lib.sanitisation`), and
  `campagne.py` — the research pipeline the README documents as the
  product's main capability — was entirely absent from a freshly deployed
  `/opt/dinoer/`. Same bug class already fixed once, 07/08/2026, on the
  `.deb` packaging channel (`debian/dinoer.install`) — never carried over to
  this channel (`scripts/deploy.sh`, the one channel the product actually
  ships through today, per README). Fixed: `CODE_FILES` now lists every
  `lib/*.py` on disk plus `campagne.py`.
- **`scripts/install.sh` and `scripts/preflight-publication.sh` (usine)
  both hard-coded a stale `GUIDE_VERSION`** (`1.3` and `1.2` respectively)
  against the real, current value (`1.6`, `lib/preflight_guide.py::GUIDE_VERSION_ATTENDUE`
  and `docs/GUIDE_LLM.md`'s `notice-version`) — the smoke test itself failed
  with `guide_non_lu` before either deploy bug was even visible. Both
  bumped to `1.6`.

Both smoke tests (`shot.py --a11y`, `shot.py --action extraire_texte`) pass
clean after both fixes; `campagne.py` imports cleanly from the deployed
copy (`__version__ 0.1.0`). Re-validated `preflight-publication.sh` clean
after all edits (no new leak introduced by the fix comments themselves — an
early draft named the test machine directly in a `deploy.sh` comment,
caught and reworded before commit).

**Remaining, not done this session (PHASE_DOCUMENTATION scope):** update
`A_COMMUNICATION.md` §7 (stale smoke-test debt description), close out this
entry in the next `_CADRE/MEMOIRE/ADDENDUM_*.md` (frozen during
PHASE_EXECUTION), C1 (publication decision) still reserved for Ronan.

---

## 2026-08-14 (evening) — "zones grises" thesis tested and not supported; two real corpus bugs found; project repositioned

Real-target test (not synthetic): a campaign on "Ronan Davalan" (person and
sole-trader business, self-consenting — no third-party privacy question),
prompt candidate 3 (e-reputation) of `TACHE_zones_grises_valeur_reelle.md`,
condition A only (Dinoer, corpus locked by `opencode.jsonc`).

**Result:** 28 pages collected at the light tier, 0/1 escalated successfully
to the heavy tier. Report and corpus checked out well on synthesis quality —
correctly flagged a 3-way source disagreement on RCS registration status
(Figaro vs Pappers vs infonet) and correctly excluded a same-surname
homonym (Ronan Vaillant, different SIREN) instead of merging him in.
Anti-leak check replayed manually (direct `subprocess` + `--format json`
call, not `invoquer_opencode()` which discards `tool_use` events): the full
JSON stream contained exactly 3 events (`step_start`, `text`,
`step_finish`) — zero `tool_use`, so zero `websearch`/`webfetch`/`bash`
reached. Proof kept alongside the corpus (see below).

**But measured against the actual thesis being tested (does Dinoer surface
what a generalist web-search-augmented model misses), the result went the
other way.** A single unengineered Perplexity query ("Que peux-tu me dire
sur Ronan Davalan ?") surfaced LinkedIn, the PiperRead project page, and
Shutterstock credits — **none of which appear anywhere in the 28 collected
pages**, verified against the raw `collecte.jsonl`, not assumed. Root
cause: the 3 SearXNG queries used were aimed at company directories, not at
the kind of query that would surface those pages — a discovery gap, not a
ranking/truncation gap.

**Second, independent bug found in the same corpus:** `github.com/RonanDavalan`
and `m.youtube.com/@RonanDavalan` were both found and fetched, but their
collected text is cookie/login banner noise only (`"Se connecter... nous
utilisons des cookies..."`, `"You signed in with another tab"`) — the light
tier can't execute their JS, and heavy-tier escalation never triggered for
either page. The escalation trigger heuristic currently keys off "empty
text", not "text collected but unusable" — a real, distinct architecture
gap, not a query-formulation problem.

**Decision (discussed openly with Ronan, no filter):** the "zones grises"
thesis is not supported by this test, and the reasons given are structural
(SearXNG degrades without authenticated/cookie-backed search engines;
hardened sites like LinkedIn resist scraping regardless of the escalation
heuristic) rather than a one-off bug queue to clear. Chasing parity with
generalist web-search-augmented models on discovery is judged not worth
further engineering investment. What the test did validate: synthesis
quality on an already-found corpus, and full traceability
(`collecte.jsonl`/`operations.jsonl`, no dependency on what a third-party
websearch backend actually does) — a narrower value proposition than the
one the project carried into this test. A repositioning plan was proposed
(close the zones-grises task honestly, correct `CARACTERISATION_DINOER.md`
§2, mark discovery-improvement work "evaluated, not pursued" in the
roadmap, rewrite public positioning, fix known `preflight-publication.sh`
debt, run a cold install test).

**PHASE_DOCUMENTATION greenlit and executed the same evening:**
`TACHE_zones_grises_valeur_reelle.md` closed with the verdict above (condition
A verified, condition B interrupted, condition C/D never run to the blind
protocol this task required — documented as such, not conflated with the
informal Perplexity check); `CARACTERISATION_DINOER.md` §2 rewritten in
place (the old "zones grises" claim replaced, not appended below — the
narrower "traceable synthesis of a locked corpus" positioning is now what
§2 states). Remaining items of the repositioning plan (roadmap markers,
public-facing docs rewrite, `preflight-publication.sh` fix, cold install
test, publication decision) are still open — see
`_CADRE/MEMOIRE/ADDENDUM_2026_08_14.md` for the full plan.

Condition B (same prompt, free model, `opencode.jsonc` inactive) was
launched and deliberately interrupted (`kill`, empty output file confirmed,
no partial/corrupted data) once Ronan decided not to pursue the full formal
B/C/D/E protocol.

**Artefacts** (outside this repo, `~/git/Dinoer/campagnes_dev/`, not
git-tracked — instance test data): `ronan-davalan-ereputation-2026-08-14/collecte.jsonl`,
`rapport_20260814T004650Z.md`,
`flux_brut_verification_zero_websearch_20260814.jsonl`.

---

## 2026-08-14 — `opencode.jsonc` added: the reasoning backend can silently bypass the collected corpus

Real-campaign discovery, not theoretical: `invoquer_opencode()` inherits
whatever permissions the **global** OpenCode config grants
(`~/.config/opencode/opencode.jsonc` on the development machine — `websearch`/`webfetch` set
to `allow`, a reasonable default for general OpenCode use, but not for
Dinoer's own guarantee that a synthesis is built only from the collected
corpus). Verified in a real run: given latitude to "plan before extracting,"
DeepSeek made 12 `websearch` calls and sourced content absent from
`collecte.jsonl` — invisible in the final text, found only by capturing the
full JSON event stream (`invoquer_opencode()` only returns the final text,
discards `tool_use` events).

Added this repository's own `opencode.jsonc` (project-local, overrides the
global config for any `opencode run` invoked from this directory):
`websearch: deny`, `webfetch: deny`, `bash: allow` (kept open — required for
scenarios that ask the model to `curl` a notification). Verified twice: the
model correctly refuses `websearch`/`webfetch` ("I don't have that tool"),
but a residual gap remains — a model denied `websearch` immediately used
`bash curl` against a public weather API instead. Documented as a reduced
surface, not a closed one.

**Commit:** `3a27ced` — ajoute opencode.jsonc pour contenir le backend de
raisonnement au corpus. `docs/GUIDE_LLM.md` updated in the same commit
(new "Containing the reasoning backend" section, `notice-version` 1.5 → 1.6).

---

## 2026-08-13 (later) — Synthesis context now reorders pages by temporal window and semantic relevance

Session 3+4 of `TACHE_fiabilisation_synthese_campagne.md`. `construire_contexte()`
(`lib/synthese.py`) concatenated the collected corpus in file-write order,
truncated at 60000 chars, no relevance ranking — root cause of the report
quality gap documented earlier today. Measured against the reference
campaign: a coarse textual pre-filter alone (`mentionne_fenetre_probable()`,
zero model call) was **not enough** — the two pages of the official event
program passed the boolean filter but still ranked 27th-28th of 29
"probable" pages by write order, still outside the truncation budget.
Semantic ranking (`lib/vector.py::embed()`, Ollama `nomic-embed-text`,
cosine similarity to a `sujet_synthese` sentence) correctly moved them to
4th/7th — measured cost negligible (a few seconds, ephemeral, no ChromaDB
collection persisted).

`construire_contexte()` gained two independent optional parameters
(`motifs_annee`/`motifs_mois`, `sujet_synthese`) and now returns a
3-tuple `(contexte, sources, pages_repoussees)`; `campagne.py` reads both
from two new optional manifest fields, defaulting to the exact
pre-existing behaviour when absent. `lib/extraction.py::extraire_cible()`
(the only other caller) updated for the new return arity. A module-level
circular import (`lib.extraction` <-> `lib.synthese`) surfaced and was
fixed with a deferred import.

New test file `tests/test_construire_contexte.py` (4 tests: 3 pure/CI-safe,
1 ground-truth against the real reference corpus with a real `embed()`
call, self-skipping when that corpus or Ollama are absent). `GUIDE_LLM.md`
gained a "Synthesis relevance" section documenting both manifest fields;
`notice-version`/`GUIDE_VERSION_ATTENDUE` bumped together, 1.4 → 1.5.

**Discarded, and why:** ranking by raw keyword density instead of
embeddings — correctly promoted the Concarneau PDF but misranked a second,
equally relevant source (`festival-cornouaille.bzh/programmation/`) near
the bottom (score of 1 occurrence) — too dependent on each source's
writing style to be a general method.

**Commit:** `6380a4b` — cable pre-filtre temporel + classement semantique
dans construire_contexte().

---

## 2026-08-13 (night, late) — README corrected: automatic report is a draft, not the proof

Ronan asked whether Dinoer was ready to push to a public repo. Answer: no —
not for leaked secrets or a broken script (`preflight-publication.sh` passes
clean), but because the only quality proof the repo can point to (a report
that outperformed Perplexity on a real research task, campaign
`spectacles-sud-finistere-2026-08-11-20`) was not produced by the automatic
pipeline the README describes. It came from 47 manual, supervised calls to
`campagne.py --extraire-cible` with an open-ended prompt, followed by manual
consolidation — the two real automatic reports from the same campaign
(`rapport_20260812T105014Z.md`: 3 sources, zero dates;
`rapport_20260812T203707Z.md`: 16/49 sources, half off-topic) prove the
automatic path alone is weak. Root cause verified in code, not assumed:
`lib/synthese.py::construire_contexte()` truncates by file order, no
relevance ranking — its own docstring has said so since 28/07/2026.

Cross-audited (Ronan, then a second Claude instance in an auditor role) and
independently re-verified by this session — every cited number checked
exactly: chunk count (49 pages, 676,667 chars, 1525 chunks via
`decouper_texte()`), zero callers for `mentionne_fenetre_probable()` and
`fusionner_evenements()` (both written, never wired), 17/47 positive
extractions matching `rapport_final_cible.md`'s stated groupings.

**Fixed now:** `README.md` (+ `docs/fr,de,es/README.md`) gained a "Report
quality: automatic draft vs. supervised research" section stating this
plainly. `docs/GUIDE_LLM.md` deliberately left untouched — it is
version-locked (`notice-version` synced with `lib/preflight_guide.py`'s
`GUIDE_VERSION_ATTENDUE`), so adding the extraction-recipe content there
means bumping both together, which touches a `.py` file — moved to the next
session (code-execution phase) instead of done here under a
documentation-only mandate.

**Full 4-session plan** (regression tests for 3 already-diagnosed bugs,
ground-truth test for `fusionner_evenements()`, real embedding-cost
measurement before deciding on vector RAG, hardened replay validation):
`_CADRE/SPECIFICATIONS/PROCEDURES_LLM/TACHE_fiabilisation_synthese_campagne.md`
— written with a full verified fact table so the next session does not have
to re-derive any of the numbers above.

---

## 2026-08-13 — `sys.exit(43)` wired for `SecretsNonConfigureError`

`SecretsNonConfigureError.CODE_SORTIE = 43` had been declared on the class
since its creation but never read anywhere: the exception fell through to
the generic `except Exception` handler in `shot.py` and exited `1`,
indistinguishable from any other unhandled error (found during the docs
resync of 2026-08-12, see previous entries). Ronan arbitrated in favor of
wiring the code rather than rewriting the (already correct) documentation
that describes it — the class already carried the intent, this was a
missed wire-up, not a design question.

A dedicated branch was added in `shot.py`, mirroring the existing
`SecretsFermesError` (42) branch. Verified in real conditions (disposable
venv, cached Chromium): a `remplir`/`depuis_secrets` scenario run with
`DINOER_CONF` pointing at a nonexistent file now exits `43` with
`code_sortie_recommande: 43` in the JSON result (previously `1`).
Non-regression checked: a plain run with no secrets involved still exits
`0`. Commit `a2e968b`.

Documentation resynced the same session (go-ahead given right after):
`CHEAT_SHEET.md`, `MANUEL.md`, `dinoer.1.md` (EN + FR + DE + ES, 12 files)
had the stale "reserved but not wired, exits 1" caveat removed.
`GUIDE_LLM.md` needed no change — its exit-code table never carried that
caveat, so it was already accurate once the code caught up. Mechanical
check: zero remaining occurrence of the caveat phrasing (and its DE/ES/FR
equivalents) across all 12 files. Commit `8aff8a2`.

---

## 2026-08-12 (night, late) — robots.txt fetch bug, ntfy notifier restored, i18n cache reconciled

Three unrelated fixes triggered by one investigation: why the territorial
campaign (previous entries) never found `deconcarneauapontaven.com`, an
official tourism-office source later surfaced by a Perplexity comparison.

- **`lib/fetch_leger.py::_robots_autorise()`** — root cause found by
  reproducing the real case: SearXNG *did* rank the domain first; the
  domain was dropped later, at the `robots.txt` check. `RobotFileParser.read()`
  delegates its own fetch to `urllib.request` with Python's bare default
  user-agent, distinct from the one actually used for the content request.
  This particular site returns 403 to that bare user-agent, which makes
  `RobotFileParser` fall back to `disallow_all=True` — even though the real
  `robots.txt` (verified with `curl`, both with and without a declared
  user-agent) forbids nothing relevant. Fixed by fetching `robots.txt` with
  `requests` and the same declared user-agent. Verified: `can_fetch()` now
  `True` for the real URL, `recuperer()` now returns `visitee` with 4871
  characters of real content (was `refusee`/`robots_interdit`). Non-regression
  checked against a real `Disallow: /wp-admin/` rule (still `False`) and a
  domain with no reachable `robots.txt` (still `None`/allowed). Commit `50b69b0`.
- **`lib/ntfy.py::notifier()`** — found missing while wiring an operator
  notification channel: `campagne.py`'s end-of-run notification imports
  `notifier` from this module, but the function had been dropped from the
  file during the Diwall→Dinoer reconstruction (09/08) — silent, since no
  campaign had a topic configured yet to actually exercise the path. Restored,
  plus two bugs found testing it against a real `ntfy.ada.local` instance:
  a non-ASCII title (em dash) raised `UnicodeEncodeError` in the `Title`
  HTTP header (`http.client` requires latin-1), and the mitigation first
  tried (percent-encoding the header) avoided the crash but was never
  decoded client-side, verified in a real round trip. Both `notifier()` and
  `publier_attente()` (MFA) now use ntfy's JSON publish endpoint instead of
  HTTP headers, which carries UTF-8 natively. Commit `271387b`.
- **`i18n-empreintes/` reconciled** — turned out to be the *Diwall* segment
  cache, copied wholesale (`grep -rl "Dinoer" i18n-empreintes/` → 0 files;
  `grep -rl "Diwall"` → 18), never Dinoer's own state going stale as
  previously assumed. Set aside as a reversible backup
  (`i18n-empreintes.diwall-backup-2026-08-12/`) rather than merged — no reuse
  value against Dinoer's substantially rewritten English sources, and its
  132-entry `arbitrages.json` outranks everything including `--forcer`,
  a real (if low-probability) cross-product contamination risk. Segment
  alignment verified 1:1 (count and type) across all 15 document×language
  pairs before writing anything; two apparent code-block mismatches checked
  by hand and confirmed to be harmless comment line-wrap differences, not
  structural drift. Rebuilt from the already-existing Lot C translations
  (`docs/{fr,de,es}/*.md`), 1398 entries. Mechanical proof, not just
  intent: `traduire.py --langue {fr,de,es}` replayed end-to-end afterwards
  — 0 translated, 0 rejected, 100% reused, no Ollama call needed. Side
  effect caught by exhaustive diff (not assumed harmless): `recomposer()`'s
  blank-line normalization touched `GUIDE.md`/`MANUEL.md` in all three
  languages (never run through this pipeline before) — verified to be pure
  whitespace, zero content change, before committing (`7d9bd6d`).
  `i18n-outillage/manifeste.json` also needed one line fixed
  (`docs/diwall.1.md` → `docs/dinoer.1.md`, orphaned since the 09/08
  manpage rename postdated the 02/08 rsync copy from Diwall) — outside git
  (factory-floor tooling), no commit.

**Territorial campaign report updated** (`campagnes_dev/.../rapport_final_cible.md`,
outside git per `DINOER_RESEARCH.md` §4.2): 2 pages added from the now-reachable
domain (47 → 49), one wholly new multi-day event (Les Concerts de
Saint-Mathieu), one real gap filled (Festival Consonances' second day,
Pont-Aven, previously missing despite being inside the window), one date
correction cross-checked against the official PDF (Filets Bleus parade
17:30, not 17:00). OpenCode extraction timed out repeatedly on the full
PDF text (53k characters) even on a reduced window — content was
transcribed directly from the already-verified `pdftotext` output instead
of forcing another model call.

---

## 2026-08-12 (night) — Volet C: PDF support, event fusion, temporal pre-filter

Follow-up to the territorial pipeline run (previous entry): operator review
found a real blind spot (PDF sources silently dropped, `pdftotext` never
considered) plus an external analysis (Gemini) proposing two more levers.
Both external levers were checked against the real campaign data before
being spec'd — see `_CADRE/SPECIFICATIONS/PROCEDURES_LLM/TACHE_volet_c_ameliorations_recherche.md`
for the full write-up. Two real design mistakes were caught by testing
against real data before commit, not assumed correct from the spec:

- **`mentionne_fenetre_probable()`** (`lib/extraction.py`) — first version
  required both a year motif and a month motif to be present anywhere in
  the text (never adjacent, to survive the `Le\n12\naoût\n2026` multi-line
  case already known from the territorial run). Testing it against all 43
  real corpus entries found a real false negative anyway:
  `mairie-benodet.fr/agenda-des-evenements/` is a calendar widget that
  never spells out "août" and never writes "2026" anywhere on the page —
  dates are rendered as bare `15/08`, `16/08`, etc. Fixed twice: the year
  requirement now only rejects a page that explicitly names a *different*
  year (bare absence of any year is not rejected), and the month motif
  list must include numeric forms (`/08`, not just `août`/`aout`) since
  spelled-out month names are not universal on real sites. Re-verified:
  0 false negatives on the 43-entry corpus, 20 sources correctly flagged
  for skipping.
- **PDF via `pdftotext`** (`lib/fetch_leger.py`) — optional system
  dependency (`poppler-utils`), detected at runtime (`shutil.which`),
  degrades to `refusee`/`pdf_sans_pdftotext` with a one-time stderr warning
  if absent, never an exception. `subprocess.run(["pdftotext", "-", "-"])`
  reads/writes via stdin/stdout, no temp file. A PDF with no extractable
  text (scanned/image) or below the usual length threshold is `refusee`/
  `pdf_illisible` — deliberately never `insuffisante_legere`: Playwright
  escalation cannot help a missing text layer. Verified against 2 real
  PDFs from the territorial campaign (61k and 49k characters extracted,
  content matches the source documents) and against the graceful-degradation
  path (`shutil.which` monkeypatched to simulate a missing binary).
- **`fusionner_evenements()`** (`lib/extraction.py`, new) — single
  `invoquer_opencode()` call clusters a list of positive `extraire_cible()`
  results that describe the same real event across different pages, always
  preserving every source URL per merged event (never dropping a citation).
  The originally proposed mechanism (hash the raw page text before the
  extraction call) was rejected before implementation: verified against the
  real corpus that the three actual duplicate groups (Locmaria concert
  found on 3 different Saint-Yvi pages, Festival des Filets Bleus on 2 jds.fr
  pages, a Bénodet concert on 2 mairie pages) never share identical raw
  text — a pre-extraction hash would have caught none of them. Verified
  end-to-end: replayed on the 15 real positive extractions, reproduces
  exactly the 11 distinct events found manually, without incorrectly
  merging the two genuinely different Pont-l'Abbé events found on
  different pages of the same site.

Bounded backfill applied to the 12/08 campaign itself (not a new SearXNG
query — same already-collected corpus): 4 of the 5 previously-lost PDF
sources re-fetched through the real (fixed) `lib/fetch_leger.py`, real
text extracted (61415/77603/49304/49225 characters), all 4 genuinely
negative for the 11-20 August window (the Festival de Cornouaille itself
runs 23-26 July; the Quimper Cornouaille PDF is an unrelated 2022
relocation guide) — not a further loss, a confirmed absence. One PDF
(Bénodet council convocation) has no extractable text layer at all
(`pdf_illisible`, likely scanned). Report's "Sources non résolues" section
also fixed to use clickable Markdown links throughout, not just in the
events section — a real inconsistency found while reviewing the operator's
feedback.

**Comment tester / comment lancer :**
```bash
python3 -m py_compile lib/extraction.py lib/fetch_leger.py
python3 -c "
import sys; sys.path.insert(0,'.')
from lib.fetch_leger import recuperer
r = recuperer('https://www.elliant.bzh/wp-content/uploads/2025/04/MAIR054-2025020139-BM-avril-2-2.pdf')
print(r['statut'], len(r['texte'] or ''))"   # -> visitee, ~61000+
```
Full campaign artifacts (updated corpus, report) outside git by design:
`~/git/Dinoer/campagnes_dev/spectacles-sud-finistere-2026-08-11-20/`.

---

## 2026-08-12 (evening) — First real run of the territorial research scenario; anti-ban gap found and fixed in `campagne.py`

First PHASE_EXECUTION + PHASE_VALIDATION run of `PIPELINE_RECHERCHE_TERRITORIALE.md`
(concerts/spectacles within 30 km of Concarneau, 11-20 August 2026 window),
green-lit by the operator. No new primitives — pure orchestration of
`lib/searxng.py`, `lib/fetch_leger.py`, `lib/selection_candidats.py`,
`lib/tables_reference.py`, `campagne.py`, `lib/extraction.py`, all already
delivered (volet B, 09/08/2026).

Real, verified 30 km commune list (haversine on `geo.api.gouv.fr`
coordinates, departments 29+56, not an estimate): 57 communes. 16 discovery
queries (SearXNG + `selectionner_meilleur()`) qualified 13 reference
domains for theme `spectacles_sud_finistere`. `campagne.py` collected 43
pages across those domains; per-source targeted extraction (`extraire_cible()`
called once per collected page, isolated in a single-line corpus each —
the existing contract is single-result, the scenario needs per-source
granularity) found 15 positive hits, deduplicated to 11 distinct events
across 9 communes.

**Real bug found and fixed during this run:** the anti-ban delay in
`campagne.py` (`delai_min_secondes`/`delai_max_secondes`) only applied
between two *retained* page fetches, never between two `lib/searxng.py::rechercher()`
calls themselves. A cible with zero eligible results skipped the delay
entirely, so a short burst of "empty" discovery/collection queries fired
back-to-back — this is exactly what happened here (16 discovery + 13
initial collection queries in a short window) and got Brave/DuckDuckGo/
Startpage/Wikipedia (the engines behind `searxng.ada.local`) to suspend
this instance for rate-limiting. Root-caused, waited out the suspension,
confirmed the fix empirically (an 18 s spacing between distinct SearXNG
calls resolved it on a manual retry), then applied the same `time.sleep()`
call at all three `rechercher()` call sites in `campagne.py` (`"produit"`,
`"table_reference"`, `"query"` cible types). Commit `50047b5`.

**Comment tester / comment lancer :**
```bash
python3 -m py_compile campagne.py && python3 -c "import campagne"
git -C ~/git/Dinoer/Dinoer show 50047b5 --stat
```
Full execution artifacts (corpus, per-source extraction results, final
report) are outside git by design (`DINOER_RESEARCH.md` §4.2 — campaign
artifacts are never versioned): `~/git/Dinoer/campagnes_dev/spectacles-sud-finistere-2026-08-11-20/`.
Detailed method, real query lists and full results in
`_CADRE/MEMOIRE/ADDENDUM_2026_08_12.md`.

---

## 2026-08-12 — Notice-version resync, dead `29_PHASE9`/`watch.py`/`vision.py` references removed

Cleanup pass on debt inherited from the 08-11/08-12 documentation rewrite,
executed in two governance-declared phases (PHASE_DOCUMENTATION then
PHASE_EXECUTION), with mechanical checks after each edit.

`notice-version` in the three LLM notices (`GUIDE_LLM_INTERACTIONS.md`,
`GUIDE_LLM_SESSIONS.md`, `GUIDE_LLM_MONITORING.md`) bumped `1.2` → `1.3`,
matching `GUIDE_LLM.md` since the 08-12 rewrite pass. Verified: `grep -rn
"notice-version" docs/GUIDE_LLM*.md` — all four files aligned.

`scripts/deploy.sh` still listed `watch.py` and `lib/vision.py` in
`CODE_FILES` and the closing `chmod`, plus a stale comment — both files were
removed from the repo when the vision/SoM layer was purged (09/08,
`FONDATION_DINOER.md` §4). The existence guards (`[ ! -f "$src" ]`,
`2>/dev/null || true`) meant the script never actually failed on this —
unlike the `install.sh` smoke test fixed on 08-12 — but the references were
misleading. Removed; `bash -n scripts/deploy.sh` confirms syntax is intact.

Reconnaissance for `dinoer_meta.modeles_utilises` (flagged dead in the
08-12 ADDENDUM) found the field has no legitimate call site left in
`shot.py` at all — the only real model invocations
(`lib/modeles.py::invoquer_opencode`) happen in `campagne.py`'s deep-research
pipeline, which builds no `dinoer_meta` and never calls
`collecter_modele_opencode()`. Resolved as the same 09/08 vision-purge debt,
not a design fork: removed `modeles_appeles`/`tracabilite_modeles_active`
from `shot.py::_construire_dinoer_meta()` and its four threading sites,
`tracabilite_modeles_active`/`tracabilite_inclure_hash` from
`lib/profil_operateur.py::ProfilOperateur` (never read once the guard was
gone), the now-permanently-dead `modeles_utilises` branch in
`lib/journal.py::enregistrer_operation()`, and the stale
`tracabilite_modeles:` block in `dinoer.conf.d/operateur.exemple.yaml`.
`lib/modeles.py`'s three collectors (`collecter_modele_ollama/claude/opencode`)
are kept as unused pure utilities — a future `campagne.py` tracing branch
stays possible, but is a new feature, not this fix. Validated with a real
run (disposable venv, cached Chromium, `--guide-version 1.3`,
`https://example.com`): `succes: true`, `dinoer_meta` produced without
`modeles_utilises`, no regression.

**Comment tester / comment lancer :**
```bash
grep -rn "notice-version" ~/git/Dinoer/Dinoer/docs/GUIDE_LLM*.md
grep -c "watch\.py\|vision\.py" ~/git/Dinoer/Dinoer/scripts/deploy.sh   # → 0
bash -n ~/git/Dinoer/Dinoer/scripts/deploy.sh                          # → syntax OK
grep -rn "modeles_appeles\|tracabilite_modeles" ~/git/Dinoer/Dinoer/*.py ~/git/Dinoer/Dinoer/lib/*.py   # → aucune occurrence
python3 -m py_compile shot.py lib/profil_operateur.py lib/journal.py lib/modeles.py
```

---

## 2026-08-11 — `extraire_texte` primitive implemented, closing the heavy-tier gap

The missing primitive identified in `FONDATION_DINOER.md` §6 and flagged
broken in the 2026-08-10 ADDENDUM: `campagne.py::_escalader_lourd()` sent
`{"type": "extraire_texte"}` to `rpa.py`, but the action existed in none of
`shot.py`'s dispatcher, `rpa.py`, or `scenarios/schema.json` — every heavy-tier
escalation of the deep-research pipeline (`DINOER_RESEARCH.md` §3.3) failed
silently, either on schema validation or on `ValueError("Type d'action
inconnu")`.

Implemented in `shot.py::executer_actions()`: after Playwright has rendered
the page, `page.content()` is parsed with BeautifulSoup, the same noise tags
as the light tier (`lib/fetch_leger.py::_BALISES_BRUIT`) are stripped —
duplicated rather than imported, to keep the heavy tier independent of the
light tier (risk isolation) — and the cleaned text, title, URL and capture
date are returned under a new `extraction_texte` key in the JSON output.
`scenarios/schema.json` gained the corresponding `ExtraireTexte` definition
(no required field beyond `type`); without it, `jsonschema.validate()` would
still reject the action even with the dispatcher fixed. Both action tables
(`GUIDE_LLM.md`, `MANUEL.md`) were updated — an undocumented working
primitive is as much a hazard as a documented broken one (Instruction n°7,
`PROTOCOLE_DEMARRAGE.md`).

Validated end-to-end against `https://example.com` through the actual call
path (`campagne.py::_escalader_lourd()` → subprocess `rpa.py` → subprocess
`shot.py`), in a disposable venv (Chromium reused from the existing
`~/.cache/ms-playwright` cache, no browser re-download) since no
`/opt/dinoer/` venv exists on this machine. Result: `{"statut":
"visitee_lourde", "titre": "Example Domain", "texte": "Example Domain\n...",
"raison": None}` — previously `"refusee"` / `"echec_palier_lourd"`.

**Comment tester / comment lancer :**
```bash
cd ~/git/Dinoer/Dinoer
python3 -m venv /tmp/venv_test_dinoer
/tmp/venv_test_dinoer/bin/pip install playwright beautifulsoup4 jsonschema pyyaml requests
echo '{"url": "https://example.com", "actions": [{"type": "extraire_texte"}]}' > /tmp/scenario_test.json
/tmp/venv_test_dinoer/bin/python3 rpa.py --scenario /tmp/scenario_test.json --guide-version 1.2 --intention "test"
# → JSON de sortie avec la clé "extraction_texte": {"titre", "texte", "url", "date_capture"}
```
Pas de nouveau navigateur à télécharger si `~/.cache/ms-playwright/` contient déjà Chromium.

Committed locally on `Dinoer/Dinoer` (no public push pending, no external
consumer yet — local commits proceed without asking, per the in-between-phase
note in `CLAUDE.md`).

---

## Lot G — git history rewrite (Diwall pre-fork history squashed)

Following the `docs/JOURNAL.md` truncation (Lot F, previous entry), the
repository's actual git history still carried all 228 commits inherited
from Diwall (corrected 15/08/2026, `git log 302bd7f | wc -l`, was documented
as 274), plus 47 Diwall version tags (`v1.0.0`..`v1.23.0`) — the git-level
equivalent of the same problem Lot F fixed at the doc level.

Executed as a dedicated, non-interactive rewrite (no `git rebase -i`,
which needs interactive input): a synthetic provenance commit was built
with `git commit-tree` on the tree of `302bd7f` (last pure-Diwall commit,
228 commits deep), then the 47 Dinoer-specific commits (`5bf13cc` onward,
the actual 09/08/2026 reconstruction and everything since) were replayed
onto it with `git rebase --onto` — a plain linear history, no merges, so
the rebase completed cleanly with zero conflicts. The 47 Diwall tags were
deleted (they pointed exclusively into the now-squashed range and no
longer relate to Dinoer's own history).

**Verified, not assumed:** tree hash of the final commit is bit-identical
to the tree hash of the pre-rewrite `HEAD` (`git diff` between the two
empty) — only the commit history changed, no code/doc content. Full test
suite re-run after the rewrite (8/8 passing), `preflight-publication.sh`
re-run clean (`OK — aucune fuite`).

**Safety net:** a local branch `backup-pre-squash-lot-g-20260814` preserves
the complete original 275-commit history (Diwall + Dinoer) exactly as it
was before this rewrite. Not deleted — kept as the mandated rollback path.

**Known consequence:** commit hashes cited in earlier `_CADRE/MEMOIRE/ADDENDUM_*.md`
entries and in this file's own earlier sections (e.g. `5bf13cc`, `d7eb95e`,
`7916b8b`) no longer sit on `main` — they're only reachable via the backup
branch above (or `git show <hash>` directly, as long as that branch and the
underlying objects aren't garbage-collected). Not a data loss: a deliberate,
declared side effect of the rewrite Ronan approved.

**Out of scope, deliberately untouched:** `origin` still points at
`git@github.com:RonanDavalan/diwall.git` (the original Diwall repo) — no
push was made or attempted. Whether/when Dinoer gets its own dedicated
remote is a separate decision, not part of Lot G.

---

## Earlier history — Diwall fork

Dinoer began as a fork of Diwall v1.21.0 (25/07/2026, base commit `d3ec9e1`),
reconstructed 09/08/2026 from Diwall v1.23.0 (base commit `302bd7f`) — see
`_CADRE/SPECIFICATIONS/FONDATION_DINOER.md`. **Correction (15/08/2026):**
this entry previously paired the 25/07 date with v1.23.0, the version of the
later reconstruction, not the original fork — `git describe --tags`
confirmed against Diwall's own history before this correction, not assumed.
The detailed session-by-session history predating that fork belongs to
Diwall's own project and is not republished here. **Note (Lot G,
14/08/2026):** this pre-fork history was, as of that rewrite, squashed at
the git level too — see the entry above.
