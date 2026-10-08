-- farma_analytics: schema, view and analytical queries over synthetic public purchases of
-- medicines in Mexico. Runs end to end in the BigQuery console; `make bq-schema` runs sections
-- 1 and 2 with a dry run before each statement.
-- Sections: 1 dataset, 2 tables, 3 view, 4 analytical queries.

-- Section 1: dataset.

-- Dataset that holds the fact table and both catalogs; its labels attribute storage costs.
CREATE SCHEMA IF NOT EXISTS farma_analytics
OPTIONS (
    location = 'US',
    description = 'Compras públicas de medicamentos en México con datos sintéticos.',
    labels = [('project', 'farma-analytics'), ('env', 'dev'), ('owner', 'bi')]
);

-- Section 2: tables.
-- No partitioning or clustering: the three tables total about 32 MB. No foreign keys: COMPRAS
-- keeps deliberate orphan keys and BigQuery would use the constraints to drop joins.

-- Fact table at purchase-line grain, joined to both catalogs by the view.
CREATE TABLE IF NOT EXISTS farma_analytics.COMPRAS (
    CLUE STRING NOT NULL OPTIONS (
        description = 'Clave CLUES de la unidad médica que compra.'
    ),
    CLAVE STRING NOT NULL OPTIONS (
        description = 'Clave del insumo comprado en el Compendio Nacional de Insumos.'
    ),
    COD_PROVEEDOR STRING NOT NULL OPTIONS (
        description = 'Código del proveedor que entrega el insumo.'
    ),
    MARCA STRING OPTIONS (
        description = 'Marca comercial del producto entregado.'
    ),
    FABRICANTE STRING OPTIONS (
        description = 'Fabricante del producto entregado, que puede diferir del de CUADRO_BASICO.'
    ),
    PIEZAS INT64 NOT NULL OPTIONS (
        description = 'Número de piezas (envases) entregadas. Medida aditiva.'
    ),
    IMPORTE NUMERIC NOT NULL OPTIONS (
        description = 'Importe de la línea en pesos mexicanos. Medida aditiva.'
    ),
    FECHA DATE NOT NULL OPTIONS (
        description = 'Fecha de la compra.'
    )
)
OPTIONS (
    description = 'Líneas de compra de medicamentos. Grano: una línea de compra. Sin llave única.'
);

-- Medical units catalog, one row per CLUE; gives entity and institution to each purchase.
CREATE TABLE IF NOT EXISTS farma_analytics.CLUE_CAT (
    CLUE STRING NOT NULL OPTIONS (
        description = 'Clave CLUES de la unidad médica. Llave del catálogo.'
    ),
    ENTIDAD STRING OPTIONS (
        description = 'Entidad federativa con su nombre oficial del INEGI.'
    ),
    INSTITUCION STRING OPTIONS (
        description = 'Institución pública de salud a la que pertenece la unidad.'
    ),
    DELEGACION STRING OPTIONS (
        description = 'Delegación u órgano administrativo de la institución en la entidad.'
    ),
    GRUPO_INSTITUCIONAL STRING OPTIONS (
        description = 'Agrupación de instituciones por tipo de población atendida.'
    ),
    NIVEL_ATENCION STRING OPTIONS (
        description = 'Nivel de atención de la unidad: primero, segundo o tercero.'
    ),
    MUNICIPIO STRING OPTIONS (
        description = 'Municipio o alcaldía donde está la unidad.'
    )
)
OPTIONS (
    description = 'Catálogo de unidades médicas. Grano: una unidad médica. Llave: CLUE.'
);

-- Supplies catalog, one row per CLAVE; gives molecule and therapeutic group to each purchase.
CREATE TABLE IF NOT EXISTS farma_analytics.CUADRO_BASICO (
    CLAVE STRING NOT NULL OPTIONS (
        description = 'Clave del insumo en el Compendio Nacional de Insumos. Llave del catálogo.'
    ),
    DESCRIPCION STRING OPTIONS (
        description = 'Descripción completa del insumo con el estilo del Cuadro Básico.'
    ),
    MOLECULA STRING OPTIONS (
        description = 'Denominación genérica del principio activo.'
    ),
    GRUPO_TERAPEUTICO STRING OPTIONS (
        description = 'Grupo terapéutico del Cuadro Básico al que pertenece la molécula.'
    ),
    PRESENTACION STRING OPTIONS (
        description = 'Forma farmacéutica, concentración y envase.'
    ),
    FABRICANTE STRING OPTIONS (
        description = 'Fabricante de referencia de la molécula, que puede diferir del de COMPRAS.'
    )
)
OPTIONS (
    description = 'Catálogo de insumos. Grano: una presentación de una molécula. Llave: CLAVE.'
);
