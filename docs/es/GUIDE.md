# Dinoer — guía del operador

Versión 1.11 — agosto de 2026 (v1.23.0) — superficie realineada con la
reconstrucción de Dinoer: sin captura de pantalla, sin Set-of-Mark, sin
`watch.py`; el agente lee el árbol de accesibilidad y controla las acciones
de Playwright mediante selectores CSS.

*También disponible en francés, alemán e inglés bajo `docs/fr/`, `docs/de/`
y el `docs/` raíz.*

---

## Por qué Dinoer — qué delegas realmente

### El problema que resuelve Dinoer

Cuando trabajas con un LLM en una aplicación web, se produce una asimetría de
percepción: el modelo lee código, ejecuta comandos, observa salida textual —
pero no ve la interfaz que ven tus usuarios. Tú sí.

Esta asimetría crea una forma específica de ansiedad: no sabes si lo que el
modelo describe coincide con lo que verías en un navegador. Para estar
seguro, debes creerle bajo palabra o verificarlo tú mismo.

Dinoer resuelve este problema dándole al modelo la misma vista estructurada
que obtendrías en un navegador: el árbol de accesibilidad, leído a través de
un Chromium headless real, más los valores del DOM que extrae con `evaluer`.
Ya no le crees al modelo bajo palabra — observas el mismo estado que él.

```
 Navegador (Chromium headless)
        │  Playwright lo controla — clic, relleno, navegación
        ▼
 shot.py / rpa.py
        │  lee el estado del DOM resultante a través de vistas paralelas
        ├──▶ a11y_tree            árbol de accesibilidad, texto
        ├──▶ evaluations          valores extraídos vía `evaluer`
        └──▶ session file         solo cookies (--sauver-session)
        │
        ▼
 boussole + JSON en stdout — el estado, tal como el operador puede auditarlo
        │
        ▼
 Tú (el modelo): lees → analizas → decides → actúas → repites
```

### Qué delegas

Dinoer te permite delegar **verificaciones repetitivas y propensas al
control**:

- Comprobar que 20 páginas de un sitio responden correctamente tras un despliegue
- Confirmar que un formulario de inicio de sesión funciona en la interfaz correcta
- Asegurar que un despliegue no rompió la estructura de una vista crítica
- Controlar un panel de administración a través de la misma interfaz que usaría un humano

Sin Dinoer, estas verificaciones son responsabilidad tuya. Con Dinoer, el
modelo las realiza e informa del resultado — con la evidencia JSON que lo
respalda.

### Qué conservas

Conservas la **validación de sentido de alto nivel**: decidir si el resultado
que presenta el modelo es aceptable, coherente con tus expectativas y acorde
con lo que tus usuarios deberían ver. Esa decisión sigue siendo tuya.

### Navegación respetuosa (v1.15.0)

Dinoer no disfraza su identidad para evadir la detección de bots.
`--stealth` elimina marcadores técnicos automáticos (`navigator.webdriver`)
que bloquean navegadores headless independientemente de la intención — no
cambia la IP del operador, su identidad, ni el hecho de que la ejecución
esté declarada. A cambio, cada ejecución informa de su propia huella
(`respect`: páginas visitadas, acciones ejecutadas, duración) y respeta
retardos de cortesía configurables y límites estrictos (`dinoer.conf
[navigation]`). El derecho a navegar y el deber de hacerlo de forma medible
se tratan como inseparables — consulta `docs/RETOUR_EXPERIENCE.md`
FR-77/FR-78/FR-79 para el contexto de campo que dio forma a esto.

**Objetivos locales — el retardo de cortesía no es una doctrina, es un valor
por defecto (v1.19.0):** el `min_action_delay_ms: 800` de fábrica protege
una primera ejecución sin configurar contra el internet público — carece de
sentido contra tu propia máquina de desarrollo/producción. Ponlo a `0` en tu
`dinoer.conf` local para depuración local; consulta `docs/MANUEL.md` sección
3b.

### Cuándo Dinoer es la herramienta adecuada

| Caso de uso | ¿Dinoer es adecuado? |
|---|---|
| Validación estructural tras un despliegue | ✓ Sí |
| Diagnosticar una interacción rota | ✓ Sí |
| Navegación e introducción de formularios (~30 s máx.) | ✓ Sí |
| Delegar comprobaciones repetitivas | ✓ Sí |
| Operación de servidor larga (clonado ~2–5 min) | ✗ No — tiempo de espera de Playwright |
| Eliminación o mutación masiva | ✗ No — mejor una llamada directa a la API |
| Flujo de trabajo que requiere deshacer (rollback) | ✗ No — Dinoer no puede deshacer |

