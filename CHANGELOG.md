# Changelog

Generated from `debian/changelog` at build time — do not edit by hand.
Edit `debian/changelog` and rebuild instead
(`bash ~/git/Dinoer/scripts/construire-paquet.sh`).

## 1.0.1 — 25 Sep 2026 21:08:00 +0200

- searxng_url is now read from the file DINOER_CONF designates, and the dinoer-campaign wrapper exports DINOER_CONF=/etc/dinoer/dinoer.conf like dinoer-shot and dinoer-rpa: on this channel the key written in /etc/dinoer/dinoer.conf was ignored and campaigns stopped on "no SearXNG URL configured".
- OpenCode: no default model any more (the model list changes, a hard-coded default disappears); without DINOER_OPENCODE_MODEL the error says to pick one from `opencode models`. A failed call reports OpenCode's own error and whether the model is missing from the list.
- OpenCode calls deny websearch/webfetch whatever the launch directory (OPENCODE_CONFIG_CONTENT, merged with the user's own value), so the report only cites the collected pages. stdin is closed on the call.
- The campaign completion notification no longer carries the local report path.
- docs/RADAR_MODELES.md: three entries inherited from the fork removed.
- postinst (and scripts/install.sh) now also check the headless Chromium shell: an interrupted download could leave the full browser without it and pass for a complete installation, leaving shot.py unable to start.
- README, GUIDE and MANUAL in French, German and Spanish brought back in line with the English source (badges, campaign options table, example paths, Spanish formal register); the translation checks pass in the three languages.

## 1.0.0 — 15 Aug 2026 00:22:11 +0200

- Initial dinoer .deb packaging, adapted from the diwall channel this package is forked from (Dinoer split off Diwall on 2026-07-25, diwall's own .deb history predates the fork and lives in Diwall's own changelog, not repeated here).
- Renamed throughout: package/source name, /opt/dinoer install path, dinoer system user/group, /etc/dinoer config directory, /var/log/dinoer journal + evidence directory, the six /usr/bin/dinoer-* wrapper commands and their man pages (corrected 15/08/2026, was documented as five — contradicted by this same changelog's own next entry, which counts dinoer-campaign as the sixth).
- Dropped dinoer-watch (watch.py and the whole SoM/vision perception layer it depended on do not exist in Dinoer — removed from the product on 2026-08-09, FONDATION_DINOER.md §4). No replacement wrapper: Dinoer's structural monitoring lives in dinoer-monitor-verifier instead, already present.
- Added campagne.py + the new dinoer-campaign wrapper (research pipeline entry point, absent from Diwall) to debian/dinoer.install. Verified against the wrapper's own source, not assumed by analogy: campagne.py never reads DINOER_CONF (it resolves its own paths via dedicated env vars — DINOER_CAMPAGNES_DIR, DINOER_SEARXNG_URL, DINOER_TABLES_REFERENCE, DINOER_JOURNAL), so dinoer-campaign does not export it, unlike dinoer-shot/dinoer-rpa.
- debian/dinoer.install's lib/*.py list rebuilt from the lib/ actually on disk today, not copied from the old diwall.install: dropped lib/vision.py (removed with SoM), added the seven modules of the deep-research pipeline (cache_recherche.py, extraction.py, fetch_leger.py, searxng.py, selection_candidats.py, synthese.py, tables_reference.py) that diwall.install never listed even before the fork, plus scenarios/*.json and docs/images/*.png resynced against what's actually referenced (dead SoM screenshot examples dropped, nothing in docs/ links to them any more).

