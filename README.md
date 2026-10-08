# farma-analytics-bigquery

Proyecto de analítica en BigQuery sobre compras públicas de medicamentos en México. Incluye la generación de los datos, el modelo dimensional y un dashboard interactivo en Data Studio para encontrar oportunidades comerciales.

Los datos son sintéticos. Los produce un generador versionado en este repositorio y no contienen información real de compras ni datos personales.

## Requisitos previos

Las versiones mínimas de las herramientas del sistema están en [`scripts/tool_versions.env`](scripts/tool_versions.env). La versión de Python está fijada en [`.python-version`](.python-version) y las dependencias de desarrollo en [`pyproject.toml`](pyproject.toml), con sus versiones exactas en `uv.lock`. Python no hace falta instalarlo a mano, porque uv descarga la versión fijada la primera vez.

En macOS, con Homebrew:

```bash
brew install --cask google-cloud-sdk
```

```bash
brew install uv node@22 ripgrep
```

```bash
xcode-select --install
```

El último comando instala `make` y `git` si todavía no los tienes.

En Linux, Google Cloud CLI se instala con la [guía oficial](https://cloud.google.com/sdk/docs/install) y uv con su instalador:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
sudo apt install make ripgrep
```

Node.js 22 se descarga desde [nodejs.org](https://nodejs.org).

## Arranque rápido

Estos pasos crean un proyecto de GCP nuevo para este repositorio y dejan el entorno listo. En los comandos, `<PROJECT_ID>` es el ID que elijas para el proyecto y `<BILLING_ACCOUNT_ID>` es el de tu cuenta de facturación.

1. Clona el repositorio y entra en la carpeta.

   ```bash
   git clone https://github.com/Tjimenez1303/farma-analytics-bigquery.git
   ```

   ```bash
   cd farma-analytics-bigquery
   ```

2. Inicia sesión en Google Cloud con tu cuenta de usuario.

   ```bash
   gcloud auth login
   ```

3. Crea el proyecto y asócialo a tu cuenta de facturación. Si no indicas `--name`, el nombre visible del proyecto es el mismo ID. El segundo comando muestra el ID de las cuentas de facturación a las que tienes acceso, y si sale vacío tienes que crear una en la [página de facturación de la consola](https://console.cloud.google.com/billing) antes de seguir.

   ```bash
   gcloud projects create <PROJECT_ID>
   ```

   ```bash
   gcloud billing accounts list
   ```

   ```bash
   gcloud billing projects link <PROJECT_ID> --billing-account=<BILLING_ACCOUNT_ID>
   ```

4. Deja el proyecto como predeterminado y habilita las APIs que usa el repositorio.

   ```bash
   gcloud config set project <PROJECT_ID>
   ```

   ```bash
   gcloud services enable bigquery.googleapis.com billingbudgets.googleapis.com cloudquotas.googleapis.com cloudbilling.googleapis.com --project=<PROJECT_ID>
   ```

5. Crea las credenciales por defecto de la aplicación (ADC), que son las que usan Python y Dataform, y asígnales el proyecto para el control de cuota.

   ```bash
   gcloud auth application-default login
   ```

   ```bash
   gcloud auth application-default set-quota-project <PROJECT_ID>
   ```

6. Copia la configuración local y rellena tus valores. El archivo explica cada variable.

   ```bash
   cp .env.example .env
   ```

7. Instala el entorno de desarrollo: Python, las herramientas de calidad y Dataform CLI.

   ```bash
   make setup-dev
   ```

8. Aplica los ajustes del proyecto: solo GoogleSQL, cuota diaria de consultas y alerta de presupuesto.

   ```bash
   make gcp-setup
   ```

9. Comprueba que todo está en orden. El diagnóstico solo hace dry runs y lecturas de metadatos, así que no factura nada.

   ```bash
   make doctor
   ```

Una salida correcta se parece a esta. B03 aparece como omitido hasta que se cree el dataset `farma_analytics`.

```text
Diagnóstico de farma-analytics-bigquery

OK       T01  gcloud                          540.0.0 (mínimo 500.0.0)
OK       T02  bq                              2.1.20 (mínimo 2.1.0)
OK       T03  Python del proyecto             3.12.14
OK       T04  Node.js                         22.18.0 (mínimo 22.0.0)
OK       T05  Dataform CLI                    3.0.70
OK       T06  SQLFluff                        4.3.0
OK       T07  pre-commit                      4.6.2
OK       T08  ripgrep                         14.1.1 (mínimo 14.0.0)
OK       T09  make                            3.81 (mínimo 3.81)
OK       T10  uv                              0.12.9 (mínimo 0.12.0)
OK       C01  .bigqueryrc del repositorio     location US, GoogleSQL, límite de bytes
OK       C02  ~/.bigqueryrc personal          no existe
OK       C03  Credenciales en el repositorio  GOOGLE_APPLICATION_CREDENTIALS vacío
OK       N01  Red                             Google APIs accesibles
OK       A01  Cuenta de gcloud                persona@example.com
OK       A02  ADC                             credencial válida
OK       A03  Proyecto de cuota de ADC        mi-proyecto
OK       A04  Misma cuenta en gcloud y ADC    persona@example.com
OK       P01  Proyecto de GCP                 mi-proyecto
OK       P02  Facturación                     activa
OK       B01  Dry run en la location          validado en US
OK       B02  Dialecto del proyecto           legacy SQL rechazado
OMITIDO  B03  Location de farma_analytics     el dataset aún no existe
              remedio: sin acción
OK       B04  Límite de bytes                 1.00 GiB por consulta

Resumen: 23 OK, 0 AVISO, 0 FALLO, 1 OMITIDO
```

Cuando un chequeo falla, la línea `remedio:` indica el comando o el paso que lo corrige. `make help` lista todos los objetivos disponibles.

## Datos sintéticos

Los datos de las tres fuentes (`COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO`) son sintéticos. Los fabricantes, las marcas y los proveedores son empresas ficticias, y las unidades médicas, las claves y las compras también son inventadas. Los nombres de las entidades, los municipios, las instituciones y las moléculas sí son reales, para que el análisis se parezca a un mercado verdadero. [`docs/datos_sinteticos.md`](docs/datos_sinteticos.md) describe cada campo, los patrones que el generador inyecta a propósito y las fuentes de los catálogos de referencia.

Para generar los datos en `data/` y comprobar que son idénticos a los de referencia:

```bash
make data
```

El comando escribe los tres CSV y un manifiesto con la huella SHA-256 de cada archivo, y lo compara con [`generator/manifest.json`](generator/manifest.json). Cada archivo debe salir como `OK`. Un `DIFIERE` indica que los bytes no coinciden, y el mensaje muestra las versiones de Python, NumPy y Faker de cada lado, porque la igualdad exacta solo está garantizada en el mismo entorno. `make data-verify` repite la comprobación sin regenerar.

La carpeta `data/` no se versiona. Cuando un cambio en [`generator/config.toml`](generator/config.toml) es intencional, `make data-manifest` actualiza el manifiesto de referencia, y los dos archivos van juntos en el mismo PR.

## Carga en BigQuery

El esquema de las tres tablas está escrito una sola vez, en las secciones 1 y 2 de [`sql/farma_analytics.sql`](sql/farma_analytics.sql). Ese archivo se puede ejecutar entero en la consola de BigQuery, y los objetivos de `make` lo usan como única fuente: crean el dataset y las tablas con sus sentencias y derivan de ellas el esquema con el que se cargan los CSV. Estos objetivos trabajan sobre el proyecto de GCP, así que los ejecuta quien tenga acceso a él.

1. Genera los datos y comprueba que coinciden con el manifiesto.

   ```bash
   make data
   ```

2. Crea el dataset `farma_analytics` y las tablas `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO`.

   ```bash
   make bq-schema
   ```

   Cada sentencia pasa antes por un dry run y solo se ejecuta si la validación no da errores. Al final, el comando compara lo publicado en BigQuery con la DDL (location, labels, tipos, modos y descripciones) y termina con `Metadatos: 0 diferencias con la DDL`. Repetirlo no cambia nada, porque las sentencias usan `CREATE ... IF NOT EXISTS`.

3. Carga los CSV.

   ```bash
   make bq-load
   ```

   Antes de llamar a BigQuery, el comando verifica `data/` contra el manifiesto y las tablas publicadas contra la DDL. Después reemplaza cada tabla con un solo job de carga (`bq load --replace`) que usa el esquema derivado de la DDL, sin autodetección y sin aceptar filas malas. Un job de carga es atómico, de modo que si falla la tabla conserva lo que tenía. Al terminar ejecuta los chequeos y muestra una huella del contenido de cada tabla, que sale idéntica si cargas dos veces los mismos archivos. La carga no crea ni modifica la vista de la sección siguiente. Si la vista ya existe, también ejecuta su chequeo, y si todavía no existe lo avisa sin fallar.

4. Revisa las tablas sin recargarlas.

   ```bash
   make bq-checks
   ```

5. Comprueba que cada chequeo detecta el error que le toca.

   ```bash
   make bq-checks-negativos
   ```

   Cada chequeo se ejecuta con unas pocas filas inventadas que traen un error a propósito, escritas dentro de la consulta en lugar de las tablas reales, así que no se factura ningún byte. Sirve para comprobar un chequeo después de modificarlo.

Los chequeos están en [`sql/checks/`](sql/checks), uno por archivo, y cada uno devuelve 0 filas cuando su regla se cumple:

- El número de filas de cada tabla es el del manifiesto (300 000, 2 000 y 161).
- `CLUE` es única en `CLUE_CAT` y `CLAVE` es única en `CUADRO_BASICO`.
- Las claves, `FECHA`, `PIEZAS` e `IMPORTE` no tienen nulos.
- `PIEZAS` es mayor que cero, `IMPORTE` no es negativo y `FECHA` cae dentro del periodo del generador.
- Las filas y el importe de `COMPRAS` cuadran con el `INNER JOIN` de los dos catálogos más las filas huérfanas, que son 750 por `CLUE` y 750 por `CLAVE`.
- El precio por pieza de cada `CLAVE` del catálogo queda entre 6.75 y 17 820 pesos, y el más caro no supera 4.4 veces el más barato.
- La vista tiene las filas de `COMPRAS` menos las huérfanas, su `IMPORTE` y sus `PIEZAS` suman lo mismo que el `INNER JOIN` de las tablas, y sus columnas calculadas no tienen nulos.

Ninguna de esas cifras está escrita en el SQL. El programa las lee del manifiesto y de [`generator/config.toml`](generator/config.toml) y se las pasa a cada consulta como parámetros, de modo que si cambia la configuración del generador los chequeos cambian con ella. Los límites del precio salen de los parámetros de precio: el precio base más bajo por el factor genérico más bajo y el ruido a la baja, y el precio base más alto por el factor de referencia más alto y el ruido al alza.

Cada consulta pasa por un dry run, lleva las labels `project` y `env` para atribuir su costo y respeta el límite de 1 GiB de `.bigqueryrc`. Los jobs de carga son la excepción, porque `bq load` no admite dry run ni labels. Por eso la validación de los CSV y del esquema se hace antes de cargar, y un job de carga no procesa bytes de consulta, así que el límite no le afecta.

Las tablas no están particionadas ni agrupadas en clústeres. Suman unos 32 MB, y la documentación de BigQuery sitúa el beneficio del clustering a partir de 64 MB y el del particionado en particiones de varios GB. Tampoco declaran claves foráneas, porque `COMPRAS` tiene huérfanos a propósito y BigQuery usaría esas restricciones para eliminar joins y daría cifras incorrectas.

Si cambias una descripción en la DDL después de crear las tablas, `make bq-schema` no la aplica, ya que `CREATE TABLE IF NOT EXISTS` no modifica una tabla existente. La verificación de metadatos marca la diferencia, y se corrige con `ALTER TABLE ... SET OPTIONS` o con `ALTER TABLE ... ALTER COLUMN ... SET OPTIONS` sobre el objeto afectado.

Repite `make bq-load` solo cuando cambien los datos. Cada recarga reescribe las tablas y reinicia los 90 días que BigQuery espera antes de cobrarlas como almacenamiento de largo plazo. A este volumen el ahorro es pequeño, pero no hay motivo para perderlo.

## Vista y consultas analíticas

La vista `v_compras_farma_completa` une cada línea de `COMPRAS` con su unidad médica de `CLUE_CAT` y con su insumo de `CUADRO_BASICO`. Tiene una fila por cada línea de compra cuya `CLUE` y cuya `CLAVE` existen en los catálogos, de modo que las 1 500 líneas huérfanas quedan fuera y la vista tiene 298 500 filas, como comprueba el chequeo `reconciliacion_vista`. Las consultas analíticas y el dashboard leen solo de ella, para que den las mismas cifras.

`FABRICANTE` aparece en `COMPRAS` y en `CUADRO_BASICO` con significados distintos, así que la vista lo separa en `FABRICANTE_COMPRA`, el fabricante del producto entregado, y `FABRICANTE_CATALOGO`, el de referencia de la molécula. Añade tres columnas calculadas por fila para el dashboard. `ANIO` y `MES` (el primer día del mes) sirven para series y comparaciones anuales, y `ENTIDAD_ISO` lleva el código ISO 3166-2 de la entidad, que Data Studio reconoce en los mapas sin confundir el estado de México con el país. Ninguna columna guarda un precio, porque un precio promedio no se puede sumar entre filas y tiene que calcularse al consultar.

La vista y sus consultas están en las secciones 3 y 4 de [`sql/farma_analytics.sql`](sql/farma_analytics.sql). Estos objetivos también trabajan sobre el proyecto de GCP.

1. Crea o reemplaza la vista.

   ```bash
   make bq-vista
   ```

   La sentencia pasa antes por un dry run. Reemplazar la vista no borra datos, porque una vista lógica no los guarda. Al terminar se ejecutan los siete chequeos y la comparación de los metadatos de la vista (tipo, dialecto, columnas y descripciones), y la salida acaba en `Chequeos: 7 de 7 en 0 filas. Metadatos: 0 diferencias.` Si cambias la vista, basta con repetir este comando sin recargar las tablas.

2. Responde las tres preguntas comerciales.

   ```bash
   make bq-consultas
   ```

   Primero calcula las filas y los totales de la vista, y se detiene si la vista está vacía. Después ejecuta las cuatro consultas de la sección 4, cada una con su dry run, e imprime las respuestas completas de las dos primeras y las 20 primeras filas de las de precio, que tienen cientos. La consola de BigQuery las muestra completas. Por último comprueba que las cifras cuadran entre consultas y con el total de la vista, y termina con `Cifras cruzadas: 5 de 5 cuadran.`

Las métricas tienen una sola definición, la misma en el SQL, el dashboard y los documentos:

| Métrica | Definición |
|---|---|
| Monto total | `SUM(IMPORTE)` |
| Piezas | `SUM(PIEZAS)` |
| Precio promedio | `SUM(IMPORTE) / SUM(PIEZAS)`, con `SAFE_DIVIDE` en SQL |
| Importe promedio por línea | `AVG(IMPORTE)` |
| Participación | valor del grupo entre el total de la vista, en porcentaje |

Algunas preguntas admiten más de una lectura. Estas son las que usamos y la razón de cada una:

| Duda | Definición | Razón |
|---|---|---|
| Qué es volumen de compra | `SUM(IMPORTE)`, y la misma consulta muestra `SUM(PIEZAS)` como alternativa | Es la medida de la pregunta de las moléculas y la del gasto del dashboard |
| Institución y entidad juntas o por separado | Las tres lecturas: la combinación, la institución sola y la entidad sola | Las tres salen de una sola lectura de la vista con `GROUPING SETS` |
| Qué fabricante se usa en el precio | `FABRICANTE_COMPRA`, y otra consulta da el precio por `FABRICANTE_CATALOGO` | Es quien vendió a ese precio. Cada molécula tiene un solo fabricante de referencia, así que la alternativa equivale al precio de la molécula en todo el mercado |
| Empates | En las 5 moléculas, el orden alfabético decide quién entra en el corte. En los líderes se usa `RANK`, que muestra a todos los empatados | La primera respuesta tiene que tener 5 filas exactas, y la segunda no debe esconder un empate |

El precio promedio por molécula mezcla presentaciones con envases de distinto tamaño, porque la pregunta pide el precio por molécula y no por `CLAVE`. Para comparar presentaciones hay que agrupar por `CLAVE` o por `PRESENTACION`.

## Controles de costo

El repositorio limita el gasto en tres capas, porque ninguna cubre todos los casos por sí sola.

El archivo [`.bigqueryrc`](.bigqueryrc) fija un límite de 1 GiB facturado por consulta. Si la estimación de una consulta lo supera, BigQuery la rechaza antes de ejecutarla y no cobra nada. Este límite solo protege las consultas que lanza `bq` desde el `Makefile`, ya que la consola de BigQuery, las bibliotecas de Python y Dataform no leen ese archivo. Cambiarlo es editar una línea y pasa por un PR como cualquier otro cambio.

La cuota diaria de consultas del proyecto (`make gcp-quota`) cubre todo lo demás. Su valor está en `.env` como `QUERY_QUOTA_GIB_PER_DAY`, con 100 GiB por día en el ejemplo. Es un tope duro: al alcanzarlo, BigQuery devuelve el error `usageQuotaExceeded` a todas las consultas del proyecto hasta la medianoche del horario del Pacífico. Para ajustarla necesitas el rol Quota Administrator (`roles/servicemanagement.quotaAdmin`).

La alerta de presupuesto (`make gcp-budget`) avisa por correo a los administradores de la cuenta de facturación cuando el gasto del mes llega al 50 %, al 90 % y al 100 % de `BUDGET_AMOUNT`. Avisa pero no detiene el gasto. Para crearla necesitas el rol Billing Account Administrator o Billing Account Costs Manager.

Con el volumen de este proyecto, el uso cabe en el nivel gratuito de BigQuery y estos controles quedan como red de seguridad. Puedes comprobarlos a mano en la consola de Google Cloud. El presupuesto está en Facturación, en la sección Presupuestos y alertas. La cuota está en IAM y administración, en Cuotas y límites del sistema, buscando "Query usage per day" de la API de BigQuery.

Si el proyecto se queda sin cuenta de facturación, BigQuery pasa a modo sandbox. En ese modo no hay presupuesto ni cuota que aplicar, y las tablas y vistas caducan a los 60 días. Por eso este repositorio usa un proyecto con facturación.

### Dialecto y archivo de configuración de bq

`make gcp-dialect` fija la opción `default_sql_dialect_option = 'only_google_sql'` del proyecto, y desde ese momento BigQuery rechaza los jobs en legacy SQL que llegan por el CLI o la API. La documentación no lo garantiza para la consola, así que lo comprobamos el 8 de octubre de 2026: una consulta con el prefijo `#legacySQL` en la consola también se rechaza, con el mensaje "Legacy SQL queries are not supported in this project". La opción es regional, así que se aplica en la región de la location de `.bigqueryrc` (`region-us`). Antes de ejecutar el `ALTER PROJECT`, el objetivo lo valida con un dry run y se detiene si la validación falla. Para cambiar opciones del proyecto necesitas el rol BigQuery Admin.

El `Makefile` exporta `BIGQUERYRC` para que `bq` use el `.bigqueryrc` del repositorio. Si ejecutas `bq` fuera de `make`, usará tu `~/.bigqueryrc` personal a menos que antes exportes la variable:

```bash
export BIGQUERYRC="$PWD/.bigqueryrc"
```

## Calidad

Cada commit pasa por las revisiones automáticas que instala `make setup-dev` con pre-commit. SQLFluff revisa el estilo de los archivos `.sql` con las reglas de [`.sqlfluff`](.sqlfluff), Ruff revisa el estilo y el formato del código Python con la configuración de [`pyproject.toml`](pyproject.toml), y otro hook bloquea los archivos `.env`, las claves de cuenta de servicio y las credenciales de Dataform. GitHub Actions ejecuta las mismas revisiones y las pruebas en cada pull request hacia `main`, sin acceso a GCP. Los checks avisan en el PR, pero no impiden el merge.

Estos objetivos ejecutan las revisiones a mano:

- `make lint` ejecuta todas las revisiones de pre-commit sobre el repositorio, con el mismo comando que usa GitHub Actions.
- `make lint-sql` revisa solo el estilo SQL.
- `make test` ejecuta las pruebas de los scripts, del generador de datos y del programa de carga, que no necesitan red ni credenciales.
- `make lint-prosa` revisa el README y la carpeta `docs/`.

El lint de prosa no forma parte de los hooks. Conviene ejecutarlo antes de abrir cada PR, y también sobre el mensaje del commit y la descripción del PR, que el script acepta por la entrada estándar:

```bash
git log -1 --format=%B | scripts/lint_prosa.sh -
```

La lista de muletillas está en [`scripts/muletillas.txt`](scripts/muletillas.txt) y se amplía añadiendo una línea. Los términos técnicos permitidos y los nombres propios que pueden ir en mayúscula en un título están en [`scripts/prosa_excepciones.txt`](scripts/prosa_excepciones.txt). Para un falso positivo puntual, la línea se marca con el comentario `<!-- lint-prosa: ignorar -->`.
