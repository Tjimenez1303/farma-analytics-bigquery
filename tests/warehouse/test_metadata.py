"""Comparison of bq show metadata with the DDL."""

import copy
import json

import pytest

from warehouse import bq
from warehouse.ddl import parse_file
from warehouse.metadata import MetadataError, compare, missing_objects, object_exists


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


# View metadata (FR-018), on the fixture view so these tests do not depend on section 3.


@pytest.fixture
def fixture_view(repo_root):
    return parse_file(repo_root / "tests" / "fixtures" / "sql" / "ddl_minima.sql").view


@pytest.fixture
def with_view(published, fixture_view, view_metadata):
    data = copy.deepcopy(published)
    data[fixture_view.ref] = view_metadata(fixture_view)
    return data


def test_matching_view_has_no_differences(ddl, with_view, fixture_view):
    assert compare(ddl.dataset, ddl.tables, _show(with_view), view=fixture_view) == []


def test_each_kind_of_view_difference_is_reported(ddl, with_view, fixture_view):
    body = with_view[fixture_view.ref]
    body["type"] = "TABLE"
    body["view"]["useLegacySql"] = True
    body["description"] = "otra"
    fields = body["schema"]["fields"]
    fields[1]["type"] = "STRING"  # CANTIDAD
    fields[2]["description"] = "otra"  # ANIO
    fields[2]["mode"] = "REQUIRED"  # the mode is not compared
    fields.append({"name": "EXTRA", "type": "STRING"})
    diffs = compare(ddl.dataset, ddl.tables, _show(with_view), view=fixture_view)
    assert {d.chequeo for d in diffs} == {"esquema_ddl"}
    assert _details(diffs) == {
        ("v_ejemplo", "tipo de objeto"),
        ("v_ejemplo", "dialecto de la vista"),
        ("v_ejemplo", "descripción de la vista"),
        ("v_ejemplo.CANTIDAD", "tipo"),
        ("v_ejemplo.ANIO", "descripción"),
        ("v_ejemplo.EXTRA", "columna"),
    }


def test_view_column_in_another_position(ddl, with_view, fixture_view):
    fields = with_view[fixture_view.ref]["schema"]["fields"]
    fields[0], fields[1] = fields[1], fields[0]
    diffs = compare(ddl.dataset, ddl.tables, _show(with_view), view=fixture_view)
    assert ("v_ejemplo.ID", "nombre en la posición 1") in _details(diffs)


def test_missing_view(ddl, with_view, fixture_view):
    show = _show(with_view, {fixture_view.ref: "Not found: Table ejemplo:v_ejemplo"})
    diffs = compare(ddl.dataset, ddl.tables, show, view=fixture_view)
    assert [d.detalle for d in diffs] == ["Falta ejemplo.v_ejemplo: ejecuta 'make bq-vista'"]
    assert missing_objects(diffs)


def test_without_view_spec_the_view_is_not_read(ddl, published):
    seen = []

    def show(ref):
        seen.append(ref)
        return bq.BqResult(0, json.dumps(published[ref]), "")

    assert compare(ddl.dataset, ddl.tables, show) == []
    assert all("v_" not in ref for ref in seen)


def test_object_exists(with_view, fixture_view):
    assert object_exists(fixture_view.ref, _show(with_view)) is True
    missing = _show(with_view, {fixture_view.ref: "Not found: Table"})
    assert object_exists(fixture_view.ref, missing) is False
    denied = _show(with_view, {fixture_view.ref: "Access Denied"})
    with pytest.raises(MetadataError, match="Access Denied"):
        object_exists(fixture_view.ref, denied)
