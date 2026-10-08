# Feature Specification: Fundaciones del proyecto (entorno local, proyecto de GCP y diagnóstico)

**Feature Branch**: `001-project-foundations`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Fundaciones del proyecto: preparar el entorno local y el proyecto de GCP para que cualquier persona pueda clonar el repositorio y, con comandos documentados, autenticarse con ADC, verificar que las herramientas necesarias están instaladas (gcloud, bq, Python, Node con Dataform CLI, SQLFluff, ripgrep, pre-commit) y ejecutar consultas en BigQuery solo con GoogleSQL. Incluye el .bigqueryrc versionado que el Makefile exporta mediante BIGQUERYRC, el ajuste de proyecto default_sql_dialect_option = 'only_google_sql', los controles de costo (alerta de presupuesto, cuota diaria de consultas y maximum_bytes_billed), la configuración de SQLFluff con dialecto BigQuery y pre-commit, el script scripts/lint_prosa.sh con la lista scripts/muletillas.txt del principio IX, el archivo .env.example sin secretos y un README inicial con el arranque rápido. El éxito se mide con un comando de diagnóstico (make doctor) que confirma herramientas, autenticación, dialecto y location sin consumir más que dry runs."

## Clarifications

### Session 2026-10-07

- Q: ¿Qué proyecto de GCP se usará para este trabajo? → A: Un proyecto nuevo y dedicado, creado desde cero, con cuenta de facturación asociada (no sandbox).
- Q: ¿Qué chequeos corren de forma automática y dónde? → A: SQLFluff y el bloqueo de secretos (`.env`, claves de cuenta de servicio y credenciales de Dataform) corren en pre-commit y también en GitHub Actions en cada PR hacia `main`, sin acceso a GCP (opción A: el check avisa pero no bloquea el merge). El lint de prosa queda como script que se ejecuta a mano con un comando documentado, fuera de los hooks y de CI. No hay ningún chequeo sobre material de referencia local.
- Q: ¿Con qué se gestionan Python y las dependencias de desarrollo? → A: Con uv. La versión de Python queda fijada en `.python-version` (3.12) y uv la descarga si falta. Las dependencias de desarrollo van en `pyproject.toml` y `uv.lock`, en local y en CI (decidido tras `/speckit-analyze`).

## User Scenarios & Testing *(mandatory)*

> Nota de alcance: en esta feature los "usuarios" son las personas que trabajan con el repositorio
> (autor, revisor técnico o cualquier persona que quiera reproducir la solución). Los nombres de archivo y
> de herramienta que aparecen abajo no son decisiones de diseño de esta spec: los impone la
> constitución (principios II, VIII y IX y la tabla de stack), así que forman parte del QUÉ.

### User Story 1 - Diagnóstico del entorno desde un clon limpio (Priority: P1)

Una persona clona el repositorio, sigue el arranque rápido del README, se autentica con ADC,
indica su proyecto de GCP en la configuración local y ejecuta un único comando de diagnóstico
(`make doctor`). El diagnóstico le dice, chequeo por chequeo, si su máquina y su proyecto están
listos: herramientas y versiones, autenticación, proyecto activo, dialecto, location y límite de
bytes. Cuando algo falla, el informe muestra qué falta y el comando exacto para corregirlo. El
diagnóstico no ejecuta ninguna consulta facturable: solo dry runs y lecturas de metadatos.

**Why this priority**: es la medida de éxito declarada de la feature y la puerta de entrada de
todas las features siguientes (generación, carga, SQL, dashboard). Sin un entorno verificable,
nadie puede reproducir la solución desde un clon limpio, que es lo que exige el principio VIII y
lo que recorre el video de demostración.

**Independent Test**: en una máquina con las herramientas instaladas y un proyecto de GCP
configurado, ejecutar `make doctor` y obtener todos los chequeos obligatorios en estado correcto y
código de salida 0. En una máquina a la que le falta algo, obtener el chequeo correspondiente en
estado de fallo, con su remedio, y código de salida distinto de 0.

**Acceptance Scenarios**:

1. **Given** un clon limpio, las herramientas instaladas en versiones soportadas, ADC configurado y
   el proyecto con el dialecto ya fijado, **When** la persona ejecuta `make doctor`, **Then** cada
   chequeo obligatorio aparece como correcto con el valor detectado (versión, cuenta, proyecto,
   dialecto, location, límite de bytes) y el comando termina con código 0.
