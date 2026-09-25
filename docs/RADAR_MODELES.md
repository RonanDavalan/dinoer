# Model radar — Field feedback on Dinoer

Reference document
Location: `docs/RADAR_MODELES.md`

Raw observation log on LLM behaviour when using Dinoer.
**No editorial filter.** False positives included. Goal: pure signal,
not promotion. Each entry is actionable to improve the framework.

Doctrine: a model that drifts is not a bad model — it is a signal
about what the framework or its documentation did not lock down sufficiently.

---

## Entry format

```
### [Date] — [Model] — [Dinoer version] — [Task]
**What worked:** ...
**What drifted:** ...
**Signal retained:** ...
```

---

## How to contribute an entry

An entry is useful if:
- It describes a real session (not an invented test)
- It includes a false positive or a drift, not just what worked
- It names the actionable signal (friction to document, rule to lock, missing primitive)

Honesty is the primary value of this document.
