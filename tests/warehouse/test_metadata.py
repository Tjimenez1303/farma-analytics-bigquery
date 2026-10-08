"""Comparison of bq show metadata with the DDL."""

import copy
import json

from warehouse import bq
from warehouse.metadata import compare, missing_objects


def _show(metadata, errors=None):
    errors = errors or {}

    def show(ref):
        if ref in errors:
            return bq.BqResult(2, errors[ref], "")
        return bq.BqResult(0, json.dumps(metadata[ref]), "")

    return show


def test_matching_metadata_has_no_differences(ddl, published):
    assert compare(ddl.dataset, ddl.tables, _show(published)) == []


def test_integer_type_and_missing_mode_are_equivalent(ddl, published):
    fields = published["farma_analytics.COMPRAS"]["schema"]["fields"]
    assert any(f["type"] == "INTEGER" for f in fields)
    assert any("mode" not in f for f in fields)
    assert compare(ddl.dataset, ddl.tables, _show(published)) == []


def _details(diffs):
    return {(d.objeto, d.detalle) for d in diffs}


def test_each_kind_of_difference_is_reported(ddl, published):
    changed = copy.deepcopy(published)
    changed["farma_analytics"]["location"] = "eu"
    changed["farma_analytics"]["labels"]["env"] = "prod"
    compras = changed["farma_analytics.COMPRAS"]
    compras["description"] = "otra"
    fields = compras["schema"]["fields"]
    fields[5]["type"] = "FLOAT"  # PIEZAS
    fields[6].pop("mode")  # IMPORTE
    fields[7]["description"] = "otra"  # FECHA
    fields.append({"name": "EXTRA", "type": "STRING"})
    clue_cat = changed["farma_analytics.CLUE_CAT"]["schema"]["fields"]
    clue_cat[1], clue_cat[2] = clue_cat[2], clue_cat[1]
    changed["farma_analytics.CUADRO_BASICO"]["schema"]["fields"].pop()

    diffs = compare(ddl.dataset, ddl.tables, _show(changed))
    assert {d.chequeo for d in diffs} == {"esquema_ddl"}
    assert _details(diffs) >= {
        ("farma_analytics", "location"),
        ("farma_analytics", "labels"),
        ("COMPRAS", "descripción de la tabla"),
        ("COMPRAS.PIEZAS", "tipo"),
        ("COMPRAS.IMPORTE", "modo"),
        ("COMPRAS.FECHA", "descripción"),
        ("COMPRAS.EXTRA", "columna"),
        ("CLUE_CAT.ENTIDAD", "nombre en la posición 2"),
        ("CUADRO_BASICO.FABRICANTE", "columna"),
    }


def test_location_is_case_insensitive(ddl, published):
    changed = copy.deepcopy(published)
    changed["farma_analytics"]["location"] = "us"
    assert compare(ddl.dataset, ddl.tables, _show(changed)) == []


def test_missing_dataset_on_stdout(ddl, published):
    diffs = compare(
        ddl.dataset,
        ddl.tables,
        _show(published, {"farma_analytics": "BigQuery error in show operation: Not found"}),
    )
    assert len(diffs) == 1
    assert diffs[0].detalle == "Falta farma_analytics: ejecuta 'make bq-schema'"
    assert missing_objects(diffs)


def test_missing_table_on_stderr(ddl, published):
    def show(ref):
        if ref == "farma_analytics.CLUE_CAT":
            return bq.BqResult(2, "", "Not found: Table farma_analytics.CLUE_CAT")
        return bq.BqResult(0, json.dumps(published[ref]), "")

    diffs = compare(ddl.dataset, ddl.tables, show)
    assert [d.detalle for d in diffs] == [
        "Falta farma_analytics.CLUE_CAT: ejecuta 'make bq-schema'"
    ]


def test_other_bq_error_is_reported(ddl, published):
    diffs = compare(ddl.dataset, ddl.tables, _show(published, {"farma_analytics": "Access Denied"}))
    assert diffs[0].detalle == "bq show falló"
    assert not missing_objects(diffs)