2. **Given** una máquina sin una de las herramientas requeridas (por ejemplo ripgrep), **When** se
   ejecuta `make doctor`, **Then** el chequeo de esa herramienta aparece como fallo con la
   instrucción de instalación documentada, el resto de chequeos se sigue evaluando y el comando
   termina con código distinto de 0.
3. **Given** una herramienta instalada en una versión inferior a la mínima declarada, **When** se
   ejecuta el diagnóstico, **Then** el informe muestra la versión encontrada, la mínima exigida y el
   chequeo como fallo.
4. **Given** una máquina sin credenciales ADC, **When** se ejecuta el diagnóstico, **Then** el
   chequeo de autenticación falla e indica el comando de login de ADC documentado en el README.
5. **Given** que no hay proyecto de GCP configurado ni en `gcloud` ni en el entorno local, **When**
   se ejecuta el diagnóstico, **Then** el chequeo de proyecto falla, explica dónde se configura y
   los chequeos que dependen del proyecto se marcan como no evaluados, sin errores confusos.
6. **Given** cualquier ejecución del diagnóstico, **When** se revisa el historial de jobs del
   proyecto, **Then** no aparece ningún job ejecutado por el diagnóstico y los bytes facturados por
   él son 0.
7. **Given** una persona que llega por primera vez al repositorio, **When** lee el README, **Then**
   encuentra un arranque rápido numerado que la lleva del clon al diagnóstico correcto sin consultar
   otra fuente, incluyendo la declaración de que los datos del proyecto son sintéticos.

---

### User Story 2 - Proyecto de GCP restringido a GoogleSQL y con costo acotado (Priority: P1)

La persona responsable del proyecto de GCP aplica, con comandos documentados e idempotentes, los
ajustes de plataforma: el dialecto del proyecto queda en `only_google_sql` en la región de la
location configurada, existe una alerta de presupuesto y una cuota diaria de consultas a nivel de
proyecto. En el repositorio, toda invocación de `bq` lanzada por el `Makefile` usa el
`.bigqueryrc` versionado, que fija GoogleSQL, la location y `maximum_bytes_billed`, sin repetir
esos flags en cada comando y sin depender del `~/.bigqueryrc` personal.

**Why this priority**: el principio II exige que el dialecto lo imponga la configuración y la
plataforma, nunca el valor por defecto, y la tabla de stack exige controles de costo. Una consulta
en legacy SQL o un escaneo sin tope invalidan cualquier trabajo posterior o generan gasto no
previsto. Comparte prioridad con la historia 1 porque el diagnóstico verifica estos ajustes.

**Independent Test**: tras aplicar los ajustes, comprobar que (a) una consulta en legacy SQL es
rechazada por el proyecto, (b) una consulta cuya estimación supera el límite de bytes falla sin
cobrarse, (c) la alerta de presupuesto y la cuota diaria aparecen configuradas en la consola, y
(d) repetir los comandos de ajuste no crea duplicados ni cambia el estado.

**Acceptance Scenarios**:

1. **Given** el proyecto con el ajuste de dialecto aplicado, **When** alguien envía un job en
   legacy SQL desde el CLI o desde una biblioteca (API), **Then** BigQuery lo rechaza. El
   comportamiento en la consola se comprueba una vez y se documenta en el README, porque la
   documentación de BigQuery dice que el ajuste aplica al CLI y a la API y no cambia el dialecto
   por defecto de la consola.
2. **Given** el `.bigqueryrc` versionado y el `Makefile`, **When** un objetivo del `Makefile`
   ejecuta `bq`, **Then** `bq` usa el `.bigqueryrc` del repositorio aunque la persona tenga un
   `~/.bigqueryrc` propio con otros valores.
3. **Given** el límite de bytes configurado, **When** una consulta lanzada desde el repositorio
   estima más bytes que el límite, **Then** falla antes de ejecutarse y no se factura nada.
4. **Given** el proyecto sin alerta de presupuesto ni cuota diaria, **When** la persona responsable
   sigue los comandos documentados, **Then** queda una alerta de presupuesto mensual asociada al
   proyecto con umbrales de aviso y una cuota diaria de bytes de consulta a nivel de proyecto.
5. **Given** los ajustes ya aplicados, **When** se repiten los comandos de ajuste, **Then** el
   resultado es el mismo estado (un solo presupuesto, el mismo valor de cuota, el mismo dialecto).
