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

## Arquitectura

```
campagne.py (orquestación)
  ├─ lib/searxng.py         → API JSON de SearXNG (solo HTTP, sin navegador)
  ├─ lib/fetch_leger.py     → requests + BeautifulSoup, respeta robots.txt
  ├─ rpa.py / shot.py       → Playwright, solo para páginas que el nivel ligero
  │                           marcó como «insuficientes» (shells solo-JS)
  ├─ lib/extraction.py      → extracción de hechos dirigida, trouve/valeur/url
  ├─ lib/tables_reference.py→ tabla persistente y con fuentes de sitios de referencia
  ├─ lib/cache_recherche.py → caché de búsqueda respaldada por ChromaDB
  └─ lib/synthese.py + lib/modeles.py → LLM delegado (OpenCode/Ollama),
                                        redacta el informe final
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

Solo canal de clonado git. **Aún no se ofrece un paquete `.deb`** — el
empaquetado se posterga deliberadamente hasta que el producto se estabilice.

```bash
git clone https://github.com/RonanDavalan/dinoer.git
cd dinoer
bash scripts/install.sh
```

Esto crea el usuario y grupo de sistema `dinoer`, el entorno virtual,
despliega el código en `/opt/dinoer/` y ejecuta una prueba de humo
(`shot.py --a11y` contra una URL real).

La configuración vive en `/etc/dinoer/dinoer.conf` (o `/opt/dinoer/dinoer.conf`
según tu destino de `deploy.sh`); junto a él se instala un ejemplo comentado
como `dinoer-sample.conf`.

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

**Recomendación:** protege `~/Vaults/Dinoer/` con `chmod 700` y cífralo con
`gocryptfs` (consulta `scripts/configurer-repertoire-chiffre.sh
--gocryptfs`). Si el directorio cifrado está inicializado pero no montado,
Dinoer devuelve un `SecretsFermesError` estructurado (código de salida 42)
en lugar de fallar silenciosamente.

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

**Ingeniero de sistemas y desarrollador principal:** Claude Code (Anthropic)
Bifurcación del núcleo ReAct de Diwall, el pipeline de investigación
(`campagne.py` y `lib/searxng.py`, `lib/fetch_leger.py`, `lib/extraction.py`,
`lib/tables_reference.py`, `lib/cache_recherche.py`), retirada de la capa de
percepción. Autor principal del código fuente.

**Sintetizador y asesor estratégico:** Gemini (Google)
Análisis arquitectónico independiente, resolución de conflictos lógicos,
optimización del flujo de trabajo, validación cruzada de decisiones técnicas.

---

## Licencia

MIT — consulta el archivo `LICENSE`.
