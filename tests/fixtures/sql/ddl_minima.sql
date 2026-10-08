-- Minimal DDL for the warehouse parser tests.
/* Block comment before the dataset. */
CREATE SCHEMA IF NOT EXISTS ejemplo
OPTIONS (
    location = 'US',
    description = 'Dataset de prueba, con coma y acentos: ñandú.',
    labels = [('project', 'demo'), ('env', 'test')]
);

-- First table.
CREATE TABLE IF NOT EXISTS ejemplo.UNO (
    ID STRING NOT NULL OPTIONS (description = 'Llave, única.'),
    VALOR NUMERIC OPTIONS (description = 'Valor con \'comillas\' escapadas.')
)
OPTIONS (description = 'Tabla uno. Grano: una fila por ID.');

CREATE TABLE IF NOT EXISTS ejemplo.DOS (
    ID STRING NOT NULL OPTIONS (description = 'Llave.'),
    CANTIDAD INT64 NOT NULL OPTIONS (description = 'Cantidad.'),
    DIA DATE OPTIONS (description = 'Día.')
)
OPTIONS (description = 'Tabla dos.');

-- View over both tables.
CREATE OR REPLACE VIEW ejemplo.v_ejemplo (
    ID OPTIONS (description = 'Llave de UNO.'),
    CANTIDAD OPTIONS (description = 'Cantidad de DOS.'),
    ANIO OPTIONS (description = 'Año de DIA.')
)
OPTIONS (
    description = CONCAT(
        'Vista ',
        'de prueba.'
    )
)
AS
SELECT
    uno.ID,
    dos.CANTIDAD,
    EXTRACT(YEAR FROM dos.DIA) AS ANIO
FROM ejemplo.UNO AS uno
INNER JOIN ejemplo.DOS AS dos
    ON uno.ID = dos.ID;

SELECT uno.ID
FROM ejemplo.UNO AS uno;