6. **Given** el ajuste de dialecto no aplicado o aplicado en otra región, **When** se ejecuta
   `make doctor`, **Then** el chequeo de dialecto falla y muestra el comando para aplicarlo en la
   región correcta.

---

### User Story 3 - Estilo SQL y protección del repositorio en cada commit y en cada PR (Priority: P2)

Quien trabaja en el repositorio instala los hooks de pre-commit con un comando documentado. Desde
ese momento, cada commit revisa los `.sql` con SQLFluff (dialecto BigQuery y la configuración del
repositorio, que refleja las convenciones del principio II) e impide versionar credenciales y
archivos `.env`. Los mismos dos chequeos corren en GitHub Actions en cada pull request hacia
`main`, sin acceso a GCP, y se pueden ejecutar a mano sobre todo el repositorio con un comando
documentado.

**Why this priority**: el SQL es el criterio de mayor peso del proyecto y la constitución exige
SQLFluff sin violaciones (G2) y un repositorio libre de secretos (G8). Tener la puerta lista antes
de escribir el primer `.sql` evita retrabajo, pero no bloquea el arranque.

**Independent Test**: con los hooks instalados, intentar un commit con un `.sql` que viola reglas
de estilo y otro con un archivo `.env`; los dos se bloquean con un mensaje claro. Un commit con un
`.sql` que cumple el estilo pasa. El check de GitHub ejecuta exactamente el mismo comando que
`make lint`, así que ese comando falla en local con el `.sql` no conforme.

**Acceptance Scenarios**:

1. **Given** un `.sql` de ejemplo que cumple el estilo del principio II, **When** se ejecuta el
   lint de SQL, **Then** no se reporta ninguna violación.
2. **Given** un `.sql` de ejemplo con violaciones verificables por la herramienta (palabras clave en
   minúsculas, alias sin `AS`, `JOIN` sin `INNER`, `USING`, `GROUP BY` por ordinal, coma final,
   líneas de más de 100 caracteres), **When** se ejecuta el lint de SQL, **Then** cada violación se
   reporta con archivo, línea y regla.
3. **Given** los hooks instalados, **When** alguien intenta versionar `.env`, una clave de cuenta
   de servicio o un archivo de credenciales de Dataform, **Then** el commit se bloquea indicando el
   archivo y el motivo.
4. **Given** un clon limpio, **When** la persona ejecuta el comando documentado de instalación de
   hooks, **Then** los hooks quedan activos sin pasos manuales adicionales.
5. **Given** un pull request hacia `main`, **When** GitHub Actions ejecuta el workflow, **Then**
   corre SQLFluff y el bloqueo de secretos sobre todo el repositorio, sin credenciales de GCP, y el
   PR muestra el resultado como check verde o rojo. El check avisa, pero no bloquea el merge.

---

### User Story 4 - Revisión de la prosa para lectores bajo demanda (Priority: P2)

Quien escribe documentación para lectores (README, ADR, hallazgos, diccionario de datos,
especificación del dashboard, guion del video, comentarios de los `.sql` entregables, mensajes de
commit y descripciones de PR) ejecuta a mano `scripts/lint_prosa.sh`, con un comando documentado
del `Makefile`, y obtiene, por archivo y línea, las
marcas prohibidas por el principio IX: rayas y semirrayas, guiones usados como raya, punto y coma
en prosa, emojis, flechas y caracteres de caja, comillas curvas, títulos en Title Case, listas con
cabecera en negrita, restos de herramientas y las muletillas de la lista versionada
`scripts/muletillas.txt`.

**Why this priority**: el principio IX y la puerta G9 lo exigen para el README de esta misma
feature y para todos los entregables de texto. Va después del diagnóstico porque no condiciona la
reproducibilidad, pero el README inicial ya debe pasarlo. Se ejecuta a mano antes de abrir cada
PR, no en los hooks ni en CI.

**Independent Test**: ejecutar el script sobre un documento de ejemplo con una violación de cada
categoría y obtener una marca por cada una. Ejecutarlo sobre un documento limpio y sobre el README
y obtener cero marcas.

**Acceptance Scenarios**:

1. **Given** un documento con una violación de cada categoría del principio IX, **When** se ejecuta
   el script, **Then** reporta cada violación con archivo, línea, categoría y fragmento, y termina
   con código distinto de 0.
2. **Given** un documento que solo tiene esos caracteres dentro de bloques de código, código en
   línea o URL, **When** se ejecuta el script, **Then** no reporta nada, salvo los restos de
   herramientas, que se detectan aunque estén dentro de una URL (por ejemplo
   `utm_source=chatgpt.com`).
