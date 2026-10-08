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
- `make test` ejecuta las pruebas de los scripts y del generador de datos, que no necesitan red ni credenciales.
- `make lint-prosa` revisa el README, la carpeta `docs/` y los comentarios de los `.sql`.

El lint de prosa no forma parte de los hooks. Conviene ejecutarlo antes de abrir cada PR, y también sobre el mensaje del commit y la descripción del PR, que el script acepta por la entrada estándar:

```bash
git log -1 --format=%B | scripts/lint_prosa.sh -
```

La lista de muletillas está en [`scripts/muletillas.txt`](scripts/muletillas.txt) y se amplía añadiendo una línea. Los términos técnicos permitidos y los nombres propios que pueden ir en mayúscula en un título están en [`scripts/prosa_excepciones.txt`](scripts/prosa_excepciones.txt). Para un falso positivo puntual, la línea se marca con el comentario `<!-- lint-prosa: ignorar -->`.
