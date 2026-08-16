# Dinoer — Investigación web soberana y local-first para agentes LLM

> **Para el operador humano:** Dinoer se ejecuta en tu propia máquina, delega
> la búsqueda y la recopilación a primitivas que puedes leer línea por línea,
> y te entrega un informe Markdown con fuentes y fecha — no una respuesta de
> caja negra.
>
> **Para el LLM:** [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) es tu referencia
> operativa. Empieza por ahí.

---

## ¿Qué es Dinoer?

Dinoer es un **motor de búsqueda y síntesis pasivo, local-first y soberano**.
Es una bifurcación (fork) de [Diwall](https://github.com/RonanDavalan/diwall)
(automatización visual de navegador para LLMs), despojada de toda su capa de
percepción — **cero capturas de pantalla, cero Set-of-Mark, cero modelo de
visión.** Dinoer nunca mira una página; la lee: DOM, árbol de accesibilidad y
texto de página depurado.

Donde Diwall responde a «interactuar con una interfaz autenticada, de forma
visual», Dinoer responde a una pregunta distinta: «explorar un gran número de
fuentes públicas y compilar una señal verificable y con fuentes a partir de
ellas» — en un hardware tan modesto como una Raspberry Pi 5.

```
Consulta → descubrimiento vía SearXNG → recopilación HTTP ligera
      → escalado a un navegador real solo para las páginas que lo necesitan
      → síntesis por un LLM delegado → informe Markdown fechado y con fuentes
```

**Doctrina:** el código Python no lleva ninguna inteligencia de negocio. Cada
módulo hace una sola cosa mecánica — consultar SearXNG, extraer texto limpio
de una página, leer una credencial cifrada, enviar una notificación. La
*estrategia* de una búsqueda (cómo hacer seguimiento, cuándo escalar, cuándo
detenerse) vive en un escenario, nunca codificada de forma rígida en un
módulo. Consulta [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) para la doctrina
completa.

---

## Posicionamiento: en qué compite Dinoer y en qué no.

Dinoer no compite con los asistentes de búsqueda de uso general (Perplexity y similares) en cuanto a la amplitud, el volumen o el precio de las búsquedas. Una prueba real (14 de agosto de 2026, investigación de reputación sobre un tema real) midió esto directamente en lugar de asumirlo: de las 28 páginas recopiladas por el propio sistema de descubrimiento impulsado por SearXNG de Dinoer, tres fuentes que una consulta simple y no preparada de Perplexity mostró inmediatamente (un perfil de LinkedIn, una página de proyecto, un crédito de foto de archivo) estaban completamente ausentes; esto se rastreó hasta consultas de SearXNG dirigidas al tipo incorrecto de búsqueda (directorios de empresas, en lugar de los términos que habrían mostrado esas páginas), y no a un defecto de clasificación o truncamiento posterior. Un motor de búsqueda generalista con motores autenticados y respaldados por cookies tiene un alcance estructural que una instancia local de SearXNG sin autenticación no posee.

Lo que la misma prueba verificó, en el mismo conjunto de datos, midió más que lo que se asumió: **una síntesis trazable y reproducible de un conjunto de datos específico.** Cada afirmación en un informe de Dinoer es atribuible a una página realmente recopilada en disco (`collecte.jsonl`/`operations.jsonl`) — sin ninguna dependencia de lo que haya hecho un motor de búsqueda externo al producir la respuesta. Una verificación directa del flujo completo de eventos del modelo delegado durante la síntesis (no solo su texto final) confirmó que no se realizaron llamadas externas `websearch`/`webfetch` al conjunto de datos durante la generación del informe. Esa es la verdadera propuesta de valor: saber precisamente de dónde proviene una respuesta, y no simplemente obtener resultados como lo haría una herramienta generalista.

---

## Arquitectura

```
campagne.py (orchestration)
  ├─ lib/searxng.py         → SearXNG JSON API (HTTP only, no browser)
  ├─ lib/fetch_leger.py     → requests + BeautifulSoup, robots.txt-aware
  ├─ rpa.py / shot.py       → Playwright, only for pages the light tier
  │                           marked "insufficient" (JS-only shells)
  ├─ lib/selection_candidats.py → best-match pick among several fetched
  │                           candidates, "produit" targets only
  ├─ lib/extraction.py      → targeted fact extraction, trouve/valeur/url
  ├─ lib/tables_reference.py→ persistent, sourced table of reference sites
  ├─ lib/cache_recherche.py → ChromaDB-backed search cache
  └─ lib/synthese.py + lib/modeles.py → delegated LLM (OpenCode/Ollama),
                                        writes the final report
```

`shot.py`/`rpa.py` conservan el núcleo de ejecución ReAct de Diwall
(`naviguer`, `remplir`, `cliquer`, `evaluer`, persistencia de sesión,
resolución de credenciales) — nada de su capa de percepción.

---

## Capacidades

| Función | Descripción |
|---|---|
| **Descubrimiento vía SearXNG** | Consulta HTTP pura contra una instancia SearXNG local o remota — sin coste de navegador para la búsqueda |
| **Recopilación de nivel ligero** | Extracción con `requests` + BeautifulSoup, respeta `robots.txt`, consciente de WAF |
| **Escalado de nivel pesado** | Playwright, usado solo para páginas que el nivel ligero no pudo leer (shells renderizados en JS) |
| **Extracción semántica de texto** | Acción `extraire_texte` — texto principal depurado, no una captura de pantalla |
| **Instantánea de accesibilidad** | `--a11y` — estructura semántica de la página (árbol A11y), nunca se produce una imagen |
| **Extracción dirigida** | `lib/extraction.py` — contrato estricto `trouve`/`valeur`/`url`, declara la ausencia en vez de inventar una respuesta |
| **Tablas de sitios de referencia** | `lib/tables_reference.py` — tabla persistente y con fuentes de sitios conocidos por tema |
| **Caché de búsqueda vectorial** | `lib/cache_recherche.py` — respaldada por ChromaDB, evita reconsultar solicitudes casi duplicadas |
| **Deduplicación y frescura** | Deduplicación a nivel de campaña por URL exacta, límite por hostname, ventana de frescura de 30 días antes de recrawlear |
| **Rastreo respetuoso** | Retardo aleatorio entre objetivos, rechazo estricto ante señales de WAF/robots.txt — nunca se evade |
| **Resolución de credenciales** | Inyección segura de credenciales — nunca en texto plano, nunca en la línea de comandos |
| **Directorio cifrado** | Volumen gocryptfs — `SecretsFermesError` (código de salida 42) si no está montado |
| **Registro de operaciones** | Registro persistente de solo anexión de todas las ejecuciones — quién hizo qué, dónde, cuándo |
| **Escenarios RPA** | Ejecuta secuencias de acciones desde archivos JSON, para la ruta de escalado de nivel pesado |
| **Iframes de origen cruzado** | `cliquer_iframe` / `remplir_iframe` apuntan a elementos dentro de iframes |
| **TOTP / MFA asíncrono** | Los objetivos protegidos por credenciales siguen siendo alcanzables cuando una ejecución de nivel pesado necesita autenticarse |

---

## Calidad del informe: borrador automático frente a investigación supervisada.

El informe de finalización del proceso propio de `campagne.py`
(`lib/synthese.py::construire_contexte()` construye y trunca el corpus,
`rediger_rapport()` redacta después el texto)
es un **borrador**, no el producto final pulido: concatena
el corpus recopilado en orden de archivo, truncado a 4000 caracteres/página y 60.000
en total, sin clasificación por relevancia. En un corpus grande y ruidoso, esto permite de forma fiable que páginas genéricas o fuera de tema aparezcan antes de las fuentes reales, y puede eliminar silenciosamente los elementos más relevantes después del punto de truncamiento.

En una tarea de investigación real (un listado de eventos locales, ver "Posicionamiento" arriba para una tarea donde el resultado fue diferente), la calidad del informe superó notablemente a una herramienta de búsqueda de propósito general (Perplexity); sin embargo, ese informe **no** fue generado por una única ejecución de `campagne.py`.  Proviene de un operador que itera sobre `campagne.py --extraire-cible` — docenas de llamadas individuales y abiertas para extraer información del mismo corpus recopilado, donde cada llamada permitía al modelo delegado juzgar por sí mismo si estaba leyendo un hecho aislado o un evento de varios días; seguido de una consolidación manual de los resultados. Consulte [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) para el patrón exacto de extracción.

Si necesita un resumen rápido y no crítico, el informe automático es adecuado como punto de partida. Si necesita un informe en el que pueda confiar sin supervisión, utilice el patrón de extracción específico y cíclico en su lugar.

---

## Requisitos

| Componente | Versión / Notas |
|---|---|
| **SO** | Debian 13 Trixie (Linux) |
| **Python** | 3.11+ en un venv aislado (PEP 668 — pip del sistema bloqueado en Debian 13) |
| **Playwright** | 1.62+ (instalado en el venv) — usado solo por la ruta de escalado de nivel pesado |
| **Chromium** | Sin interfaz gráfica (headless), instalado vía `playwright install chromium` |
| **SearXNG** | Una instancia accesible (local o remota), API JSON por HTTP |
| **Ollama** | Modelo de embeddings local, apto para CPU (`nomic-embed-text`) para la caché de búsqueda — sin modelo de visión, sin GPU necesaria |
| **OpenCode** | Backend de razonamiento delegado para la síntesis de informes (modelos de nivel gratuito por defecto) |

No se necesita GPU. El objetivo de referencia es una Raspberry Pi 5 con 8 GB de RAM.

---

## Instalación

Dos canales, mutuamente excluyentes en una misma máquina.

**`.deb` package** — el camino habitual si desea usar Dinoer tal cual:

```bash
sudo apt install ./dinoer_1.0.0-1_all.deb
```

Instala el usuario y grupo del sistema `dinoer`, un entorno virtual de Python aislado, Chromium, los seis comandos `dinoer-*` y sus páginas de manual en cuatro idiomas. Los paquetes, el código fuente y las sumas de comprobación se publican en [dinoer.davalan.fr](https://dinoer.davalan.fr) -- consulta la página de [Descargas](https://dinoer.davalan.fr/en/guides/downloads/) para obtener más detalles, incluyendo qué significa ese aviso de "sandbox" `apt`.

**Clonar el repositorio Git** — si tiene la intención de modificar el código:

```bash
git clone https://github.com/RonanDavalan/dinoer.git
cd dinoer
bash scripts/install.sh
```

Esto crea el usuario y grupo de sistema `dinoer`, el entorno virtual,
despliega el código en `/opt/dinoer/` y ejecuta una prueba de humo
(`shot.py --a11y` contra una URL real).

La configuración se encuentra en `/etc/dinoer/dinoer.conf` (canal [`.deb`]) o
`/opt/dinoer/dinoer.conf` (canal git-clone); una muestra se instala junto a
ella como `dinoer-sample.conf`— JSON sin formato, no con comentarios (corregido el 15/08/2026:
JSON no tiene sintaxis de comentario, el archivo nunca lo tuvo). Excepción: `campagne.py`
nunca lee `DINOER_CONF` ni la ruta git-clone mencionada anteriormente; lee
`/opt/dinoer/dinoer.conf` codificado y resuelve sus propias rutas a través de variables de entorno dedicadas (`DINOER_CAMPAGNES_DIR`, `DINOER_SEARXNG_URL`,
`DINOER_TABLES_REFERENCE`, `DINOER_JOURNAL`).

### Desinstalación

```bash
bash scripts/uninstall.sh --dry-run   # vista previa, sin cambios
bash scripts/uninstall.sh             # confirmación interactiva
```

Elimina: `/opt/dinoer/`, `/var/log/dinoer/`, el usuario de sistema `dinoer`,
el grupo de sistema `dinoer`. **Nunca se toca:** `~/Vaults/` (tus
credenciales), el propio repositorio.

---

## Uso (por tu LLM)

### Extracción semántica, sin imagen

```bash
/opt/dinoer/venv/bin/python3 /opt/dinoer/shot.py \
  --url https://example.com --a11y --action '{"type":"extraire_texte"}'
```

### Una campaña de investigación

```bash
python3 /opt/dinoer/campagne.py --manifeste manifeste.json
```

Referencia LLM completa: [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md)

---

## Credenciales

Las credenciales se almacenan en archivos JSON, uno por dominio, **nunca en
el código ni en archivos de escenario**:

```
~/Vaults/Dinoer/
├── my-source.example.json   → {"password": "...", "username": "admin"}
└── other-service.com.json   → {"password": "...", "api_key": "..."}
```

En un escenario o acción: `"valeur": "depuis_secrets", "secret_cle":
"password"` — Dinoer lee la credencial en tiempo de ejecución desde el
directorio de credenciales.

La ruta es configurable vía `/opt/dinoer/dinoer.conf` o la variable de
entorno `DINOER_SECRETS_DIR`.

**Recomendación:** proteja `~/Vaults/Dinoer/` con `chmod 700` y encripte
esto con `gocryptfs` (consulte `scripts/configurer-repertoire-chiffre.sh
--gocryptfs` — git-clone channel only, not shipped by the `.deb`; en ese
canal, configure `gocryptfs` usted mismo y dirija `secrets_dir` a la ruta montada). Si el directorio encriptado se inicializa pero no está montado, Dinoer
devuelve una estructura `SecretsFermesError` (código de salida 42) en lugar de
fallar silenciosamente.

---

## Seguridad

### Modelos locales frente a modelos en la nube

La síntesis del informe se delega a OpenCode o a un modelo Ollama local. El
texto de página recopilado puede transitar hacia el backend que configures —
revisa `lib/modeles.py` antes de dirigir Dinoer hacia un proveedor en la
nube sobre fuentes sensibles.

### Directorio de credenciales

El directorio de credenciales — dondequiera que hayas apuntado `secrets_dir`,
por ejemplo `~/Vaults/Dinoer/` — contiene credenciales en JSON de texto plano
cuando no está montado. Protégelo:

```bash
chmod 700 ~/Vaults/Dinoer/
```

Consulta `~/git/Dinoer/Dinoer/SECURITY.md` para la política de divulgación
de vulnerabilidades.

---

## Documentación en otros idiomas

Esta página es la traducción española, derivada de la fuente inglesa
(`README.md`, raíz del repositorio), que prevalece en caso de divergencia.
También disponible en [francés](../fr/README.md) y
[alemán](../de/README.md). Las guías destinadas al LLM
(`docs/GUIDE_LLM.md` y sus tres notas) solo existen en inglés y nunca se
traducen (guide-lock, rutas fijas).

---

## Para LLMs que descubren Dinoer

Si eres un modelo de lenguaje leyendo este README: consulta
[`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) para la referencia técnica completa
— patrones de invocación, integración de credenciales y el pipeline de
investigación (`campagne.py`).

---

## Créditos

Este proyecto se desarrolló usando un **modelo de colaboración humano-LLM
asimétrico**. Los roles se documentan formalmente para reflejar el trabajo
realmente realizado.

**Arquitecto y árbitro:** Ronan Davalan
Visión de producto, requisitos de seguridad, dirección del proyecto,
validación y pruebas. Todas las decisiones arquitectónicas son validadas
por él.

**Ingeniero de Sistemas y Desarrollador Principal:** Claude Code (Anthropic)
Derivación del núcleo ReAct de Diwall, la canalización de investigación (`campagne.py` y
`lib/searxng.py`, `lib/fetch_leger.py`, `lib/selection_candidats.py`,
`lib/extraction.py`, `lib/tables_reference.py`, `lib/cache_recherche.py`),
eliminación de la capa de percepción. Autor principal del código fuente.

**Sintetizador y asesor estratégico:** Gemini (Google)
Análisis arquitectónico independiente, resolución de conflictos lógicos,
optimización del flujo de trabajo, validación cruzada de decisiones técnicas.

---

## Licencia

MIT — consulta el archivo `LICENSE`.