Para los casos desaconsejados, consulta `docs/GUIDE_LLM.md` sección «When NOT
to use Dinoer» (fricciones FR-59 y FR-60 documentadas).

---

**Este documento está escrito para la persona que opera Dinoer.**

Complementa `GUIDE_LLM.md` (dirigido a los modelos) con ejemplos concretos,
procedimientos paso a paso y recordatorios sobre los tropiezos más
comunes.

---

## Casos de uso de demostración

Los siguientes casos ilustran cómo puede verse en la práctica una sesión de
agente más Dinoer. Están pensados para que los evalúes en tu propio
contexto, no como una recomendación de adoptar alguno en concreto. Solo el
Caso 1 se distribuye como escenario ejecutable; los demás son narrativos a
propósito, y cada uno explica por qué bajo su propio encabezado.

### Caso 1 — resolución de problemas CSS/JS locales

Incluido como escenario real y ejecutable:
`scenarios/exemples/depannage_local.json`. Diagnostica un desplazamiento de
maquetación o una interacción bloqueada en una interfaz servida localmente —
una sonda rápida que lee `erreurs_js`/`erreurs_console` y el árbol de
accesibilidad, y luego valida la corrección con `rpa.py --replay-verifier`
contra una referencia capturada antes de la regresión. Ejecútalo directamente:

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/exemples/depannage_local.json \
  --guide-version 1.3
