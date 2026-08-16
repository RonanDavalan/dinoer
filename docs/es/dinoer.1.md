% DINOER(1) | Comandos de Dinoer
%
% Agosto de 2026

# NOMBRE

dinoer - conjunto de herramientas de automatización e investigación web basado en ReAct para agentes LLM

# SINOPSIS

**shot.py** \[*opciones*\] **--url** *URL*

**rpa.py** \[*opciones*\] **--scenario** *ARCHIVO*

**campagne.py** \[*opciones*\] **--manifeste** *ARCHIVO*

**journal.py** \[*opciones*\]

**scripts/monter-repertoire-chiffre.sh**

**scripts/demonter-repertoire-chiffre.sh**

**scripts/monitor-verifier.sh** **--scenario** *ARCHIVO* **--reference** *ARCHIVO*

# DESCRIPCIÓN

Dinoer le da a un agente LLM manos sobre interfaces web que de otro modo no
podría operar: acciones impulsadas por Playwright controladas por un núcleo
de ejecución ReAct, con un árbol de accesibilidad (**--a11y**) como los ojos
cuando el agente lee el estado. Cada comando imprime un único objeto JSON en
la salida estándar, diseñado para ser leído por un programa y no por un humano.

Dinoer se distribuye de dos maneras: este paquete [`.deb`] o una clonación de Git instalada por **scripts/install.sh** bajo **/opt/dinoer/** para aquellos que deseen modificar el código. Los puntos de entrada de Python se ejecutan dentro del entorno virtual:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py ...

Para la lista exhaustiva de opciones de cualquier comando, ejecútelo con
**--help** — esa salida siempre tiene prioridad sobre esta página.

# COMANDOS

**shot.py**
: Captura una página y devuelve un JSON que la describe. Con **--a11y**, se
incluye el árbol de accesibilidad. Las acciones se pueden ejecutar en la
misma sesión del navegador mediante **--actions** (un archivo JSON).
**--reprendre-session** reutiliza únicamente las cookies, nunca el estado
del DOM.

**rpa.py**
: Ejecuta un archivo de escenario (JSON) que describe una secuencia de
acciones, y devuelve una línea en formato JSON. Este es el comando a
utilizar para cualquier operación repetible, y el único que evalúa las
aserciones del escenario y admite **--replay-verifier**.

**campagne.py**
: Orquesta una campaña de investigación profunda a partir de un manifiesto
JSON: paginación por fuente, deduplicación mediante caché vectorial,
extracción dirigida sin síntesis. Lee `/opt/dinoer/dinoer.conf` de forma
fija, solo para su clave `campagnes_dir` — nunca `DINOER_CONF`, ver
ARCHIVOS más abajo.

**journal.py**
: Lee el registro de operaciones de solo añadido en
**/var/log/dinoer/operations.jsonl**. Filtra por objetivo, fecha,
mutabilidad, errores o intención; devuelve texto plano o JSON.

**scripts/monter-repertoire-chiffre.sh**, **scripts/demonter-repertoire-chiffre.sh**
: Monta y desmonta el directorio de credenciales cifrado con gocryptfs.
Dinoer se niega a resolver cualquier credencial mientras está cerrado,
saliendo con el código de estado 42 en lugar de recurrir a una alternativa
menos segura. Configurado una vez por **scripts/configurer-repertoire-chiffre.sh**.

**scripts/monitor-verifier.sh**
: Ejecuta una única pasada de no regresión estructural de un escenario
contra una referencia guardada y sale con un código distinto de cero si hay
divergencias. Diseñado para ser ejecutado por cron o un temporizador
systemd; no contiene ningún bucle propio.

# OPCIONES COMUNES

Las opciones que se muestran a continuación son comunes a **shot.py** y
**rpa.py**, a menos que se indique lo contrario. Esta es una selección, no
la lista completa.

**--guide-version** *X.Y*
: Prueba obligatoria de que **/opt/dinoer/docs/GUIDE_LLM.md** fue leído. Sin
ella — y sin un marcador local aún válido — el comando se niega a
ejecutarse y sale con código 1. El valor esperado es el comentario
*notice-version* en la línea 3 de esa guía. Este es el único lugar donde
Dinoer no es opcional.

**--version**
: Imprime la versión instalada en formato JSON y termina, sin iniciar un
navegador. Distinta de **--guide-version**; los dos números no están
relacionados.

**--a11y**
: Incluye el árbol de accesibilidad en la salida JSON. El agente lee el DOM
a través de este árbol; Dinoer no tiene ninguna ruta de captura de pantalla
o de imagen.

**--wait-until** *networkidle*|*load*|*domcontentloaded*
: Cuándo se considera que la navegación inicial ha finalizado. El valor
predeterminado, *networkidle*, espera 500 ms de silencio de red y es
adecuado para la mayoría de los objetivos. Una página que realiza sondeos
continuos nunca queda en silencio — use *load* en ese caso; aumentar
**--timeout** no puede ayudar, ya que la página nunca terminará.

