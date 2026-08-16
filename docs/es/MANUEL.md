# Dinoer — Manual operativo

**Versión 1.23.0 — agosto de 2026**

Este documento responde a una sola pregunta: **cómo hacer X con Dinoer**.

> **Si es usuario** — no necesita comandos. Dígale a su modelo qué quiere visitar,
> observar o lograr en un sitio web, una aplicación web o una interfaz de administración.
> El modelo lee este manual y traduce su intención en las acciones correctas.
>
> **Si es un modelo de lenguaje** — estos son sus comandos. Ejecútelos directamente.

Sin descripciones arquitectónicas. Comandos que funcionan.

---

## Índice

1. [Verificar la instalación](#1-verificar-la-instalación)
2. [Leer una página](#2-leer-una-página)
3. [Navegación respetuosa (v1.15.0)](#3-navegación-respetuosa-v1150)
4. [Directorio cifrado y credenciales](#4-directorio-cifrado-y-credenciales)
5. [Escribir y ejecutar un escenario RPA](#5-escribir-y-ejecutar-un-escenario-rpa)
6. [Acciones — referencia completa](#6-acciones--referencia-completa)
7. [Resolver obstáculos comunes](#7-resolver-obstáculos-comunes)
8. [Monitorización — comprobaciones estructurales](#8-monitorización--comprobaciones-estructurales)
9. [Registro de operaciones](#9-registro-de-operaciones)
10. [Opciones de línea de comandos — referencia](#10-opciones-de-línea-de-comandos--referencia)
11. [Códigos de salida y salida JSON](#11-códigos-de-salida-y-salida-json)

---

## 1. Verificar la instalación

```bash
# Comprobación más económica posible — sin Playwright, sin URL, exit 0 inmediato (v1.18.0+)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --version
# → {"outil": "shot.py", "version": "1.23.0"}
```

```bash
# Prueba completa en un solo comando (~3 s)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://example.com --a11y --guide-version 1.3
```

Resultado esperado: JSON en stdout con `"succes": true`.

**`--guide-version` (v1.18.0+):** `shot.py` y `rpa.py` se niegan a ejecutarse
sin ella — a menos que ya exista un marcador local de una llamada anterior
aceptada (`~/.config/dinoer/guide_state.json`). El valor es el
`<!-- notice-version: X.Y -->` de la línea 3 de `docs/GUIDE_LLM.md` — no el
número de versión de Dinoer. Lee el valor actual en vez de confiar en
cualquier valor citado aquí: `grep notice-version /opt/dinoer/docs/GUIDE_LLM.md`.
Consulta la sección «Mandatory pre-flight» de `docs/GUIDE_LLM.md` para el
mecanismo completo y el formato de error si te lo saltas.

**Una vez que el marcador existe, `--guide-version` vuelve a ser opcional**
— todos los demás ejemplos de comandos de este manual la omiten
deliberadamente, ya que un marcador de cualquier llamada anterior exitosa ya
los cubre, siempre que el `notice-version` de `docs/GUIDE_LLM.md` no haya
cambiado desde entonces.

```bash
# Verificar la versión instalada
grep "__version__" /opt/dinoer/shot.py
# → __version__ = "1.23.0"

# Verificar que playwright-stealth está disponible (v1.15.0)
/opt/dinoer/venv/bin/python -c "import playwright_stealth; print('stealth OK')"

# Verificar que el directorio cifrado está montado
ls ~/Vaults/__PROJET__/Dinoer/
# → debe mostrar archivos .json, no una lista vacía
```

Si `ls ~/Vaults/...` devuelve una lista vacía o un error:
→ móntalo: `bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh`

### 1a. Instalar desde el código fuente (el único canal por ahora)

**Aún no se ofrece un paquete `.deb`** — el empaquetado se posterga
deliberadamente hasta que el producto se estabilice. Instala desde un clon git:

```bash
git clone https://github.com/RonanDavalan/dinoer.git ~/git/Dinoer/Dinoer
cd ~/git/Dinoer/Dinoer
bash scripts/install.sh
```

`scripts/install.sh` crea el usuario y grupo de sistema `dinoer`, el venv de
Python, despliega el código en `/opt/dinoer/`, instala Chromium y ejecuta
una prueba de humo (`shot.py --a11y` contra una URL real). Si tiene
intención de modificar el propio código de Dinoer, edite este repositorio y
despliega con `scripts/deploy.sh`.

La configuración vive en `/opt/dinoer/dinoer.conf` (JSON); la clave del
directorio cifrado de secretos es `secrets_dir`. Sobrescritura por proyecto
vía la variable de entorno `DINOER_CONF` o `~/.dinoer.conf`.

Desinstalar:

```bash
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --dry-run   # vista previa, sin cambios
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh             # confirmación interactiva
```

---

## 2. Leer una página

### 2a. Lectura rápida — texto y estructura, sin imagen

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y
```

Devuelve: `a11y_tree` (árbol de accesibilidad — la estructura textual de la
página), `boussole` (URL efectiva, título, estado HTTP). Úselo para leer el
título, verificar la URL o mapear la página antes de interactuar.

### 2b. Texto de página depurado

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ \
  --action '{"type": "extraire_texte"}'
```

Devuelve `extraction_texte` con `titre`, `texte` (etiquetas de ruido
eliminadas: `script`, `style`, `nav`, `header`, `footer`, `aside`,
`noscript`), `url`, `date_capture`. Este es el texto de la página según
Dinoer — nunca una captura de pantalla.

### 2c. Lee primero la boussole

Toda salida contiene un objeto `boussole` — léelo antes que cualquier otra cosa:

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

Si `boussole.url_courante` no coincide con lo que esperas: detente e
investiga antes de cualquier acción mutante.

### 2d. Lee `etat` para una decisión de sí/no (v1.16.0)

Toda ejecución exitosa incluye un objeto `etat` en la raíz del JSON — léelo
antes de cualquier acción mutante, en lugar de verificar manualmente por su
cuenta `auth_status`, `respect.plafond_atteint`, `erreurs_js` y
`erreurs_console`:

```json
"etat": {
  "pret_a_agir": true,
  "niveau_confiance": "eleve",
  "raisons": ["aucun signal de friction détecté"]
}
```

Si `pret_a_agir` es `false`: lee `raisons` para conocer la causa
(autenticación inactiva, deriva de sesión, límite de navegación alcanzado, o
un bloqueo de WAF detectado) antes de continuar.

`etat` no comprueba si la URL o el contenido de la página coinciden con su
expectativa de negocio — usa `evaluer` con `attendu`/`contient`/`motif`
(sección 5d) para eso.

---

## 3. Navegación respetuosa (v1.15.0)

### 3a. Modo sigiloso `--stealth`

Algunos sitios bloquean navegadores headless basándose en
`navigator.webdriver=true` sin examinar la intención. `--stealth` elimina
este marcador técnico automático.

```bash
# shot.py directo
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y --stealth

# Vía rpa.py
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/my-scenario.json --stealth
```

Cuando está activo: `boussole.stealth_actif = true` en la salida JSON.

**Lo que `--stealth` cambia:** se elimina `navigator.webdriver`, se normalizan plugins, idiomas y plataforma.
**Lo que `--stealth` no cambia:** la IP del operador, su identidad o la intención de navegación.

### 3b. Retardos y límites de cortesía

Configurados en `/opt/dinoer/dinoer.conf` (sección `[navigation]`). Los
valores por defecto están activos incluso sin archivo de configuración
(v1.19.0 — D-10):

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

`min_action_delay_ms`: retardo mínimo (ms) entre cada acción. Valor por
defecto de fábrica: 800 ms.

**Desarrollo local — póngalo a `0`:** el valor por defecto de 800 ms protege
a un operador distraído en su *primera ejecución sin configurar* contra el
internet público — no tiene ningún propósito protector frente a su propia
máquina de desarrollo. Fije la clave explícitamente en su `dinoer.conf`
local. Conserve el valor por defecto de 800 ms (o auméntelo) para cualquier
objetivo alcanzado a través del internet público.

Los límites `max_pages_par_run` y `max_actions_par_run` detienen la
ejecución de forma limpia si se superan — el JSON de salida contiene
entonces:

```json
"respect": {
  "pages_visitees": 10,
  "actions_executees": 10,
  "duree_totale_ms": 12400,
  "plafond_atteint": "max_pages_par_run"
}
```

### 3c. Métricas de impacto

Cada ejecución devuelve `respect` (raíz del JSON y dentro de `boussole`):

| Clave | Significado |
|---|---|
| `pages_visitees` | Número de navegaciones `type: naviguer` ejecutadas |
| `actions_executees` | Número total de acciones del escenario ejecutadas |
| `duree_totale_ms` | Duración total de la ejecución |
| `plafond_atteint` | `"max_pages_par_run"` o `"max_actions_par_run"` si hubo parada anticipada |
| `indice_agressivite` | Proporción de acciones mutantes sobre el total — manténla por debajo de 0.3 durante una exploración abierta |
| `waf_bloquants` | Número de navegaciones marcadas como bloqueadas por WAF |

### 3d. Benchmark de sigilo — cuantitativo (v1.17.1)

Prefiere contar señales de huella digital concretas antes que comparar a
simple vista — este es el método usado para verificar la corrección de
compatibilidad de la API `playwright-stealth` en v1.17.0
(`docs/RETOUR_EXPERIENCE.md` FR-79):

```bash
# Sin stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://bot.sannysoft.com --timeout 20000 \
  --actions '[{"type":"evaluer","script":"navigator.webdriver"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.failed\").length"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.passed\").length"}]'

# Con stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://bot.sannysoft.com --stealth --timeout 20000 \
  --actions '[{"type":"evaluer","script":"navigator.webdriver"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.failed\").length"},
               {"type":"evaluer","script":"document.querySelectorAll(\"td.passed\").length"}]'
```

Lee los tres valores en `evaluations[].valeur`: `navigator.webdriver` debe
pasar de `true` a `false`, `td.failed` debe bajar hacia `0`. Medición de
referencia (corrección v1.17.0, sesión 47): 12 fallidos → 0 fallidos.

### 3e. Señal de detección de WAF (v1.16.0, refinada en v1.17.2)

Dinoer marca de forma pasiva un probable bloqueo de WAF — HTTP 403/429, o
una coincidencia de palabra clave en el título/HTML (`Cloudflare`,
`CAPTCHA`, `checking your browser`, etc.). Esto es una señal, nunca una
excepción — la ejecución se completa con normalidad:

```json
"respect": {
  "waf_bloquants": 1
}
```

Cuando está presente y es `> 0`: `etat.niveau_confiance` es `"faible"` y
`etat.pret_a_agir` es `false`. Decida usted mismo si reintentar con
`--stealth`, cambiar de objetivo o detenerse — Dinoer no aborta la
ejecución por usted.

Desde v1.17.2, los nombres de proveedor genéricos (`Cloudflare`, `Akamai`)
solo coinciden con el título de la página — la coincidencia contra el HTML
completo producía anteriormente falsos positivos en referencias a recursos
CDN ordinarias. Si persiste un falso positivo, `--ignorer-waf` degrada
`niveau_confiance` sin forzar `pret_a_agir: false`
(`boussole.waf_ignore_actif: true` registra la anulación). La detección se
basa en palabras clave y puede producir falsos positivos en páginas que
legítimamente hablan de bloqueo/detección — trátala como una señal rápida,
no como un veredicto certero.

---

## 4. Directorio cifrado y credenciales

### 4a. Estructura

Las credenciales viven en un directorio cifrado — un volumen gocryptfs —
que contiene un archivo `.json` por dominio.

```
~/Vaults/__PROJET__/Dinoer/
  ├── app.example.com.json         ← credenciales para https://app.example.com/
  ├── admin.example.com.json       ← credenciales para https://admin.example.com/
  └── operations.jsonl             ← registro de operaciones (v1.15.0)
```

Formato del archivo de credenciales:

```json
{
  "username": "admin@example.com",
  "password": "my-password"
}
```

El nombre del archivo = `urlparse(url).hostname`. Para
`https://app.example.com/login/`, crea `app.example.com.json`.
El directorio se resuelve desde `DINOER_CONF` → `~/.dinoer.conf` →
`/opt/dinoer/dinoer.conf`, clave `secrets_dir`.

### 4b. Rellenar un formulario — la regla absoluta

**PROHIBIDO — expone la contraseña en el shell y en `/proc`:**

```bash
PASS=$(jq -r '.password' ~/Vaults/.../file.json)   # NUNCA
curl -d "password=$PASS" https://...                 # NUNCA
```

**CORRECTO — credenciales resueltas dentro de Playwright:**

```json
{"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"},
{"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"}
```

Los valores nunca pasan por el shell, el historial de bash, los logs de
proceso ni ningún archivo.

### 4c. Elegir el archivo de credenciales para una ejecución

```bash
# Directorio de credenciales por defecto (definido en dinoer.conf > secrets_dir)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url https://target.local/ --a11y

# Archivo de credenciales explícito (--secrets)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y \
  --secrets /path/to/mounted/directory/creds.json

# Directorio de credenciales por proyecto vía .dinoer.conf
export DINOER_CONF=~/git/MyProject/.dinoer.conf
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url https://target.local/ --a11y
```

Contenido de `~/git/MyProject/.dinoer.conf`:

```json
{"secrets_dir": "../MyProject-secrets"}
```

La ruta se resuelve en relación con la ubicación de `.dinoer.conf`.

**Contenido del archivo `--secrets` — `origines_autorisees` obligatoria
desde el 05/08/2026** (cambio disruptivo, sin período de compatibilidad):
un archivo al que le falte esta clave se rechaza antes de cualquier
lectura.

```json
{"username": "operator", "password": "secret", "origines_autorisees": ["target.local"]}
```

`origines_autorisees` enumera los hostnames contra los que se puede usar
este archivo — mismo formato en minúsculas, sin esquema, sin puerto que
`domaine_depuis_url()`. Una lectura contra una página cuyo dominio no está
en la lista se rechaza (`SecretsOrigineNonAutoriseeError`).

### 4d. TOTP / MFA

Dos rutas activas, ambas resueltas dentro de Playwright (nunca un código
tecleado):

```json
{"type": "remplir", "selecteur": "input[name=otp]", "valeur": "depuis_secrets_totp"}
```

Lee la clave `totp_cle` (semilla base32) del archivo de credenciales y
calcula el código TOTP actual.

Para recibir el código vía ntfy (flujo sin intervención humana):

```json
{"type": "attendre_mfa_ntfy", "selecteur": "input[name=otp]", "timeout": 120}
```

`selecteur` es el selector CSS del campo OTP. La URL base de ntfy proviene
de `DINOER_NTFY_URL` (entorno) o la clave `ntfy.url` de `dinoer.conf`.

### 4e. Checksum de integridad (opcional, v1.15.0)

Para proteger un archivo de credenciales contra una corrupción FUSE
silenciosa, añade un campo `checksum`:

```bash
# Generar el checksum
/opt/dinoer/venv/bin/python -c "
import json, hashlib
creds = json.load(open('my_credentials.json'))
fields = {k: creds[k] for k in sorted(['username','password']) if k in creds}
print('sha256:' + hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest())
"
```

Añade el valor devuelto al archivo de credenciales:

```json
{
  "username": "admin@example.com",
  "password": "my-password",
  "checksum": "sha256:a3f2c1..."
}
```

Si el checksum no coincide, `shot.py` lanza `SecretsChecksumError` (código
de salida 42) con un mensaje explícito.
Sin la clave `checksum`: comportamiento sin cambios (opcional estricto).

### 4f. Directorio cifrado cerrado — qué hacer

```
SecretsFermesError: Le répertoire chiffré Dinoer est initialisé mais non monté.
```

```bash
# Montar el directorio cifrado
bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh

# Verificar el montaje
ls ~/Vaults/__PROJET__/Dinoer/
# → debe mostrar archivos JSON
```

### 4g. HTTP Basic Auth — `--http-credentials` (v1.21.0)

Para objetivos detrás de un desafío HTTP Basic Auth a nivel de red (RFC
7617) — el muro que un proxy inverso como Caddy, nginx o Traefik levanta
antes de que se renderice cualquier página, común delante de interfaces de
administración autoalojadas. Este es un mecanismo distinto de la
autenticación basada en formulario descrita arriba (4a-4f), que sigue
totalmente soportada y sin verse afectada.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://internal.example/ \
  --http-credentials --secrets ~/Vaults/__PROJET__/Dinoer/internal_example.json
```

Archivo de credenciales — el par sencillo `username`/`password` ya usado
para el caso común (un único juego de credenciales para el objetivo):

```json
{"username": "admin", "password": "my-password"}
```

Las claves dedicadas `http_username`/`http_password` se intentan primero y
solo son necesarias cuando el mismo objetivo tiene *a la vez* un muro Basic
Auth a nivel de red *y* su propio inicio de sesión de aplicación separado
(dos pares de credenciales distintos en el mismo archivo) — Dinoer recurre
automáticamente a `username`/`password` cuando faltan las claves dedicadas.

Confirmado en producción contra un objetivo real protegido por Caddy: el
valor por defecto seguro (`send: "unauthorized"` — las credenciales se
envían solo después de un 401 genuino, nunca de forma preventiva) resolvió
el desafío al primer intento. `boussole.http_credentials_actif: true`
confirma un éxito real, no solo que se pasó la opción;
`boussole.http_auth_requise: true` marca un 401 sin resolver, distinto de
un bloqueo de WAF.

---

## 5. Escribir y ejecutar un escenario RPA

### 5a. Protocolo en 3 pasos

**Paso 1 — Explorar la página (solo lectura)**

```bash
# Vista rápida — árbol de accesibilidad
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y

# Lectura completa — árbol + texto depurado
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y \
  --action '{"type": "extraire_texte"}'

# Inventario enriquecido del DOM (frameworks, data-attrs estables)
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/diagnostic_dom.json \
  --url https://target.local/
```

**Qué anotar:**
- Atributos estables: `name`, `id`, `aria-label`, `data-testid`
- Overlays bloqueantes (banners de cookies, modales)
- SPA o recarga HTTP completa

**Paso 2 — Escribir el escenario**

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

**Paso 3 — Ejecutar**

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/login_app.json
```

### 5b. Escenario completo: iniciar sesión y navegar entre páginas

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

### 5c. Extraer datos del DOM

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

Resultado en `evaluations[]`:

```json
"evaluations": [
  {"index": 0, "script": "document.title", "valeur": "Dashboard — My App"},
  {"index": 1, "script": "...", "valeur": 42},
  {"index": 2, "script": "...", "valeur": "https://app.example.com/dashboard/"}
]
```

### 5d. Aserciones sobre evaluer (solo rpa.py)

Tres claves mutuamente excluyentes — una por acción:

```json
{"type": "evaluer", "script": "document.querySelectorAll('.row').length", "attendu": 3}
{"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
{"type": "evaluer", "script": "window.location.href", "motif": "/dashboard$"}
```

| Clave | Comparación | Tipos válidos |
|---|---|---|
| `attendu` | igualdad estricta `==` | str, int, bool |
| `contient` | subcadena `in` | solo str |
| `motif` | `re.search()` de Python | solo str |

Si la aserción falla: rpa.py se detiene inmediatamente (exit 1) antes de
cualquier acción mutante posterior.

### 5e. Subescenarios (declencher_scenario)

Define un inicio de sesión como subescenario reutilizable:

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

Llama a este subescenario desde otro escenario:

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

Profundidad máxima: 5 niveles de anidamiento. `declencher_scenario` es
aplanado por `rpa.py` antes de que las acciones lleguen a `shot.py`.

### 5f. Verifique que está en la página correcta antes de cualquier mutación

Añade siempre una guarda como primera acción en escenarios que eliminan o modifican:

```json
{"type": "evaluer", "script": "window.location.href", "contient": "/dashboard"},
{"type": "evaluer", "script": "document.querySelector('.alert-danger')?.textContent ?? null", "attendu": null}
```

Si la guarda falla: rpa.py se detiene antes de que se ejecute la eliminación.

### 5g. Reanudar una sesión (cookies persistidas)

```bash
# Primera invocación — autenticar y guardar la sesión
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/login/ \
  --actions /tmp/login.json \
  --sauver-session /tmp/dinoer/session.json

# Invocaciones posteriores — reutilizar la sesión (sin volver a iniciar sesión)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/dashboard/ \
  --reprendre-session /tmp/dinoer/session.json
```

**Señal de deriva de sesión:** si la sesión ha expirado,
`boussole.session_derive: true` en el JSON. En ese caso: reinicia el inicio
de sesión completo sin `--reprendre-session`.

### 5h. No regresión estructural — `--replay-verifier` (v1.17.0)

```bash
# Primera ejecución — guardar la referencia estructural
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/dashboard.json \
  --sauver-verifier-reference /tmp/dashboard.ref.json

# Ejecuciones posteriores — comparar
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/dashboard.json \
  --replay-verifier /tmp/dashboard.ref.json
```

Compara `http_status`, `dom_stats` y los resultados de `evaluer` contra la
referencia guardada. Veredicto en stderr:

```json
{"type_comparaison": "replay_verifier", "verdict": "stable", "diffs": []}
```

Exit 1 en `verdict: "regression"`, con `diffs` listando cada campo
discordante (`reference` vs `obtenu`). Las dos opciones son mutuamente
excluyentes.

### 5i. Reanudar un escenario largo tras un fallo — `--checkpoint` (v1.17.0)

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/long_audit.json \
  --checkpoint /tmp/long_audit.checkpoint.json
```

Si el escenario falla a mitad de camino, se escribe el archivo de
checkpoint con el recuento de acciones completadas y un archivo de sesión.
**Vuelve a lanzar exactamente el mismo comando** para reanudar: las
acciones ya completadas se omiten. Con éxito total, el archivo de
checkpoint se elimina automáticamente.

Una ejecución detenida por un límite de navegación
(`max_actions_par_run`/`max_pages_par_run`) se trata igual que un fallo
parcial desde v1.17.2 — el checkpoint se actualiza con el progreso real, no
se elimina.

El estado del DOM (modales abiertos, formularios parcialmente rellenados)
nunca se preserva entre reanudaciones — solo se preservan las
cookies/`localStorage` y la posición en la lista de acciones. No confíes en
`--checkpoint` para reanudar a mitad de un único formulario multipaso;
solo reanuda en los límites entre acciones.

### 5j. Apuntar a elementos dentro de un iframe (v1.17.0)

No existe numeración de elementos dentro de un iframe (mismo origen o
origen cruzado) — apunta a él por selector CSS directamente:

```json
{"type": "cliquer_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "button.valider"},
{"type": "remplir_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`remplir_iframe` soporta `valeur: "depuis_secrets"` exactamente igual que
`remplir` (sección 4b) — nunca una credencial en texto plano en el
escenario. Si el elemento objetivo rechaza la interacción (por ejemplo, una
región `contenteditable` en estado de solo lectura), añade `"force": true`
a `cliquer_iframe` — misma semántica que `cliquer` (sección 7e).

Para encontrar el selector interno: usa `evaluer` sobre el contenido del
iframe si es del mismo origen
(`document.querySelector('iframe').contentDocument...`), o consulta el
propio marcado/documentación de la aplicación objetivo si es de origen
cruzado.

### 5k. Iframes anidados — `iframe_chemin` (v1.18.0)

Un iframe dentro de otro iframe: sustituye `iframe_selecteur` por
`iframe_chemin`, un array ordenado — un selector CSS por nivel de anidamiento,
del más externo al más interno.

```json
{"type": "cliquer_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "button.valider"},
{"type": "remplir_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`iframe_selecteur` (un solo frame) e `iframe_chemin` (descenso anidado) son
mutuamente excluyentes — se requiere exactamente uno por acción. Para un
iframe de un solo nivel, sigue usando `iframe_selecteur` (sección 5j).

---

## 6. Acciones — referencia completa

| Tipo | Parámetros obligatorios | Parámetros opcionales | Notas |
|---|---|---|---|
| `naviguer` | `url` | — | Recarga HTTP completa. Se cuenta en `respect.pages_visitees` |
| `cliquer` | `selecteur` | `force` (bool), `repli_js` (bool) | `force: true` evita elementos ocultos por CSS o un showModal. `repli_js: true` reintenta vía JS si el clic nativo sigue fallando (v1.22.0) — rechazado con `--no-evaluer` (exit 2, antes del lanzamiento) |
| `remplir` | `selecteur`, `valeur` | `secret_cle` | `valeur: "depuis_secrets"` requiere `secret_cle`; `"depuis_secrets_totp"` para TOTP |
| `evaluer` | `script` | `attendu`, `contient`, `motif` | JS ejecutado en el navegador. Aserciones solo para rpa.py |
| `defiler` | `px` o `selecteur` | — | Desplazamiento vertical en píxeles (`px`) o desplazamiento hasta un elemento (`selecteur`) |
| `pause` | `ms` | — | Retardo fijo en ms. Prefiere `attendre_selecteur_present` para señales del DOM |
| `attendre` | `selecteur` | — | Espera a que el selector CSS esté presente en el DOM (`state=attached`) |
| `attendre_navigation` | — | — | Espera a `networkidle` (fin de las solicitudes de red) |
| `attendre_url` | `motif` | `attendre_changement` (bool) | Coincidencia de subcadena en la URL. `attendre_changement: true` espera primero una navegación real (consulta la trampa FR-55) |
| `attendre_selecteur_present` | `selecteur` | — | Espera a que el elemento sea visible (`state=visible`) |
| `attendre_absence` | `selecteur` | `delai_initial_ms` | Espera a que el elemento se elimine del DOM (`state=detached`) |
| `attendre_reseau_calme` | — | `timeout_ms` | 500 ms de silencio de red. `timeout_ms`: duración máxima antes de rendirse |
| `attendre_mfa_ntfy` | `selecteur` | `timeout` | Espera un código TOTP vía ntfy y lo rellena en el campo |
| `nettoyer_overlay` | `selecteur` | — | Oculta overlays bloqueantes (banner de cookies, modal) — selector explícito, sin autodetección |
| `declencher_scenario` | `scenario` | — | Inserta en línea las acciones de un subescenario. Profundidad máxima: 5 (rpa.py) |
| `extraire_texte` | — | — | Texto de página depurado a partir del DOM renderizado — `extraction_texte` (`titre`, `texte`, `url`, `date_capture`) |
| `cliquer_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur` | `force` (bool) | Clic dentro de un iframe (v1.17.0). `iframe_chemin` para iframes anidados (v1.18.0, sección 5k) |
| `remplir_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur`, `valeur` | `secret_cle` | Rellenar dentro de un iframe (v1.17.0). `valeur: "depuis_secrets"` soportado |

---

## 7. Resolver obstáculos comunes

### 7a. Banner de cookies / overlay bloqueante

```json
{"type": "nettoyer_overlay", "selecteur": ".cookie-consent-banner, #gdpr-overlay"}
```

Colócala **antes** de cualquier otra acción de lectura/interacción. El
overlay enmascara elementos en el árbol de accesibilidad.

### 7b. Elemento fuera del viewport

Desplázate hasta él (por cantidad o por selector), luego actúa:

```json
{"type": "defiler", "selecteur": "#the-button"},
{"type": "cliquer", "selecteur": "#the-button"}
```

o

```json
{"type": "defiler", "px": 600},
{"type": "cliquer", "selecteur": "button[data-testid='load-more']"}
```

### 7c. SPA (React, Vue, Angular) — navegar sin recarga

Tras un clic que cambia la vista en una SPA, Playwright no sabe cuándo
termina la navegación.

```json
{"type": "cliquer", "selecteur": "a[href*='/dashboard']"},
{"type": "attendre_url", "motif": "/dashboard"},
{"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
```

Nunca asumas que un clic ha completado la navegación sin una señal del DOM.
Tras un envío (submit), combina `attendre_url` con
`attendre_selecteur_present` (trampa de coincidencia parcial, consulta
`docs/GUIDE_LLM_INTERACTIONS.md`).

### 7d. Diálogo CSS o showModal()

`TimeoutError` en `cliquer` cuando el elemento es visible en el DOM =
elemento oculto por CSS o dentro de un diálogo.

```json
{"type": "cliquer", "selecteur": "#dialog-confirm button[type=submit]", "force": true}
```

Si `force: true` es insuficiente (error de interactuabilidad/obstrucción):
añade `repli_js: true` a la misma acción (v1.22.0), o recurre a JS:

```json
{"type": "evaluer", "script": "document.querySelector('#dialog-confirm button[type=submit]').click()"}
```

### 7e. Operación larga (spinner, trabajo por lotes)

No uses `pause` para esperar una duración fija. Espera la señal del DOM:

```json
{"type": "cliquer", "selecteur": "button[data-testid='run-job']"},
{"type": "attendre_absence", "selecteur": ".spinner", "delai_initial_ms": 500},
{"type": "attendre_selecteur_present", "selecteur": ".result-container"}
```

Si la operación no ofrece ninguna señal del DOM, sondea el estado con
`evaluer` y continúa cuando la evidencia esté presente.

### 7f. Límite alcanzado (v1.15.0)

Si `respect.plafond_atteint` está presente en la salida, la ejecución se
detuvo antes de que el escenario terminara. Las acciones restantes no se
ejecutaron.

Opciones:
1. Aumentar `max_pages_par_run` o `max_actions_par_run` en `dinoer.conf`
2. Dividir el escenario en varias ejecuciones
3. Reanudar una sección parcial con `--checkpoint`

### 7g. Campo de formulario `<select>`

`remplir` (`.fill()`) no funciona en `<select>`. Usa un setter JS vía
`evaluer`:

```json
{"type": "evaluer", "script": "(() => { const s = document.querySelector('select[name=role]'); s.value='admin'; s.dispatchEvent(new Event('change',{bubbles:true})); })()"}
```

### 7h. Sitio bloqueado por WAF (403 inmediato)

```bash
# Prueba con stealth
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y --stealth
```

Si el 403 persiste con `--stealth`: el sitio usa fingerprinting TLS
(JA3/JA4) o análisis de comportamiento avanzado (Cloudflare Enterprise).
`playwright-stealth` no evade estas protecciones. Consulta
`docs/RETOUR_EXPERIENCE.md` FR-77/FR-78/FR-79 para el contexto.

Dinoer también marca de forma pasiva un bloqueo probable — consulta la
sección 3e (`respect.waf_bloquants`).

### 7i. La navegación inicial nunca se completa — `--wait-until` (v1.22.0)

Síntoma: `TimeoutError` en la navegación inicial, y aumentar `--timeout` no
cambia nada (45 s falla exactamente igual que 10 s). Causa: por defecto
Dinoer espera `networkidle` — 500 ms de silencio de red. Una página que
sondea continuamente (estadísticas en vivo, contadores que se autoactualizan,
paneles de administración de router) nunca produce ese silencio, así que
ningún valor de timeout puede ser nunca suficientemente grande.

```bash
# shot.py — reconocimiento directo
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url http://target.local/ --wait-until load --a11y

# rpa.py — propagado a shot.py, así que los escenarios llegan a los mismos objetivos
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario ./admin_login.json --wait-until load
```

Un escenario puede llevarla como propiedad raíz en su lugar, manteniéndose autocontenido:

```json
{"url": "http://target.local/", "wait_until": "load", "actions": [...]}
```

La opción de línea de comandos tiene prioridad sobre la propiedad del escenario.

| Valor | Espera a | Úselo cuando |
|---|---|---|
| `networkidle` | 500 ms de silencio de red | por defecto — manténgalo salvo que falle |
| `load` | evento `load` (página y subrecursos) | sondeo continuo / estadísticas en vivo |
| `domcontentloaded` | HTML parseado, subrecursos aún pendientes | página muy pesada, el DOM es todo lo que necesita |

Se aplica solo a la navegación inicial — la acción `naviguer` no se ve
afectada. `boussole.wait_until` informa el valor solo cuando difiere del
valor por defecto.

---

## 8. Monitorización — comprobaciones estructurales

No existe monitorización basada en imagen en Dinoer (sin diff visual). Las
comprobaciones estructurales son basadas en texto y aptas para CI.

### 8a. Monitorización estructural continua — `scripts/monitor-verifier.sh` (v1.18.0)

Monitoriza la *estructura* (`http_status`, `dom_stats`, `evaluations`) —
cero imagen, cero llamada a LLM, construido sobre `--replay-verifier`
(sección 5h).

```bash
# Primera ejecución — crear la referencia estructural
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/sillage_login.json \
  --sauver-verifier-reference /opt/dinoer/references/sillage_login.ref.json

# Un pase de comprobación y alerta — no es un daemon, ejecútelo repetidamente vía cron.
# scripts/*.sh nunca se despliega en /opt/dinoer/, así que se ejecuta desde el
# origen git, como su propio usuario.
bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/sillage_login.json \
  --reference /tmp/ref_sillage.json \
  --ntfy-topic dinoer-monitoring
```

```bash
# crontab -e (su propio crontab)
*/15 * * * * bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/sillage_login.json \
  --reference /opt/dinoer/references/sillage_login.ref.json \
  --ntfy-topic dinoer-monitoring \
  >> /var/log/dinoer/cron-structural.jsonl 2>&1
```

Estable → silencio. Regresión → una notificación `ntfy` con el diff. Cada
invocación es un proceso aislado — sin daemon, sin riesgo de fuga de
memoria, y los límites de Navegación Respetuosa se reinician limpiamente en
cada pase.

**Deuda conocida (v1.23.0):** el script llama a `rpa.py --no-capture
--replay-verifier`, pero `--no-capture` ya no es una opción de `rpa.py`. Es
semánticamente redundante (Dinoer no tiene ruta de imagen), pero
actualmente hace que el script falle en argparse. No confíes en él tal
cual hasta que se corrija.

**Matiz del bloqueo de lectura de la guía:** si se invoca bajo un usuario
del SO distinto (por ejemplo, una cuenta de servicio del sistema), ese
usuario necesita validar `--guide-version` una vez
(`~<home>/.config/dinoer/guide_state.json`).

---

## 9. Registro de operaciones

El registro es `/var/log/dinoer/operations.jsonl`. Si la ruta de registro
configurada está dentro del directorio cifrado y este no está montado, las
entradas se redirigen a una alternativa local (escritura degradada,
700/600) en lugar de escribirse en texto claro en el host sin cifrar.

```bash
# Leer las últimas 10 entradas
tail -n 10 /var/log/dinoer/operations.jsonl | python3 -m json.tool

# Filtrar por objetivo (herramienta journal.py)
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com

# Filtrar solo operaciones mutantes
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --mutatif

# Desde una fecha
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --depuis 2026-07-01

# Solo ejecuciones fallidas (v1.20.0) — resultado != éxito
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --cible app.example.com --erreurs
```

Campos de cada entrada:

| Campo | Significado |
|---|---|
| `ts` | Marca de tiempo ISO 8601 |
| `version` | Versión de Dinoer |
| `mode` | `shot.py` o `rpa.py` |
| `cible_url` | URL objetivo |
| `scenario` | Ruta del archivo de escenario (modo RPA) |
| `source_scenario` | Solo nombre del archivo de escenario, sin ruta (v1.18.0) |
| `resultat` | `"succes"` o `"echec"` |
| `mutatif` | `true` si hubo al menos una acción de escritura |
| `respect` | El registro de navegación de la ejecución |
| `evaluations` | Valores `{script, valeur_retournee}` saneados |
| `duree_ms` | Duración en ms |
| `intention` | Etiqueta pasada vía `--intention` o el campo `intention` del escenario |

### 9a. Rotación de logs (G-36)

Dinoer no incluye una configuración de logrotate —
`/var/log/dinoer/operations.jsonl` crece sin límite hasta que el
administrador instala una. `lib/journal.py` abre y cierra el archivo en
cada escritura (sin descriptor de archivo persistente entre ejecuciones),
específicamente para que el comportamiento **por defecto** de logrotate
(renombrar el archivo actual, crear uno nuevo) funcione correctamente sin
ninguna opción especial: la siguiente escritura reabre la ruta y encuentra
el nuevo inodo.

**No añadas `copytruncate`** a una configuración de logrotate de Dinoer —
es innecesario aquí y reintroduce una ventana de pérdida de escritura.
Ejemplo `/etc/logrotate.d/dinoer`:

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

`journal.py` (el lector) ya sigue los archivos rotados de forma
transparente (`operations.jsonl`, `.1`, `.2.gz`, …) — no hace falta ningún
paso adicional tras la rotación.

---

## 10. Opciones de línea de comandos — referencia

### shot.py

| Opción | Por defecto | Descripción |
|---|---|---|
| `--version` | — | Imprime la versión instalada y termina inmediatamente — sin Playwright, sin ningún otro argumento necesario (v1.18.0) |
| `--guide-version X.Y` | — | Prueba de haber leído `docs/GUIDE_LLM.md` — obligatoria salvo que ya exista un marcador local válido (v1.18.0, sección 1) |
| `--url URL` | obligatorio | URL a capturar |
| `--actions FILE` | — | Archivo JSON de acciones secuenciales |
| `--action JSON` | — | Acción única como JSON en línea — cuida el escapado, prefiere `--actions FILE` para acciones con mucho JS |
| `--attendre-selecteur SEL` | — | Espera a un selector antes de terminar la ejecución |
| `--timeout MS` | 10000 | Timeout de Playwright por acción (ms) |
| `--wait-until VALUE` | `networkidle` | `networkidle`\|`load`\|`domcontentloaded` — solo navegación inicial (v1.22.0, sección 7i) |
| `--largeur PX` | 1280 | Ancho del viewport |
| `--hauteur PX` | 720 | Alto del viewport |
| `--a11y` | desactivado | Incluye el árbol de accesibilidad en el JSON |
| `--stealth` | desactivado | Modo sigiloso playwright-stealth (v1.15.0) |
| `--secrets FILE` | — | Ruta explícita a un archivo de credenciales |
| `--auth-indicator SEL` | — | Selector CSS presente solo en sesión autenticada |
| `--auth-indicator-negative SEL` | — | Requiere `--auth-indicator`; selector CSS presente solo fuera de sesión autenticada |
| `--ignorer-waf` | desactivado | Un bloqueo de WAF detectado degrada `niveau_confiance` pero ya no fuerza `pret_a_agir: false` por sí solo (v1.17.2, sección 3e) |
| `--http-credentials` | desactivado | Resuelve credenciales HTTP Basic Auth desde el archivo de credenciales, delimitadas al origen del objetivo (v1.21.0, sección 4g) |
| `--ignore-tls-errors` | desactivado | Acepta TLS inválido en objetivos LAN/dev controlados — nunca en internet público (v1.15.1) |
| `--no-evaluer` | desactivado | Rechaza la acción **evaluer** (y `repli_js`) para toda la ejecución — recomendado contra formularios sensibles (v1.15.1) |
| `--no-filtre-evaluer` | desactivado | Desactiva la neutralización en stdout de los valores devueltos por **evaluer**, las URLs y los mensajes de error — solo para ejecuciones de depuración explícitas; cuando está desactivado, se fija `boussole.filtre_evaluer_actif: false` (v1.23.0) |
| `--intention TEXT` | — | Etiqueta de negocio registrada en el log |
| `--sauver-session FILE` | — | Guarda las cookies tras las acciones |
| `--reprendre-session FILE` | — | Reanuda una sesión guardada |
| `--source-scenario NAME` | — | Interno (plomería de rpa.py para el log — no para llamadas directas) |
| `--chainage JSON` | — | Interno (plomería de rpa.py para el log — no para llamadas directas) |

### rpa.py

Propaga todas las opciones relevantes de shot.py, más:

| Opción | Descripción |
|---|---|
| `--version` | Imprime la versión instalada y termina inmediatamente (v1.18.0) |
| `--guide-version X.Y` | Prueba de haber leído `docs/GUIDE_LLM.md` — verificada de forma independiente, misma regla que shot.py (v1.18.0) |
| `--scenario FILE` | Ruta al escenario JSON o YAML (obligatorio) |
| `--url URL` | Sobrescribe la URL del escenario sin modificar el archivo |
| `--stealth` | Propagada a shot.py |
| `--wait-until` | Propagada a shot.py (v1.22.0, sección 7i) |
| `--ignorer-waf` | Propagada a shot.py (v1.17.2, sección 3e) |
| `--http-credentials` | Propagada a shot.py; también se puede fijar como propiedad raíz del escenario `"http_credentials": true` (v1.21.0, sección 4g) |
| `--auth-indicator-negative` | Requiere un `auth_indicator` (CLI o propiedad raíz del escenario) |
| `--sauver-verifier-reference FILE` | Guarda la referencia estructural para `--replay-verifier` (v1.17.0, sección 5h) |
| `--replay-verifier FILE` | Compara la ejecución contra una referencia estructural, exit 1 en caso de regresión (v1.17.0, sección 5h) |
| `--checkpoint FILE` | Reanuda un escenario largo tras un fallo a mitad de ejecución (v1.17.0, sección 5i) |

### campagne.py (pipeline de investigación)

| Opción | Descripción |
|---|---|
| `--manifeste FILE` | Manifiesto de campaña (JSON) — requiere `id_campagne` + `cibles` |
| `--id-campagne ID` | Identificador de campaña (usado en el manifiesto y la extracción) |
| `--extraire-cible DEMANDE` | Extracción dirigida sobre un corpus ya recopilado, sin síntesis |
| `--desactiver-cache` | Omite la caché de búsqueda |
| `--purger-cache` | Purga toda la caché de búsqueda |
| `--purger-cache-avant-jours N` | Purga las entradas de caché anteriores a N días |

Tipos de objetivo en el manifiesto: `query`, `url`, `produit`,
`table_reference`.
Artefactos: el `/var/log/dinoer/operations.jsonl` compartido + un
`collecte.jsonl` por campaña. Detalle completo: `campagne.py --help`.

---

## 11. Códigos de salida y salida JSON

### Códigos de salida

| Código | Causa | Qué hacer |
|---|---|---|
| 0 | Éxito | — |
| 1 | Error de Playwright, acción fallida, aserción de rpa.py, `action_secret_en_clair` | Lee `erreur` en el JSON. Consulta `GUIDE_LLM_INTERACTIONS.md` |
| 1 | `guide_non_lu` — `--guide-version` ausente/incorrecta, sin marcador válido (v1.18.0) | Se dispara antes de que Playwright se inicie. Lee `docs/GUIDE_LLM.md`, vuelve a lanzar con `--guide-version X.Y` (sección 1) |
| 2 | Argumentos incompatibles, `arguments_incompatibles`, `url_scheme_interdit`, `chemin_sensible_refuse` | Lee `message` — nombra el conflicto |
| 3 | Módulo `playwright` no encontrado | Invoca vía `/opt/dinoer/venv/bin/python` |
| 42 | `SecretsFermesError` — directorio cifrado no montado, o checksum inválido | Móntalo, o verifica el archivo de credenciales |
| 43 | `SecretsNonConfigureError` — sin `secrets_dir` configurado | Configura `secrets_dir` en `dinoer.conf` (`undo` de un ejemplo faltante: crea `/opt/dinoer/dinoer.conf`) |

### Estructura de la salida JSON

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
    "version_shot": "1.23.0",
    "horodatage_iso": "2026-08-12T14:23:11+02:00",
    "hostname_executant": "operator-host",
    "utilisateur_executant": "operator",
    "profil_actif": "operateur.exemple.yaml",
    "url_au_moment_capture": "https://target.local/dashboard"
  }
}
```

`operation_id` (v1.16.0) siempre está presente e identifica de forma única
esta ejecución — nombra el directorio de aislamiento bajo
`/tmp/dinoer/<operation_id>/` y coincide con el campo `operation_id` de la
entrada de esta ejecución en el registro de operaciones (sección 9). `etat`
(v1.16.0) está presente solo en la ruta de éxito. `latences_actions`
(v1.20.0) siempre está presente (lista vacía si no hubo acciones), una
entrada por cada acción que realmente se despachó — consulta
`GUIDE_LLM_MONITORING.md` para saber cómo complementa
`respect.duree_totale_ms`.

Claves condicionales (ausentes cuando están inactivas): `dom_stats`,
`a11y_tree`, `evaluations`, `extraction_texte`, `auth_status`,
`stealth_actif`, `session_derive`, `respect.plafond_atteint`,
`respect.waf_bloquants`, `respect.indice_agressivite` (presente siempre que
se haya ejecutado al menos una acción), `boussole.repli_js_utilise`,
`boussole.wait_until`, `boussole.http_credentials_actif`,
`boussole.http_auth_requise`, `boussole.tls_errors_ignored`,
`boussole.waf_ignore_actif`, `boussole.filtre_evaluer_actif`,
`boussole.champs_rediges`, `actions_executees_avant_echec`,
`pages_visitees_avant_echec` (solo en el JSON de fallo, v1.17.0). Consulta
`GUIDE_LLM_MONITORING.md` para la tabla exhaustiva de activación.

### Error — formato

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

## Rutas de referencia

| Ruta | Rol |
|---|---|
| `/opt/dinoer/` | Instalación de producción |
| `/opt/dinoer/venv/bin/python` | Python a usar en cada invocación |
| `/opt/dinoer/dinoer.conf` | Configuración de la máquina (secrets_dir, navigation, ntfy) |
| `/opt/dinoer/scenarios/` | Escenarios RPA (incluyendo `diagnostic_dom.json`) |
| `/opt/dinoer/docs/` | Documentación |
| `/opt/dinoer/references/` | Referencias de `--sauver-verifier-reference` / replay |
| `/tmp/dinoer/<operation_id>/` | Datos de sesión temporales de una ejecución, aislados por `operation_id` (v1.16.0, se limpia al reiniciar) |
| `~/Vaults/__PROJET__/Dinoer/` | Credenciales + log (volumen gocryptfs) |
| `~/git/Dinoer/Dinoer/` | Código fuente git (edita aquí, luego `deploy.sh`) |
| `/var/log/dinoer/operations.jsonl` | Registro de operaciones persistente (`journal.py`) |

Desplegar tras modificar el código fuente:

```bash
bash ~/git/Dinoer/Dinoer/scripts/deploy.sh
```