3. **Given** un `.sql` con una raya en un comentario y un `;` como terminador de sentencia, **When**
   se ejecuta el script, **Then** solo marca la raya del comentario.
4. **Given** un uso permitido del guion (marcador de lista, flag de CLI, kebab-case, rango
   2024-2025, palabra compuesta, fecha ISO o número negativo), **When** se ejecuta el script,
   **Then** no lo marca.
5. **Given** un término técnico permitido por el principio IX (por ejemplo "clave primaria" o
   "estimador robusto"), **When** se ejecuta el script, **Then** no lo marca, porque existe un
   mecanismo explícito y visible de excepciones de dominio.
6. **Given** una nueva muletilla añadida a `scripts/muletillas.txt`, **When** se vuelve a ejecutar
   el script, **Then** la detecta sin cambiar el código del script.
7. **Given** los artefactos de Spec Kit (`specs/`, `.specify/`) y los archivos de configuración,
   **When** se ejecuta el script sobre el repositorio completo, **Then** quedan fuera de la revisión.
8. **Given** un texto recibido por entrada estándar o como archivo (por ejemplo un mensaje de commit
   o la descripción de un PR), **When** se pasa al script, **Then** lo revisa con las mismas reglas.

---

### Edge Cases

- **Dos credenciales distintas**: `bq` y `gcloud` usan la credencial de usuario de `gcloud`,
  mientras que las bibliotecas cliente y Dataform usan ADC. Si las dos credenciales pertenecen a
  cuentas distintas o ADC no tiene proyecto de cuota, el diagnóstico lo avisa con el comando para
  alinearlas.
- **Proyecto distinto en `gcloud` y en el entorno local**: si el proyecto de `gcloud config` y el
  de `.env` no coinciden, el diagnóstico muestra cuál se usará y avisa de la discrepancia.
- **`~/.bigqueryrc` personal con otros valores**: el `Makefile` lo ignora porque exporta
  `BIGQUERYRC`. Si existe, el diagnóstico lo informa como aviso y el README advierte que `bq`
  lanzado fuera del `Makefile` lo usaría.
- **Variable `GOOGLE_APPLICATION_CREDENTIALS` apuntando a un archivo dentro del repositorio**: el
  diagnóstico falla, porque las claves de cuenta de servicio no se versionan (principio VIII).
- **API de BigQuery deshabilitada o falta de permiso para crear jobs**: el dry run falla; el
  diagnóstico distingue ambos casos y muestra el remedio (habilitar la API o pedir el rol mínimo).
- **Dataset `farma_analytics` ya existente en otra location**: la location de un dataset no se
  puede cambiar, así que el diagnóstico falla y explica la discrepancia. Si el dataset no existe
  todavía, el chequeo se omite sin error.
- **Ajuste de dialecto aplicado en una región distinta de la location configurada**: el ajuste
  tiene ámbito regional, así que el diagnóstico lo trata como no aplicado.
- **Sin permiso para cambiar opciones del proyecto, crear presupuestos o editar cuotas**: los
  comandos de ajuste fallan con un mensaje que nombra el permiso o rol necesario y no dejan estados
  parciales sin informar.
- **Proyecto sin facturación asociada** (por ejemplo, si se omitió ese paso): BigQuery funciona en
  modo sandbox, sin presupuesto ni cuota y con expiración de 60 días en tablas y vistas. El README
  advierte de esa consecuencia y el diagnóstico lo informa como aviso cuando puede detectarlo.
- **Sin conexión a internet**: los chequeos locales (herramientas y versiones, configuración
  versionada) se completan y los remotos se marcan como no evaluados, no como correctos.
- **Herramientas instaladas por gestores distintos** (Homebrew, pipx, npm global o local): el
  diagnóstico detecta la herramienta por su comando y su versión, no por la ruta de instalación.
- **Falsos positivos del lint de prosa** (nombres propios en títulos, como BigQuery o Data
  Studio): se resuelven con el mecanismo de excepciones explícito, nunca desactivando una regla
  para todo el repositorio.
- **`scripts/muletillas.txt` contiene las propias muletillas**: el archivo de la lista queda fuera
  de la revisión de prosa.
- **Plataforma**: el diagnóstico y los scripts funcionan en macOS y en Linux. Windows solo se
  admite mediante WSL.

## Requirements *(mandatory)*

