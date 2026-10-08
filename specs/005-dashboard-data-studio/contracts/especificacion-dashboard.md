# Contrato: especificación del dashboard (`docs/dashboard.md`)

`docs/dashboard.md` es la definición versionada del informe de Data Studio (principio VIII, FR-030).
Se escribe en español y pasa `scripts/lint_prosa.sh` (principio IX). Las tablas con datos reales
están permitidas. Su contenido sale de [data-model.md](../data-model.md) y de
[research.md](../research.md), redactado para lectores.

## Secciones obligatorias, en este orden

1. **Qué es y para quién.** Un párrafo: el tablero de compras públicas de medicamentos sobre la
   vista, para analistas comerciales de laboratorios, con datos sintéticos.
2. **Fuente de datos.** Tipo, conector, vista, sin consulta personalizada, credenciales, frescura y
   la razón de cada valor.
3. **Campos.** La tabla de los 22 campos (columna, nombre de negocio, tipo, agregación, uso) y la del
   campo calculado Precio Promedio, con la fórmula literal. Las alternativas aplicadas, si la prueba
   en el producto las exigió.
4. **Tema y colores.** Fondo, colores de texto, color de datos, acento, bordes, familia tipográfica
   y tamaños. Una tabla de contrastes con estas columnas exactas:
   `| Primer plano | Fondo | Uso | Contraste | Umbral |`, donde "Contraste" se escribe como
   `N.NN:1` y "Umbral" como `4.5:1`, `3:1` o `No aplica`.
5. **Rejilla, disposición y textos fijos.** Tamaño del lienzo, rejilla, la tabla de coordenadas de
   cada componente y el texto literal del título, el subtítulo, la etiqueta "Periodo", el botón y la
   etiqueta de comparación ([data-model.md](../data-model.md#textos-fijos)).
6. **Controles.** La tabla de controles con su valor por defecto, búsqueda, selección múltiple y
   límite de valores, y la cascada.
7. **Tarjetas.** Métrica, unidad, formato y comparación de cada una, y cómo se marca el sentido del
   cambio (flechas o la alternativa de R5).
8. **Gráficos.** Una subsección por gráfico con tipo, campos, orden, límite, etiquetas, color, título
   y cross-filtering. La del top 10 incluye la definición de "Top 10 de moléculas" (pares
   molécula-fabricante) y cuántas moléculas distintas tiene en el estado inicial.
9. **Recuadro de hallazgos.** El texto literal publicado, con el estado de filtros y la consulta de
   origen de cada cifra.
10. **Comportamientos comprobados en el producto.** Una tabla con lo que la documentación no
    aclaraba y el resultado observado: moneda MXN, `NULLIF` sobre agregados, flechas de la tarjeta,
    comparación sin datos, fechas exactas del periodo anterior, Reset y el rango de fechas, sufijos de los
    números compactos, fuente Roboto y `MX-CMX` en el mapa (con la alternativa aplicada si la hubo).
11. **Verificación contra el SQL.** El comando `make bq-dashboard` con sus variables y el registro de
    verificación (estado, componente, valor del tablero, valor del SQL, resultado) para el estado
    inicial y el filtrado.
12. **Compartir.** El modo de compartir, el enlace de lectura, la comprobación sin sesión (fecha y
    navegador) y el resultado de la prueba con un analista que no conoce el proyecto (SC-005).

## Reglas que se prueban (`tests/docs/test_dashboard_spec.py`)

- La tabla de campos tiene una fila por cada columna de la vista, con los mismos nombres que la
  sección 3 de `sql/farma_analytics.sql`, y ninguna fila de más.
- Ninguna fórmula de campo calculado contiene `AVG`.
- Cada fila de la tabla de contrastes con umbral numérico cumple:
  - el contraste declarado coincide, con dos decimales, con el que da la fórmula de WCAG 2.1 para
    los dos colores;
  - el contraste declarado es mayor o igual que su umbral.
- Los tamaños de letra declarados son tres o menos.
- El documento no contiene el ID del proyecto. La prueba compara con `GOOGLE_CLOUD_PROJECT` cuando
  está definido en el entorno. El enlace del
  informe no incluye el ID del proyecto y sí se versiona (FR-037).

Lo demás (que el informe coincide con el documento) se revisa a mano con la lista de
[quickstart.md](../quickstart.md) y queda en el registro de verificación.