```

### Caso 2 — comparar componentes de hardware entre tiendas

Un agente al que se le pide comparar el precio y el stock de un componente
en varias tiendas en línea podría combinar Dinoer con una herramienta
separada de descubrimiento de URLs (una instancia de búsqueda local, por
ejemplo) para encontrar páginas de tiendas candidatas, y luego usar Dinoer
en modo de solo lectura con acciones `evaluer` para extraer
precio/stock/especificaciones de cada página, y finalmente comparar los
resultados él mismo.

**No se distribuye como escenario incluido, deliberadamente:** nombrar una
tienda concreta en un escenario público y versionado es una decisión que te
corresponde a ti, no un valor por defecto que este proyecto deba imponer en
tu nombre. También conlleva un riesgo real de fragilidad — un escenario
público dirigido a un sitio comercial nombrado puede fallar meses después
cuando la postura anti-bot de ese sitio cambie (el 39 % de los sitios
comerciales muestreados en `docs/RETOUR_EXPERIENCE.md` FR-77 devolvieron un
bloqueo inmediato), lo que desacredita el ejemplo más de lo que ayuda. Si
construyes tú mismo esta composición, ten en cuenta que cualquier
herramienta de descubrimiento de URLs con la que combines Dinoer (una
instancia de búsqueda local u otra) no es un componente de Dinoer — es una
pieza separada que el agente compone encima.

### Caso 3 — explorar y resumir documentación técnica (aplicaciones de una sola página)

Un agente encargado de producir una guía de integración para un sitio de
documentación construido como aplicación de una sola página (SPA) podría
usar `rpa.py` con `attendre_reseau_calme` para dejar que el enrutamiento del
lado del cliente se asiente, extraer el árbol de accesibilidad para mapear
la estructura de la página, luego recorrer bloques de código de forma
recursiva con `evaluer` para extraer su contenido exacto, y finalmente
sintetizar el material recopilado en una guía.

**No se distribuye como escenario incluido, por la misma razón que el Caso
2** — nombrar un sitio de documentación concreto (o, peor, un proveedor de
pagos concreto cuya documentación resulta ser el ejemplo de trabajo) es un
compromiso comercial y reputacional que este proyecto no debería asumir por
defecto, y el mismo riesgo de fragilidad ante WAF se aplica a un escenario
público fijado a un objetivo real.

### Caso 4 — configurar un panel de observabilidad o analítica autoalojado

Un operador que configura un panel de monitorización o analítica web
autoalojado detrás de un proxy inverso puede usar Dinoer para controlar la
propia interfaz — crear un panel, conectar una fuente de datos, establecer
una regla de alerta — de la misma forma en que se configura cualquier otro
panel de administración, en lugar de editar archivos a mano para pasos que
la interfaz está pensada para manejar. Esto incluye objetivos situados
detrás de un desafío HTTP Basic Auth a nivel de red (`--http-credentials`,
v1.21.0) — confirmado contra una interfaz de administración real protegida
por Caddy, no solo un fixture sintético: las credenciales almacenadas
respondieron al desafío en el primer intento.

**No se distribuye como escenario incluido** — la disposición del panel y
los nombres de las fuentes de datos son específicos de la infraestructura de
cada operador, e inventar un equivalente sintético duplicaría lo que ya
cubre el fixture local del Caso 1 para la regresión estructural, no para
este tipo de trabajo de configuración guiada y multipaso.

### Caso 5 — administrar una plataforma de venta de entradas de principio a fin

Dinoer usado a lo largo de varias sesiones para configurar y operar una
instalación real y autoalojada de venta de entradas — configuración de
eventos, categorías de entradas, un dominio personalizado y las herramientas
de escaneo/registro del día del evento — a través de la misma interfaz web
que usaría un administrador humano. Se encontró y resolvió fricción real por
el camino (manejo de sesión, peculiaridades de los desplegables, un aviso de
permiso que bloqueaba un paso desatendido) — no es una historia de éxito sin
fricción, lo cual es parte de lo que la hace un ejemplo útil: los obstáculos
eran obstáculos ordinarios de automatización web, no algo específico de
Dinoer.

**No se distribuye como escenario incluido** — una configuración de venta de
entradas toca facturación y particularidades del recinto propias del
operador, el mismo razonamiento que el Caso 2.

### Caso 6 — seguimiento de una agenda de eventos regional

Un uso sencillo de sondeo semántico: pedirle a un agente que revise una
agenda de eventos local en busca de próximos acontecimientos, sin saber de
antemano en qué página está la respuesta. El modo de solo lectura de Dinoer
combinado con el árbol de accesibilidad permite al agente escanear e
informar en un puñado de solicitudes — sin necesidad de modelo de visión
para este tipo de tarea guiada por texto. Una sesión también produjo un
ejemplo limpio y real del comportamiento de falso positivo documentado de
la señal de WAF: una página cargó con normalidad (contenido rico, sin
captcha, sin interstitial) mientras `respect.waf_bloquants` seguía
activándose, debido a un recurso de terceros no relacionado en la página que
coincidía con una palabra clave de detección — resuelto en cerca de un
minuto leyendo el árbol de accesibilidad ya presente en la misma respuesta,
exactamente como anticipa la regla de la guía «señal, nunca un candado».

**No se distribuye como escenario incluido** — un sitio de eventos regional
concreto no es un objetivo público estable y reproducible, y nombrar uno
públicamente es decisión del operador, no un valor por defecto del proyecto.

### Caso 7 — probar el acceso real a sitios de comercio electrónico bajo navegación respetuosa

Una observación recurrente y honesta de sesiones reales: usado con respeto
(retardos limitados por tasa, límites de página/acción, `--stealth` activo,
sin intento de forzar el acceso más allá de un bloqueo real), Dinoer
ejecutado contra una variedad de sitios de comercio electrónico revela que
una gran proporción de las plataformas principales devuelve un bloqueo
directo — HTTP 403, o una solicitud que nunca se completa — sin importar
cuán cortés sea el tráfico. Esto no es una carencia de Dinoer que haya que
corregir: la postura anti-bot es la propia elección del sitio, y Dinoer no
intenta vencerla (consulta «Navegación respetuosa» más arriba). En la
práctica: para tareas de comparación de compras contra grandes plataformas
comerciales, espera una proporción significativa de callejones sin salida, y
trata una señal de bloqueo (`respect.waf_bloquants`) como información para
rodear, no como un error que reintentar.

Una distinción a tener presente: una pantalla de verificación invisible que
nunca se resuelve y no presenta nada sobre lo que actuar (sin casilla, sin
desafío de imagen) es distinta de un CAPTCHA interactivo. Este último es
legítimo responderlo con honestidad — un agente que opera para un humano
identificado, desde la propia IP de ese humano, no es el «robot» al que
apunta la pregunta. El primero simplemente no ofrece ninguna puerta que abrir
desde el lado del agente, y forzarlo (rotación de IP, suplantación de huella
TLS) queda fuera de lo que hace Dinoer.

**No se distribuye como escenario incluido, y deliberadamente sin nombrar las
plataformas implicadas** — consulta el razonamiento sobre fragilidad ante WAF
del Caso 2: una tabla fechada de bloqueo/no bloqueo ligada a sitios
comerciales nombrados queda obsoleta y socava su propio argumento más rápido
de lo que lo ilustra. `docs/RETOUR_EXPERIENCE.md` FR-77 documenta el mismo
patrón a escala de panel (tasa de bloqueo inmediato del 39 %).

---

## Requisitos previos antes de empezar

```bash
# 1. Verificar que Dinoer responde
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://example.com --a11y
# → debe devolver {"succes": true, ...}