**--timeout** *MS*
: Tiempo de espera por operación en milisegundos (por defecto 10000).

**--stealth**
: Elimina los marcadores automáticos que identifican un navegador sin
interfaz gráfica. No cambia la dirección IP del operador ni falsifica una
identidad — el objetivo es el trato equitativo, no el disfraz.

**--secrets** *ARCHIVO*
: Resuelve las credenciales desde un archivo JSON explícito dentro de un
directorio montado, en lugar de la búsqueda predeterminada basada en el
host. Nunca pase una contraseña en la línea de comandos: los campos del
escenario usan `"depuis_secrets"` más `secret_cle`, y la credencial se
resuelve dentro de Playwright.

**--no-evaluer**
: Rechaza la acción **evaluer** para toda la ejecución — no se ejecuta
JavaScript arbitrario en la página de destino.

**--no-filtre-evaluer**
: Desactiva la neutralización en la salida estándar de los valores
devueltos por **evaluer**, las URLs y los mensajes de error — solo para
ejecuciones de depuración explícitas. La neutralización está activada por
defecto; cuando se desactiva, se establece `boussole.filtre_evaluer_actif:
false` en la salida para que el operador pueda auditarlo directamente
desde el JSON.

**--replay-verifier** *ARCHIVO*
: Compara la ejecución actual contra una referencia guardada y sale con un
código distinto de cero si hay divergencias. La referencia se escribe con
**--sauver-verifier-reference**. Solo **rpa.py**.

# ARCHIVOS

**/etc/dinoer/dinoer.conf**
: Configuración leída por el resolvedor de credenciales (`shot.py`, `rpa.py`, a través de
**DINOER_CONF**, que sobrescribe esta ruta). Creado por el operador, nunca
generado automáticamente. `secrets_dir` dentro de él apunta al directorio de
credenciales montado. **campagne.py no lee este archivo** — corregido
15/08/2026: lee un valor codificado `/opt/dinoer/dinoer.conf` para su propia
clave `campagnes_dir` únicamente (`campagne.py::_CONF_PATH`), nunca `DINOER_CONF`,
por lo tanto, en el canal `.deb` no verá este archivo incluso si está presente.

**/opt/dinoer/**
: Código de la aplicación, el entorno virtual de Python y la documentación
a la que hacen referencia los comandos mismos.

**/opt/dinoer/docs/GUIDE_LLM.md**
: El punto de entrada que un agente debe leer obligatoriamente.
**MANUEL.md**, en el mismo directorio, contiene los comandos exactos con
rutas reales.

**/var/log/dinoer/**
: Registro de operaciones de solo añadido (`operations.jsonl`) y el
directorio de evidencia estructurada. Se conserva entre redespliegues.

**/tmp/dinoer/**
: Directorio de trabajo efímero por ejecución, se limpia al reiniciar.

# ESTADO DE SALIDA

**0**
: La ejecución se completó. Tenga en cuenta que un error HTTP 404 o 403 en
el objetivo se reporta en el JSON, no como un fallo del comando.

**1**
: La ejecución falló, o la verificación previa de lectura de la guía no se
cumplió (*guide_non_lu*).

**2**
: Argumentos incompatibles, rechazados antes de que se iniciara cualquier
navegador.

**42**
: El directorio de credenciales está cerrado, o un archivo de credenciales
falló su checksum de integridad. Móntelo con
**scripts/monter-repertoire-chiffre.sh**, o revisa el archivo de
credenciales si el mensaje indica un checksum inválido.

**43**
: No se ha configurado **secrets_dir**. Configúrelo en **dinoer.conf**, o apunte
**DINOER_CONF** a un archivo de configuración específico del proyecto.

# EJEMPLOS

Capturar una página con el árbol de accesibilidad:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url https://example.com --a11y --guide-version 1.6

Leer solo el estado de una página, sin ejecutar ninguna acción:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url https://example.com --guide-version 1.6

Acceder a un panel de administración que actualiza estadísticas continuamente:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url http://target.local/ --wait-until load --a11y

Ejecutar un escenario con credenciales de un archivo explícito:

    /opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
        --scenario ./login.json --secrets ~/Vaults/project/creds.json

Verificar que una página no ha retrocedido estructuralmente:

    bash scripts/monitor-verifier.sh --scenario ./page.json --reference ./page.ref.json

Leer el registro de operaciones de un objetivo:

    /opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible example.com --format json

# VÉASE TAMBIÉN

La documentación completa se instala con el paquete:
**/opt/dinoer/docs/MANUEL.md** para el manual del operador,
**/opt/dinoer/docs/GUIDE_LLM.md** para la guía dirigida a los agentes,
**/opt/dinoer/docs/FAQ_LLM.md** para las respuestas organizadas por versión.