### Functional Requirements

**Diagnóstico (`make doctor`)**

- **FR-001**: El repositorio MUST ofrecer un comando de diagnóstico (`make doctor`) que evalúe
  todos los chequeos obligatorios aunque alguno falle y termine con código 0 solo si todos los
  obligatorios son correctos.
- **FR-002**: El diagnóstico MUST verificar que están instaladas, en una versión igual o superior a
  la mínima declarada (o igual a la exacta cuando está fijada), estas herramientas: `gcloud`, `bq`,
  uv, el Python del proyecto (la versión fijada en `.python-version`), Node.js, Dataform CLI,
  SQLFluff, ripgrep, pre-commit y `make`.
- **FR-003**: Cada versión MUST declararse una sola vez: en el archivo que lee la propia
  herramienta cuando existe (`.python-version`, `required-version` y grupo `dev` de
  `pyproject.toml` con su `uv.lock`, `package.json` con su lockfile, `rev` de los hooks) y, para el
  resto de herramientas del sistema, en `scripts/tool_versions.env`. El diagnóstico lee esas
  fuentes y el README las enlaza.
- **FR-004**: El diagnóstico MUST verificar que existe una cuenta activa en `gcloud` y que ADC
  devuelve una credencial válida, y MUST avisar si ambas pertenecen a cuentas distintas o si ADC
  no tiene proyecto de cuota.
- **FR-005**: El diagnóstico MUST verificar que hay un proyecto de GCP configurado (en `gcloud` o en
  el entorno local) y accesible para la identidad activa, y MUST mostrar su ID.
- **FR-006**: El diagnóstico MUST confirmar que el `.bigqueryrc` en uso es el del repositorio y que
  fija GoogleSQL para consultas y para `mk`, la location y `maximum_bytes_billed`.
- **FR-007**: El diagnóstico MUST confirmar que el proyecto tiene `default_sql_dialect_option =
  'only_google_sql'` activo en la región de la location configurada, es decir, que el proyecto
  rechaza legacy SQL.
- **FR-008**: El diagnóstico MUST confirmar que un dry run de verificación se valida en la location
  configurada y, si el dataset `farma_analytics` ya existe, que su location coincide con la
  configurada.
- **FR-009**: El diagnóstico MUST NOT ejecutar consultas facturables ni modificar recursos: solo
  MAY usar dry runs, lecturas de metadatos y comandos locales.
- **FR-010**: Cada chequeo del informe MUST mostrar su nombre, su estado (correcto, aviso, fallo o
  no evaluado, que el informe escribe como `OK`, `AVISO`, `FALLO` y `OMITIDO`), el valor detectado y, en caso de fallo o aviso, el comando o la sección del README
  que lo corrige. El informe MUST terminar con un resumen de cuántos chequeos hay en cada estado.
- **FR-011**: Los chequeos que dependen de otro que falló (por ejemplo, los de BigQuery sin
  proyecto) MUST marcarse como no evaluados, con el motivo.
- **FR-012**: El diagnóstico MUST fallar si `GOOGLE_APPLICATION_CREDENTIALS` apunta a un archivo
  dentro del repositorio y MUST avisar si existe un `~/.bigqueryrc` personal.

**Configuración de BigQuery en el repositorio**

- **FR-013**: El repositorio MUST versionar un `.bigqueryrc` en la raíz que fije `--location` como
  flag global, `--use_legacy_sql=false` y `--maximum_bytes_billed` en `[query]`, y
  `--use_legacy_sql=false` en `[mk]`. MUST NOT incluir el ID de proyecto.
- **FR-014**: El `Makefile` MUST exportar `BIGQUERYRC` apuntando al `.bigqueryrc` del repositorio,
  y sus objetivos MUST NOT repetir los flags que ese archivo ya fija ni usar los prefijos
  `#standardSQL` o `#legacySQL`.
- **FR-015**: La location configurada en `.bigqueryrc` MUST ser la única fuente de la location del
  proyecto. Cualquier otra pieza que la necesite (comandos de ajuste, diagnóstico, documentación)
  MUST tomarla de ahí o comprobarse contra ella.
- **FR-016**: Los jobs que lance el `Makefile` MUST llevar labels estables de atribución de costo
  (por ejemplo `project` y `env`), en minúsculas y sin valores volátiles.

**Ajustes del proyecto de GCP**

