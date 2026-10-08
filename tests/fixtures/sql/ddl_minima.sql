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

SELECT uno.ID
FROM ejemplo.UNO AS uno;
