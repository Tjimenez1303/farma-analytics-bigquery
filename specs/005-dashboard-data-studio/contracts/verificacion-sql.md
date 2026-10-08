# Contrato: consultas de verificación y `make bq-dashboard`

Las consultas de `sql/dashboard/` producen las cifras que el tablero tiene que mostrar con un estado
de filtros dado (FR-031). El subcomando `python -m warehouse dashboard`, detrás de
`make bq-dashboard`, las ejecuta y las cruza (FR-032).

## Archivos

```text
sql/dashboard/
├── kpis.sql                          # Totales de un periodo con los filtros
├── kpis_por_anio.sql                 # Totales por ANIO con los filtros salvo las fechas
├── gasto_entidad.sql                 # IMPORTE por ENTIDAD
├── participacion_institucion.sql     # IMPORTE y % por INSTITUCION
└── top10_molecula_fabricante.sql     # 10 pares MOLECULA y FABRICANTE_COMPRA por IMPORTE
```

## Reglas de las consultas (`tests/warehouse/test_dashboard_sql.py`)

- Cada archivo empieza con un comentario en inglés que dice qué componente del tablero verifica.
- Cada consulta lee solo de `farma_analytics.v_compras_farma_completa` con el alias `vista`, sin ID
  de proyecto, y no hace joins.
- Una CTE `filtrada` aplica el bloque de filtros, que es idéntico en las cinco consultas salvo la
  línea de fechas, ausente en `kpis_por_anio.sql`:

  ```sql
  WHERE
      vista.FECHA BETWEEN @fecha_inicio AND @fecha_fin
      AND (ARRAY_LENGTH(@entidades) = 0 OR vista.ENTIDAD IN UNNEST(@entidades))
      AND (ARRAY_LENGTH(@instituciones) = 0 OR vista.INSTITUCION IN UNNEST(@instituciones))
      AND (
          ARRAY_LENGTH(@grupos_institucionales) = 0
          OR vista.GRUPO_INSTITUCIONAL IN UNNEST(@grupos_institucionales)
      )
      AND (
          ARRAY_LENGTH(@grupos_terapeuticos) = 0
          OR vista.GRUPO_TERAPEUTICO IN UNNEST(@grupos_terapeuticos)
      )
      AND (ARRAY_LENGTH(@moleculas) = 0 OR vista.MOLECULA IN UNNEST(@moleculas))
  ```

- El precio es `SAFE_DIVIDE(SUM(...IMPORTE), SUM(...PIEZAS))`. No hay `AVG` de precios.
- La participación es `SAFE_DIVIDE(SUM(...IMPORTE), SUM(SUM(...IMPORTE)) OVER ())` multiplicada por
  100.
- Estilo del principio II: sin `SELECT *`, `GROUP BY` por nombre, `ROUND` y `ORDER BY` solo en el
  `SELECT` final, alias con `AS`, líneas de 100 caracteres o menos y SQLFluff sin violaciones.
- Las columnas de salida y su orden son las de
  [data-model.md](../data-model.md#consultas-de-verificación).
- `top10_molecula_fabricante.sql` ordena por `IMPORTE DESC, MOLECULA, FABRICANTE_COMPRA` y termina
  con `LIMIT 10`. `gasto_entidad.sql` y `participacion_institucion.sql` ordenan por `IMPORTE DESC` y
  después por el nombre.
- Los importes se devuelven sin redondear. Solo el precio y la participación se redondean, a 2 y 4
  decimales, para que la comparación con el tablero no dependa de un redondeo intermedio.

## Subcomando y objetivo

```text
make bq-dashboard [DESDE=AAAA-MM-DD] [HASTA=AAAA-MM-DD] [ENTIDAD=a,b] [INSTITUCION=a,b]
                  [GRUPO_INSTITUCIONAL=a,b] [GRUPO_TERAPEUTICO=a,b] [MOLECULA=a,b]
```

- Objetivo nuevo del `Makefile`, con las dependencias `require-venv require-project` y el texto de
  ayuda "Calcula sobre la vista las cifras que muestra el dashboard (KPIs, entidades, instituciones
  y top 10) con los filtros indicados".
- Llama a `python -m warehouse dashboard` con `--desde`, `--hasta`, `--entidad`, `--institucion`,
  `--grupo-institucional`, `--grupo-terapeutico` y `--molecula`. Los valores por defecto son
  2025-01-01, 2025-12-31 y listas vacías.
- El texto de `--help` de cada opción dice qué filtro del tablero reproduce, con su nombre visible
  ("Periodo", "Entidad", etc.).

## Comportamiento

1. Valida las fechas (formato ISO, inicio menor o igual que fin) y que los nombres de los filtros no
   estén vacíos. Un error termina con código 2 sin llamar a `bq`.
2. Comprueba que la vista tiene filas con `sql/ops/totales_vista.sql`. Si no las tiene, se detiene
   con el mensaje de `make bq-consultas`.
3. Calcula el periodo de referencia: las mismas fechas un año antes. El 29 de febrero pasa a ser el
   28 de febrero.
4. Ejecuta, cada una con dry run antes y con las labels de `BQ_JOB_LABELS`:
   - `kpis.sql` con el periodo pedido y con el de referencia;
   - `kpis_por_anio.sql`, `gasto_entidad.sql`, `participacion_institucion.sql` y
     `top10_molecula_fabricante.sql` con el periodo pedido.
   Los parámetros van como `--parameter=fecha_inicio:DATE:2025-01-01` y
   `--parameter=entidades:ARRAY<STRING>:["Jalisco"]`, con los valores codificados en JSON.
5. Imprime:
   - el estado de filtros en una línea;
   - las tres tarjetas con el valor del periodo, el de referencia y el cambio en %, con el formato
     del tablero (millones con 1 decimal, precio con 2) y el valor exacto entre paréntesis;
   - los totales por año;
   - las entidades, las instituciones y el top 10 en tablas de texto con los números alineados a la
     derecha;
   - los bytes estimados de cada consulta.
6. Comprueba las cifras cruzadas y termina con código 1 si alguna falla, informando la diferencia:
   - **D1**: la suma del importe de las entidades es igual al importe de `kpis.sql`;
   - **D2**: la suma del importe de las instituciones es igual al importe de `kpis.sql`, y sus
     participaciones suman 100 con una tolerancia de 0.01;
   - **D3**: cuando el periodo pedido es un año natural completo, el importe y las piezas de
     `kpis.sql` son iguales a los de ese año en `kpis_por_anio.sql`, y lo mismo para el periodo de
     referencia;
   - **D4**: el importe del top 10 no supera el importe de `kpis.sql`, y sus filas están ordenadas
     de mayor a menor.
7. Termina con código 0 si todo cuadra.

## Pruebas (`tests/warehouse/test_dashboard_command.py`, con el `bq` falso)

- Construcción de parámetros: fechas, listas vacías, listas con varios valores y nombres con
  tilde, codificados en JSON.
- Cálculo del periodo de referencia, incluido un 29 de febrero.
- Cada consulta va precedida de su dry run, lleva las labels y no repite los flags de
  `.bigqueryrc`.
- Un dry run fallido detiene el comando sin ejecutar la consulta.
- La vista vacía detiene el comando antes de ejecutar las consultas del tablero.
- D1 a D4 aceptan resultados que cuadran y rechazan cada caso que no cuadra.
- Ningún valor de los catálogos de referencia del generador para entidad, institución, grupo
  institucional, molécula y grupo terapéutico contiene una coma.
- `make help` muestra `bq-dashboard` con su texto.
