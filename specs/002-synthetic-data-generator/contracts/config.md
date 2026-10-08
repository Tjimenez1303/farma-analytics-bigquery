# Contrato: `generator/config.toml`

Archivo TOML 1.0 leído con `tomllib`. Es la única fuente de la semilla y de los parámetros
(FR-005). Los valores de abajo son los finales tras el ajuste de T043 (research R11). Cualquier cambio posterior exige actualizar
`generator/manifest.json` en el mismo PR.

```toml
# Root seed, 128-bit hex string (TOML integers are limited to 64 bits).
seed = "0x..."

[periodo]
inicio = 2024-01-01
fin = 2025-12-31
solo_dias_laborables = true

[volumen]
lineas_compra = 300000
unidades_medicas = 2000
fabricantes_innovadores = 12
fabricantes_genericos = 28
proveedores = 60
genericos_por_molecula = [1, 4]
proveedores_por_fabricante = [1, 3]
piezas_max = 50000

[huerfanos]
orphan_rate = 0.005
proporcion_clue = 0.5

[concentracion]
alpha_moleculas = 0.9
moleculas_destacadas = { "Insulina glargina" = 2, "Atorvastatina" = 4, "Clopidogrel" = 6 }
beta_entidades = 1.0
participacion_institucion = { "IMSS" = 0.42, "IMSS-Bienestar" = 0.18, "ISSSTE" = 0.15, "Servicios Estatales de Salud" = 0.12, "SEDENA" = 0.06, "SEMAR" = 0.04, "PEMEX" = 0.03 }
reparto_nivel = { "Primer nivel" = 0.70, "Segundo nivel" = 0.25, "Tercer nivel" = 0.05 }
peso_compra_nivel = { "Primer nivel" = 1.0, "Segundo nivel" = 4.0, "Tercer nivel" = 12.0 }

[estacionalidad]
factores_mes = [1.25, 1.15, 1.10, 1.00, 0.95, 0.95, 0.90, 0.95, 1.00, 0.95, 0.90, 0.90]
crecimiento_total = 0.06

[precios]
nivel = { bajo = [15.0, 100.0], medio = [100.0, 600.0], alto = [600.0, 2500.0], muy_alto = [2500.0, 9000.0] }
factor_referencia = [1.40, 1.80]
factor_generico = [0.50, 0.80]
ruido_max = 0.10
piezas_lognormal = { mu = 4.5, sigma = 1.2 }

[patrones.p3]
molecula_ejemplo = "Clopidogrel"
prob_referencia = { "PEMEX" = 0.75, "SEMAR" = 0.70, "SEDENA" = 0.65, "ISSSTE" = 0.40, "Servicios Estatales de Salud" = 0.35, "IMSS-Bienestar" = 0.25, "IMSS" = 0.20 }

[patrones.p4]
factor_2025 = { "Oncología" = 1.30 }
factor_2025_resto = 1.05

[patrones.p5]
moleculas = ["Atorvastatina", "Insulina glargina"]
cuota_generico_inicial = 0.15
cuota_generico_final = 0.32
```

## Reglas de validación

La generación termina con código 2 sin escribir nada si alguna falla. El mensaje nombra la ruta
del parámetro (por ejemplo `huerfanos.orphan_rate`), el valor y el rango válido.

| Parámetro | Regla |
|---|---|
| `seed` | Texto hexadecimal con prefijo `0x`, de 1 a 128 bits. |
| `periodo.inicio`, `periodo.fin` | Fechas TOML. `inicio` es 1 de enero, `fin` es 31 de diciembre y cubren al menos dos años calendario completos (FR-018). |
| `volumen.*` | Enteros positivos. `lineas_compra` entre 1 000 y 2 000 000. Los rangos `[min, max]` cumplen `1 <= min <= max`. `genericos_por_molecula[1]` no supera `fabricantes_genericos`. |
| `huerfanos.orphan_rate` | Real en `[0, 0.05]`. |
| `huerfanos.proporcion_clue` | Real en `[0, 1]`. |
| `concentracion.participacion_institucion` | Las siete instituciones de `reference/instituciones.csv`, valores en `(0, 1)` que suman 1 con tolerancia de 1e-9. |
| `concentracion.moleculas_destacadas` | Moléculas que existen en `reference/moleculas.csv`, con rangos enteros únicos entre 1 y el número de moléculas. Deben incluir `patrones.p3.molecula_ejemplo` y todas las de `patrones.p5.moleculas`. |
| `concentracion.reparto_nivel`, `peso_compra_nivel` | Los tres niveles. El reparto suma 1 y los pesos son positivos. |
| `estacionalidad.factores_mes` | Doce reales positivos. |
| `estacionalidad.crecimiento_total` | Real en `(-0.5, 1)`. |
| `precios.nivel` | Los cuatro niveles de `reference/moleculas.csv`, cada uno con `0 < min < max`. |
| `precios.factor_referencia`, `factor_generico` | `0 < min <= max`, y el máximo genérico no supera el mínimo de referencia. |
| `precios.ruido_max` | Real en `[0, 0.5)`. |
| `patrones.p3.molecula_ejemplo` | Molécula que existe, con al menos un genérico autorizado, y que no está en `patrones.p5.moleculas`. |
| `patrones.p3.prob_referencia` | Las siete instituciones, valores en `[0, 1]`. |
| `patrones.p4.factor_2025` | Grupos que existen en `reference/moleculas.csv`, factores positivos. |
| `patrones.p5.moleculas` | Moléculas que existen y tienen al menos un genérico autorizado. Cuotas en `[0, 1]` con la inicial menor que la final. |
| Claves desconocidas | Error: una errata no puede pasar desapercibida. |
