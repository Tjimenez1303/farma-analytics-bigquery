# Matriz de trazabilidad

Cada requisito del proyecto aparece con el artefacto que lo cumple y la forma de verificarlo. Cada feature añade sus filas al terminar, y antes de la entrega la cobertura tiene que ser completa.

## Materiales e insumos

| Requisito | Artefacto | Verificación |
|---|---|---|
| Generar `COMPRAS` con los campos `CLUE`, `CLAVE`, `COD_PROVEEDOR`, `MARCA`, `FABRICANTE`, `PIEZAS`, `IMPORTE` y `FECHA` | `data/COMPRAS.csv`, producido por `make data` | `tests/generator/test_contract.py` compara el encabezado literal y el formato de cada campo |
| Generar `CLUE_CAT` con los campos `CLUE`, `ENTIDAD`, `INSTITUCION`, `DELEGACION`, `GRUPO_INSTITUCIONAL`, `NIVEL_ATENCION` y `MUNICIPIO` | `data/CLUE_CAT.csv`, producido por `make data` | `tests/generator/test_contract.py` y `tests/generator/test_realism.py` |
| Generar `CUADRO_BASICO` con los campos `CLAVE`, `DESCRIPCION`, `MOLECULA`, `GRUPO_TERAPEUTICO`, `PRESENTACION` y `FABRICANTE` | `data/CUADRO_BASICO.csv`, producido por `make data` | `tests/generator/test_contract.py` y `tests/generator/test_realism.py` |
| Entregar los datos en CSV o Parquet | CSV en UTF-8 sin BOM, según [el contrato de formato](../specs/002-synthetic-data-generator/contracts/csv-format.md) | `tests/generator/test_contract.py` comprueba la codificación, los saltos de línea y el encabezado |
| Poder reproducir los datos | Semilla y parámetros en `generator/config.toml`, manifiesto en `generator/manifest.json` | `make data` verifica las huellas SHA-256 y `tests/generator/test_determinism.py` genera dos veces y compara |
