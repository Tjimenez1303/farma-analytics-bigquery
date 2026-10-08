"""Expected values from the manifest and the generator configuration."""

from decimal import Decimal

from warehouse.expectations import CONFIG_PATH, as_bq_parameters, load_expectations


def test_current_values():
    expectations = load_expectations()
    values = {name: (p.type, p.value) for name, p in expectations.items()}
    assert values == {
        "filas_compras": ("INT64", "300000"),
        "filas_clue_cat": ("INT64", "2000"),
        "filas_cuadro_basico": ("INT64", "161"),
        "huerfanos_clue": ("INT64", "750"),
        "huerfanos_clave": ("INT64", "750"),
        "fecha_inicio": ("DATE", "2024-01-01"),
        "fecha_fin": ("DATE", "2025-12-31"),
        "precio_minimo": ("NUMERIC", "6.75"),
        "precio_maximo": ("NUMERIC", "17820"),
        "dispersion_maxima": ("NUMERIC", "4.4"),
    }


def test_bq_parameters_only_for_requested_names():
    expectations = load_expectations()
    assert as_bq_parameters(expectations, ["filas_compras", "fecha_inicio", "precio_minimo"]) == [
        "--parameter=filas_compras:INT64:300000",
        "--parameter=fecha_inicio:DATE:2024-01-01",
        "--parameter=precio_minimo:NUMERIC:6.75",
    ]
    assert as_bq_parameters(expectations, []) == []


def test_thresholds_follow_the_configuration(tmp_path):
    config = tmp_path / "config.toml"
    text = CONFIG_PATH.read_text(encoding="utf-8")
    assert "ruido_max = 0.10" in text
    config.write_text(text.replace("ruido_max = 0.10", "ruido_max = 0.20"), encoding="utf-8")
    expectations = load_expectations(config_path=config)
    # 15 x 0.5 x 0.8, 9000 x 1.8 x 1.2 and (1.8 x 1.2) / (0.5 x 0.8).
    assert Decimal(expectations["precio_minimo"].value) == Decimal(6)
    assert Decimal(expectations["precio_maximo"].value) == Decimal(19440)
    assert Decimal(expectations["dispersion_maxima"].value) == Decimal("5.4")


def test_dispersion_is_rounded_up(tmp_path):
    config = tmp_path / "config.toml"
    text = CONFIG_PATH.read_text(encoding="utf-8")
    config.write_text(text.replace("ruido_max = 0.10", "ruido_max = 0.07"), encoding="utf-8")
    value = Decimal(load_expectations(config_path=config)["dispersion_maxima"].value)
    exact = Decimal("1.8") * Decimal("1.07") / (Decimal("0.5") * Decimal("0.93"))
    assert value >= exact
    assert value - exact < Decimal("0.000001")
    assert value == value.quantize(Decimal("0.000001"))