# 2. Verificar que el directorio cifrado está montado (si usas gocryptfs)
ls ~/Vaults/Dinoer/
# → debe mostrar archivos .json, no contenido cifrado

# 3. Verificar las credenciales de un dominio
/opt/dinoer/venv/bin/python -c "
import sys; sys.path.insert(0, '/opt/dinoer')
from lib.repertoire_chiffre import lire_credential
print('OK' if lire_credential('target.local', 'password') else 'EMPTY')
"
```

---

## Configuración de credenciales por proyecto

Cada proyecto puede tener su propio directorio de credenciales. Dos métodos:

**Método 1 — variable de entorno directa (puntual):**

```bash
DINOER_SECRETS_DIR=~/Vaults/MyProject \
  /opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url …
```

**Método 2 — archivo `.dinoer.conf` de proyecto (recomendado para proyectos recurrentes):**

```bash
# Crear el archivo en la raíz del proyecto
echo '{"secrets_dir": "../MyProject-secrets"}' > ~/git/MyProject/.dinoer.conf

# Luego, o bien prefija cada invocación, o exporta al inicio de la sesión de shell
export DINOER_CONF=~/git/MyProject/.dinoer.conf
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url …
```

El `secrets_dir` en `.dinoer.conf` puede ser una ruta relativa — se resuelve
en relación con la ubicación del archivo `.dinoer.conf`.

---

## Capturar una página y analizarla

```bash
# Leer el estado de la página (solo lectura)
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --a11y
# → devuelve url_courante, titre_page, a11y_tree en el JSON
```

**Lo que obtienes:**
- `boussole.url_courante` + `boussole.titre_page`: URL y título efectivos tras la navegación
- `a11y_tree`: estructura de la página en texto (encabezados, campos, botones)
- `etat.pret_a_agir` + `etat.raisons`: fricciones percibidas, para que el modelo las rodee

---

## Automatizar un formulario de inicio de sesión

**Paso 1** — Prepara el archivo de credenciales.

El archivo de credenciales se llama `<hostname>.json`, donde `hostname` =
resultado de `urlparse(url).hostname`. Para `https://app.example.com/`, el
archivo es `app.example.com.json`.

```json
{"username": "admin@example.com", "password": "my-secret"}
```

**Paso 2** — Explora la página de inicio de sesión.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://app.example.com/login/ --a11y
```

Lee `a11y_tree` para identificar los selectores de los campos.

**Paso 3** — Escribe el escenario.

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

**Paso 4** — Ejecuta.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /tmp/login.json
```

---

## Validar varias páginas en una sola invocación

Para comprobar N páginas de un sitio autenticado sin repetir el inicio de
sesión cada vez:

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

## Extraer un valor de la página

Para leer una cadena de texto, un contador o cualquier valor del DOM:

```bash
cat > /tmp/extract.json << 'EOF'
[{"type": "evaluer", "script": "document.title"}]
EOF
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ --actions /tmp/extract.json
# → resultado en evaluations[0].valeur
```

Para texto documental depurado (formularios y etiquetas de ruido
eliminados), usa `extraire_texte` en su lugar — la salida es una estructura
`titre`/`texte`/`url`/`date_capture` que un agente de resumen puede consumir
directamente.

**Importante**: escribe siempre los scripts JS en un archivo `--actions`,
nunca en línea con `--action` (el shell corrompe las comillas anidadas).

---

## Configurar monitorización estructural continua (v1.18.0)

Dinoer no tiene pipeline visual — la monitorización es *estructural*:
comprueba el código de estado de la página, los recuentos de elementos del
DOM y los resultados de evaluación JS. Esto es más barato que la comparación
de imágenes y detecta una clase distinta de regresión (por ejemplo, un campo
de formulario desaparecido con la maquetación sin cambios).

```bash
# 1. Guardar una referencia estructural, una vez
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --sauver-verifier-reference /opt/dinoer/references/my-scenario.ref.json

# 2. Un pase de comprobación y alerta
bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --reference /opt/dinoer/references/my-scenario.ref.json \
  --ntfy-topic dinoer-monitoring
```

Silencioso cuando es estable, un push `ntfy` cuando se detecta una
regresión. Prográmalo tú mismo con cron — el script hace un solo pase y
termina, no ejecuta un bucle. `scripts/*.sh` nunca se despliega en
`/opt/dinoer/`, así que la entrada de cron se ejecuta desde el origen git,
como tu propio usuario (no la cuenta de servicio `dinoer`, que no puede
acceder a `~/git/Dinoer/Dinoer/`):

