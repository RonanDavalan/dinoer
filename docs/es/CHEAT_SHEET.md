# Dinoer — hoja de referencia rápida

Versión 1.23.0 — agosto de 2026

Todo en una página. Referencia completa: `docs/MANUEL.md`.

---

## Tres comandos

```bash
# Ver una página: árbol de accesibilidad
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url URL --a11y

# Ejecutar un escenario
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py --scenario FILE.json

# Leer una referencia de escenario y comparar (monitorización estructural)
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario FILE.json --replay-verifier REF.json
```

La primera llamada en una máquina necesita `--guide-version X.Y`, léelo con
`grep notice-version /opt/dinoer/docs/GUIDE_LLM.md`.

---

## El bucle

```
        tú decides qué hacer a continuación
                  │
                  ▼
   ┌──────────────────────────────┐
   │  shot.py / rpa.py            │   un proceso, un JSON en stdout
   │    ├─ Chromium (headless)    │
   │    ├─ A11y: estructura de la página │
   │    └─ secrets: rellena credenciales│   nunca en el shell, nunca en un log
   └──────────────┬───────────────┘
                  │  boussole + JSON
                  ▼
        tú lees el mismo estado
        que el operador también puede ver
```

El estado de sesión vive en un archivo, no en el proceso: una segunda
llamada con `--reprendre-session` reutiliza las cookies — nunca el estado
del DOM.

---

## Lee la salida en este orden

| Lee | Te dice |
|---|---|
| `succes` | si la ejecución se completó |
| `boussole.url_courante` | dónde acabaste realmente |
| `boussole.dernier_code_http` | último estado de navegación |
| `etat.pret_a_agir` + `etat.raisons` | fricciones percibidas — un informe, nunca una barrera |
| `a11y_tree` | estructura de la página — encabezados, campos, botones |
| `respect` | tu propia huella: páginas, acciones, duración |

Si `boussole` no coincide con lo que esperas, detente antes de cualquier
acción mutante.

---

## Cada acción

`type` siempre es obligatorio. Las claves de abajo son las adicionales.

| Acción | Obligatorio | Opcional |
|---|---|---|
| `naviguer` | `url` | — |
| `cliquer` | `selecteur` | `force`, `repli_js` |
| `cliquer_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur` | `force` |
| `remplir` | `selecteur`, `valeur` | `secret_cle` |
| `remplir_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur`, `valeur` | `secret_cle` |
| `evaluer` | `script` | `attendu` \| `contient` \| `motif` |
| `extraire_texte` | — | — |
| `defiler` | `px` \| `selecteur` | — |
| `pause` | `ms` | — |
| `attendre` | `selecteur` | — |
| `attendre_selecteur_present` | `selecteur` | — |
| `attendre_absence` | `selecteur` | `delai_initial_ms` |
| `attendre_navigation` | — | — |
| `attendre_url` | `motif` | `attendre_changement` |
| `attendre_reseau_calme` | — | `timeout_ms` |
| `attendre_mfa_ntfy` | `selecteur` | `timeout` |
| `nettoyer_overlay` | `selecteur` | — |
| `declencher_scenario` | `scenario` | — |

---

## Credenciales — la única forma correcta

```json
{"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"}
```

Nunca extraigas un secreto al shell. `lib/repertoire_chiffre.py` lo resuelve
dentro del proceso Playwright; el valor nunca llega a tu línea de comandos,
tu historial, ni ningún log.

---

## Cuando algo se resiste

| Síntoma | Prueba |
|---|---|
| El clic agota el tiempo, elemento visualmente oculto | `"force": true`, luego `"repli_js": true` |
| Elemento debajo del pliegue (fold) | `defiler` primero |
| La página nunca termina de cargar | `--wait-until load` |
| El envío no hace nada, sin error | validación HTML nativa — envía el formulario vía `evaluer` |
| `exit 42` | directorio cifrado no montado (`bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh`), o checksum de credenciales inválido (revisa el archivo de credenciales) — ambos son `SecretsFermesError` |
| `guide_non_lu` | pasa `--guide-version` una vez |
| 403 / 429 | lee `respect.waf_bloquants` — una señal, no una excepción |

---

## Códigos de salida

`0` éxito · `1` fallo de ejecución o aserción fallida · `2` argumentos inválidos (rechazados antes de iniciar cualquier navegador) · `3` intérprete incorrecto — usa el venv (`/opt/dinoer/venv/bin/python`) · `42` directorio cifrado de credenciales cerrado, o checksum de credenciales inválido (familia `SecretsFermesError`) · `43` ningún `secrets_dir` configurado (`SecretsNonConfigureError`).