- **FR-017**: El repositorio MUST ofrecer un comando documentado que aplique
  `default_sql_dialect_option = 'only_google_sql'` al proyecto configurado, en la región de la
  location configurada, sin ID de proyecto fijo en el código.
- **FR-018**: El repositorio MUST documentar comandos para crear una alerta de presupuesto mensual
  asociada al proyecto, con umbrales de aviso, y para fijar una cuota diaria de bytes de consulta a
  nivel de proyecto. El README MUST explicar que la alerta avisa pero no detiene el gasto y que la
  cuota es un tope duro.
- **FR-019**: Todos los comandos de ajuste MUST ser idempotentes: repetirlos no crea duplicados ni
  cambia un estado ya correcto.
- **FR-020**: Los comandos de ajuste MUST nombrar el permiso o rol que falta cuando fallan por
  autorización.
- **FR-021**: El README MUST documentar cómo comprobar manualmente que la alerta de presupuesto y la
  cuota diaria están activas.
- **FR-037**: El README MUST documentar, como primer paso del arranque, la creación de un proyecto
  de GCP nuevo y dedicado, la asociación de una cuenta de facturación y la habilitación de las APIs
  necesarias (como mínimo BigQuery), con el ID de proyecto y el ID de la cuenta de facturación
  tomados de `.env` y nunca versionados.

**Configuración local y secretos**

- **FR-022**: El repositorio MUST versionar `.env.example` con todas las variables que una persona
  puede configurar en el `Makefile` y los scripts (las obligatorias y las opcionales, estas
  comentadas), cada una con un comentario y un valor de ejemplo vacío o ficticio. Las variables que
  solo usan las pruebas quedan fuera. MUST NOT contener secretos, IDs reales ni datos personales.
- **FR-023**: `.gitignore` MUST excluir `.env`, claves de cuenta de servicio, archivos de
  credenciales de Dataform y cualquier otro archivo de credenciales local.
- **FR-024**: La autenticación documentada MUST ser ADC con login de usuario. El README MUST NOT
  proponer claves de cuenta de servicio.

**Calidad de SQL y hooks**

- **FR-025**: El repositorio MUST versionar una configuración de SQLFluff con dialecto BigQuery que
  aplique las convenciones del principio II que la herramienta puede verificar: palabras clave en
  mayúsculas, `AS` explícito en tablas y columnas, `INNER JOIN` calificado, sin `USING`, sin
  `GROUP BY` por ordinal, sin coma final, operadores `AND`/`OR` al inicio de línea y líneas de 100
  caracteres o menos. La política de capitalización de identificadores MUST admitir columnas en
  UPPER_SNAKE_CASE y alias en snake_case.
- **FR-026**: El repositorio MUST versionar una configuración de pre-commit que ejecute en cada
  commit exactamente dos chequeos: el lint de SQL sobre los `.sql` y un bloqueo de credenciales
  (`.env`, claves de cuenta de servicio y credenciales de Dataform). El lint de prosa MUST NOT
  formar parte de los hooks.
- **FR-038**: El repositorio MUST versionar un workflow de GitHub Actions que, en cada pull request
  hacia `main`, ejecute los mismos chequeos de pre-commit sobre todo el repositorio, sin
  credenciales ni acceso a GCP, y publique el resultado como check del PR. El check MUST NOT
  configurarse como requisito de merge en esta feature.
- **FR-027**: Las versiones de Python, SQLFluff, pre-commit, pytest, los hooks y Dataform CLI MUST
  fijarse en versión exacta en archivos versionados, con lockfile para las dependencias de Python
  (`uv.lock`) y de Node (`package-lock.json`).
- **FR-028**: El repositorio MUST incluir ejemplos de SQL (uno que cumple y otro con violaciones)
  que permitan comprobar que la configuración de SQLFluff acepta y rechaza lo esperado.

**Lint de prosa**

- **FR-029**: El repositorio MUST versionar `scripts/lint_prosa.sh`, que use ripgrep para revisar
  los archivos del alcance del principio IX y marque cada categoría que lista ese principio, con
  archivo, línea, categoría y fragmento, y termine con código distinto de 0 si hay marcas. El
  script MUST ejecutarse a mano mediante un objetivo documentado del `Makefile` y MUST NOT formar
  parte de los hooks ni de CI.
- **FR-030**: Antes de revisar, el script MUST excluir bloques de código, código en línea y URL; en
  los `.sql` MUST revisar solo los comentarios. Los restos de herramientas MUST detectarse también
  dentro de URL.