```bash
# crontab -e (tu propio crontab)
*/15 * * * * bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --reference /opt/dinoer/references/my-scenario.ref.json \
  --ntfy-topic dinoer-monitoring \
  >> /var/log/dinoer/cron-structural.jsonl 2>&1
```

---

## Problemas comunes

| Situación | Qué hacer |
|---|---|
| `FileNotFoundError` en el archivo de credenciales | Comprueba que el archivo JSON se llama con el FQDN completo (`urlparse(url).hostname`) |
| `SecretsFermesError` (código de salida 42) | Monta el directorio cifrado: `bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh` |
| JSON inválido en la salida | Usa `2>/dev/null \| tail -1` para extraer solo la línea JSON |
| Inicio de sesión seguido de una redirección de Django al panel | No uses `naviguer` en una sesión Django reanudada — pasa la URL vía `--url` |
| Campo de formulario `<select>` no se rellena | Usa `remplir` con `selecteur`, luego `cliquer` en la opción, o contrólalo vía `evaluer` |
| El clic no tiene efecto en un botón fuera del viewport | Añade `{"type":"defiler","selecteur":"#the-button"}` antes del clic |
| `auth_status: "active"` incluso en la página de inicio de sesión | El selector positivo es ambiguo (encabezado persistente) — añade `--auth-indicator-negative .btn-login` |
| Los Web Components bloquean un selector normal | Usa `cliquer_iframe`/`remplir_iframe` con un selector explícito, o accede dentro del shadow root vía `evaluer` |
| `respect.waf_bloquants` aparece en una página que en realidad no está bloqueada | La detección se basa en palabras clave (v1.16.0, refinada en v1.17.2) — trátala como una señal, no un veredicto. Si persiste en una página que has confirmado que no está bloqueada, añade `--ignorer-waf` |
| `cliquer` hace clic en el elemento equivocado en una página que mutó | Prefiere selectores estables en orden, o vuelve a leer el árbol con una llamada `--a11y` nueva antes de hacer clic |
| Un escenario RPA largo falla a mitad de camino y no quieres repetir los pasos ya completados | Añade `--checkpoint FILE` (v1.17.0) — vuelve a lanzar el mismo comando para reanudar; el estado del DOM no se preserva, solo la sesión y la posición de la acción |
| Los elementos interactivos dentro de un iframe son invisibles para el árbol | Usa `cliquer_iframe`/`remplir_iframe` (v1.17.0) con un selector CSS explícito, o `iframe_chemin` (v1.18.0) para un iframe anidado dentro de otro |
| Tu modelo informa `"erreur": "guide_non_lu"` / código de salida 1 en su primera llamada a Dinoer | Esperado la primera vez que un modelo usa Dinoer en esta máquina con este usuario del SO (v1.18.0) — debe leer `docs/GUIDE_LLM.md` y pasar `--guide-version` una vez. Esto es deliberado, no un fallo — indícale al modelo que lea la guía en lugar de sortear el error |

---

## Desinstalar Dinoer

El script `~/git/Dinoer/Dinoer/scripts/uninstall.sh` elimina la instalación
de forma limpia, en el orden inverso a `install.sh`.

```bash
# Ver qué se eliminará, sin hacer nada
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --dry-run

# Desinstalación completa (confirmación interactiva)
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh

# Sin confirmación (pruebas en frío, reinstalación encadenada)
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --confirme && bash ~/git/Dinoer/Dinoer/scripts/install.sh
```

**Qué se elimina:**

| Elemento | Detalle |
|---|---|
| `/opt/dinoer/` | Código, venv de Python, configuración |
| `/var/log/dinoer/` | Registros de operaciones |
| Usuario de sistema `dinoer` | Creado exclusivamente para Dinoer |
| Grupo de sistema `dinoer` | Ídem |
| Pertenencia al grupo | Tu cuenta se elimina del grupo `dinoer` |
| Hook de git pre-push | `core.hooksPath` desactivado en el repositorio de origen |

**Qué nunca se toca:**
- `~/Vaults/` — tus credenciales
- `~/git/Dinoer/` — el origen git
- Caché del navegador de Playwright (`~/.cache/ms-playwright/`)

**Evidencia estructurada (`/var/log/dinoer/preuves/`):** si el directorio
contiene capturas, se conserva por defecto con una advertencia. Para
eliminarlo:

```bash
bash ~/git/Dinoer/Dinoer/scripts/uninstall.sh --confirme --purge-preuves
```

---

## Consultar el historial de operaciones

```bash
# Todas las operaciones sobre un objetivo
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local

# Solo operaciones mutantes (clics, entrada de formularios)
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local --mutatif

# Desde una fecha
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible target.local \
  --depuis 2026-06-01
```
