# Dinoer — Access observations

Version 1.0 — July 2026

A neutral, dated log of real access outcomes encountered while using Dinoer
against public sites. Purpose: give future runs (and future models) factual
grounding instead of repeated guessing about which targets are reachable.

**What this file is not:** a verdict on any site's legitimacy, a WAF-vendor
classifier, or a call to action. An entry records what was observed, on what
date, with what Dinoer configuration — nothing about the target's intent or
worth. See `docs/GUIDE_LLM.md` section "WAF and Cloudflare blocking" for the
doctrine behind this neutrality (perceive the friction, do not moralize
about it).

No entry yet.

---

## Adding an entry

When a real run produces a genuine access observation (not a synthetic
re-test), append a dated section above the "Adding an entry" heading:

- Date, target (public name, no internal codenames), Dinoer version and
  flags used (`--stealth`, `--wait-until`, etc.)
- Outcome: accessible / blocked (403, timeout, other) — cite the actual
  `http_status` or symptom from the JSON output
- No qualification of the target beyond the observed outcome