- **FR-031**: El script MUST leer las muletillas de `scripts/muletillas.txt` (una por línea, con
  líneas de comentario admitidas, sin distinguir mayúsculas), inicializada con todo el vocabulario y
  las fórmulas prohibidas del principio IX.
- **FR-032**: El script MUST respetar los usos permitidos del guion y del punto y coma del principio
  IX y MUST ofrecer un mecanismo explícito y visible de excepciones para los términos de dominio
  permitidos y para falsos positivos puntuales.
- **FR-033**: El script MUST aceptar rutas explícitas o entrada estándar, para revisar mensajes de
  commit y descripciones de PR, y MUST excluir los artefactos de Spec Kit, los archivos de
  configuración y la propia lista de muletillas.

**README**

- **FR-034**: El repositorio MUST tener un README inicial con un arranque rápido numerado que cubra
  prerrequisitos y versiones, creación del proyecto de GCP con facturación (FR-037), autenticación
  con ADC, configuración del proyecto (`.env` y `gcloud`), ajustes de proyecto de GCP, instalación
  de hooks y `make doctor` con un ejemplo de salida correcta.
- **FR-035**: El README MUST declarar que los datos del proyecto son sintéticos y MUST pasar
  `scripts/lint_prosa.sh` sin marcas.
- **FR-036**: El `Makefile` MUST listar sus objetivos con una descripción breve cuando se ejecuta
  sin argumentos o con `make help`.

### Key Entities *(include if feature involves data)*

- **Configuración versionada de `bq`** (`.bigqueryrc`): valores por defecto de los jobs del
  repositorio. Atributos: location, dialecto para consultas y para `mk`, límite de bytes
  facturados. Única fuente de la location.
- **Configuración local** (`.env`, a partir de `.env.example`): valores propios de cada persona que
  no se versionan, como el ID de proyecto, los datos para crear el presupuesto y la cuota diaria.
- **Catálogo de prerrequisitos**: lista de herramientas con su comando de detección, versión mínima
  o exacta e instrucción de instalación. Lo leen el diagnóstico y el README.
- **Informe de diagnóstico**: lista de chequeos con nombre, estado, valor detectado y remedio, más
  un resumen y un código de salida.
- **Ajustes del proyecto de GCP**: opción de dialecto por región, alerta de presupuesto (importe,
  umbrales) y cuota diaria de bytes de consulta.
- **Reglas de calidad**: configuración de SQLFluff, configuración de pre-commit, workflow de CI,
  ejemplos de SQL, `scripts/lint_prosa.sh`, `scripts/muletillas.txt` y las excepciones de dominio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona que ya tiene las herramientas instaladas pasa de clonar el repositorio a
  un diagnóstico sin fallos en 15 minutos o menos, siguiendo solo el README.
- **SC-002**: El diagnóstico termina en 60 segundos o menos con una conexión normal y factura 0
  bytes: el historial de jobs del proyecto no muestra ningún job ejecutado por él.
- **SC-003**: En los 8 escenarios de fallo inducido (herramienta ausente, versión inferior a la
  mínima, Python del proyecto distinto del fijado, sin ADC, sin proyecto, dialecto sin fijar en la
  región configurada, location distinta del dataset existente, credenciales dentro del
  repositorio), el diagnóstico marca el
  chequeo correcto como fallo, muestra un remedio y termina con código distinto de 0 (8 de 8).
- **SC-004**: El 100 % de los intentos de ejecutar legacy SQL en el proyecto desde el CLI o la API
  son rechazados. El resultado en la consola se comprueba una vez y queda documentado.
- **SC-005**: Una consulta cuya estimación supera el límite configurado falla sin coste (0 bytes
  facturados).
- **SC-006**: Repetir dos veces seguidas los comandos de ajuste del proyecto deja exactamente un
  presupuesto, el mismo valor de cuota y el mismo dialecto.
- **SC-007**: El repositorio contiene 0 secretos y 0 archivos `.env`, y los intentos de versionar
  credenciales se bloquean en local (3 de 3 tipos de archivo del escenario 3 de la historia 3:
  `.env`, clave de cuenta de servicio y credenciales de Dataform).
- **SC-010**: El 100 % de los PR hacia `main` muestran el check de CI. Ese check ejecuta el mismo
  comando que `make lint`, y ese comando falla en local cuando hay un `.sql` no conforme o un
  archivo de credenciales.
