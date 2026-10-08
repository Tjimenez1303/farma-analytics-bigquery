# Contrato: formato de los CSV (`data/*.csv`)

| Aspecto | Regla |
|---|---|
| Archivos | `data/COMPRAS.csv`, `data/CLUE_CAT.csv` y `data/CUADRO_BASICO.csv`, con el nombre exacto de la tabla. |
| Codificación | UTF-8 sin BOM. |
| Fin de línea | LF (`\n`), también en la última fila. |
| Delimitador y comillas | Coma. Comillas dobles solo cuando el campo contiene coma, comilla o salto de línea (`QUOTE_MINIMAL`). Una comilla dentro de un campo se duplica. |
| Encabezado | Una fila con los nombres de campo exactos y en el orden de los requisitos. |
| Fechas | `YYYY-MM-DD`. |
| Enteros | Dígitos sin signo ni separador de miles. |
| Importes | Punto decimal y exactamente dos decimales (`1234.50`), sin separador de miles ni símbolo de moneda. |
| Claves | Texto tal cual, con ceros a la izquierda. |
| Vacíos | No hay campos vacíos. |
| Saltos de línea dentro de campos | No hay. |
| Orden de filas | El de [data-model.md](../data-model.md), siempre el mismo. |

Encabezados exactos:

```text
COMPRAS:        CLUE,CLAVE,COD_PROVEEDOR,MARCA,FABRICANTE,PIEZAS,IMPORTE,FECHA
CLUE_CAT:       CLUE,ENTIDAD,INSTITUCION,DELEGACION,GRUPO_INSTITUCIONAL,NIVEL_ATENCION,MUNICIPIO
CUADRO_BASICO:  CLAVE,DESCRIPCION,MOLECULA,GRUPO_TERAPEUTICO,PRESENTACION,FABRICANTE
```

Carga prevista (feature posterior): `bq load --source_format=CSV --skip_leading_rows=1` hacia
tablas ya creadas con la DDL, sin autodetección de esquema y sin `--allow_quoted_newlines`.