- **SC-008**: El lint de SQL acepta el ejemplo conforme sin violaciones y detecta cada una de las
  violaciones sembradas en el ejemplo no conforme (100 %).
- **SC-009**: El lint de prosa detecta el 100 % de las violaciones sembradas (al menos una por cada
  categoría del principio IX) y reporta 0 marcas sobre el documento limpio y sobre el README.

## Assumptions

- El dueño del repositorio ejecuta en persona todos los comandos que tocan GCP o su máquina:
  crear el proyecto, asociar la facturación, habilitar las APIs, autenticarse, instalar
  herramientas, aplicar los ajustes de proyecto, crear el presupuesto y la cuota y lanzar `make doctor`. La implementación
  entrega los archivos versionados y la secuencia exacta de comandos, en orden y con la salida
  esperada, así que el README tiene que bastar para que una persona los ejecute sin ayuda.
- Cada persona que reproduzca la solución usa su propio proyecto de GCP y su propia cuenta,
  creado con los mismos pasos del README. El ID de proyecto sale de `gcloud` o de `.env` y nunca
  se versiona.
- uv gestiona el Python del proyecto y sus dependencias de desarrollo, en local y en CI. Sustituye
  a `venv` y `pip`, y descarga la versión fijada de Python si falta.
- Los scripts usan `curl`, que viene de serie en macOS y en las distribuciones de Linux habituales,
  por eso no es un chequeo del diagnóstico.
- Se asume que los dry runs no quedan en el historial de jobs. La validación de SC-002 lo comprueba
  y, si aparecieran, el criterio se reformula para exigir 0 bytes facturados.
- El README se escribe en español, como la constitución y las reglas de prosa, y llama Data Studio
  a la herramienta de dashboards, su nombre desde abril de 2026.
- La location por defecto es `US`, como indica la constitución. Cambiarla es editar una sola línea
  de `.bigqueryrc`.
- El proyecto de GCP es nuevo, dedicado a este trabajo y con facturación asociada, como recomienda
  la constitución. El sandbox no es un camino soportado. Con el volumen previsto, el nivel gratuito
  de BigQuery cubre el uso y la alerta y la cuota actúan como red de seguridad.
- Los valores iniciales de los controles de costo se fijan en el plan según el volumen de datos de
  la feature de generación. Como orientación: un `maximum_bytes_billed` de alrededor de 1 GB por
  consulta, una cuota diaria muy por debajo del nivel gratuito mensual y un presupuesto mensual
  pequeño con avisos al 50 %, 90 % y 100 %. Los avisos van a los administradores de la cuenta de
  facturación, así que no se versiona ningún correo.
- El `.bigqueryrc` solo protege los jobs de `bq`. La consola, las bibliotecas de Python y Dataform
  no lo leen. Para ellos, el dialecto lo impone el ajuste de proyecto y el gasto lo acota la cuota
  diaria. Las features que lancen jobs desde Python MUST tomar el límite de bytes de la misma
  fuente.
- Verificar la alerta de presupuesto y la cuota exige permisos de facturación que no toda persona
  que clona el repositorio tiene. Por eso el diagnóstico no las verifica y el README documenta la
  comprobación manual.
- La forma concreta de confirmar el dialecto del proyecto sin ejecutar consultas facturables (por
  ejemplo, un dry run en legacy SQL que el proyecto debe rechazar) se resuelve en la fase de
  investigación del plan.
- El ajuste de dialecto tiene ámbito regional (`region-<location>.default_sql_dialect_option`),
  según la documentación de configuración por defecto de BigQuery.
- Instalar las herramientas queda fuera del tiempo de SC-001: el README enlaza a la instalación
  oficial de cada una y da un comando de ejemplo para macOS (Homebrew) y Linux.
- Fuera de alcance de esta feature, porque llegan en features posteriores: el generador de datos y
  sus dependencias de Python, la creación del dataset y las tablas, el proyecto Dataform
  (`workflow_settings.yaml`, declarations y assertions), la matriz de trazabilidad y el resto de
  objetivos del `Makefile` (generar, cargar, validar, desplegar).
- La configuración del repositorio en GitHub (solo squash merge, borrado automático de ramas y
  protección de `main` que exija el check de CI) es una recomendación de la constitución y no forma
  parte de esta feature. Se puede activar después sin cambiar el workflow.
- Los archivos de referencia locales del autor quedan fuera del repositorio mediante exclusiones
  locales de git y no se mencionan ni se verifican en ningún archivo versionado.
