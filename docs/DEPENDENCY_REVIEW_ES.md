# Revisión de Dependabot — 31 de octubre de 2026

Se integran conjuntamente seis actualizaciones para comprobar su combinación sobre el código de
dashboards actual, conservando los SHA completos de las Actions. La versión del código pasa a 0.2.1;
las referencias de scoring de versiones anteriores deben regenerarse, como exige el control existente.
No cambia el protocolo de entrenamiento, las reglas, los umbrales ni el presupuesto de revisión.

La primera validación conjunta detectó `Pandas4Warning` dentro de la conversión `fetchdf()` de DuckDB.
La salida SQL se transfiere ahora mediante `con.sql(...).to_arrow_table().to_pandas()`, una interfaz
relacional documentada desde DuckDB 1.4. Una regresión adicional trata los avisos como errores y
comprueba ventanas UTC, etiquetas desconocidas y MFA ausente en la conversión. Las variables de modelo
se normalizan a float64 para que los decimales de Arrow no entren como objetos en NumPy.
Se fija además la sesión SQL en UTC: el horario fuera de oficina no debe depender de la zona de la
máquina. Otra regresión inicia la conexión en Europe/Madrid y comprueba el límite de las 07:00 UTC.
No se silencian avisos y se conserva la consulta de agregación y sus reglas.

| PR original | Propuesta | Resolución |
| --- | --- | --- |
| [#2](https://github.com/krlokbrera/aegislake/pull/2) | checkout 7.0.1 | Aplicada con SHA `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| [#4](https://github.com/krlokbrera/aegislake/pull/4) | setup-python 7.1.0 | Aplicada con SHA `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` |
| [#5](https://github.com/krlokbrera/aegislake/pull/5) | upload-artifact 7.0.2 | Aplicada con SHA `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| [#6](https://github.com/krlokbrera/aegislake/pull/6) | pandas 3.1.0 | Rango ampliado a `>=2.2,<4`; validación conjunta en CI |
| [#7](https://github.com/krlokbrera/aegislake/pull/7) | DuckDB 2.0.0 | Rango ampliado a `>=1.4,<3`; validación conjunta en CI |
| [#8](https://github.com/krlokbrera/aegislake/pull/8) | PyArrow 26.0.0 | Rango ampliado a `>=21,<27`; validación conjunta en CI |
| [#3](https://github.com/krlokbrera/aegislake/pull/3) | Python 3.15-slim | Rechazada para este alcance: incumple `requires-python >=3.11,<3.14` y falla la instalación del contenedor |

La [CI de compatibilidad conjunta](https://github.com/krlokbrera/aegislake/actions/runs/41230660587)
verificó 63 pruebas en Python 3.11 y 3.12, con 90 % de cobertura, Ruff correcto y ninguna vulnerabilidad
conocida detectada por pip-audit en ambos entornos. Las pruebas ya no emiten el aviso de pandas.
También pasaron la generación de la demo sintética, la compilación de Bicep, la construcción de Docker
y la ejecución del contenedor como usuario sin privilegios, sin iniciar sesión ni desplegar en Azure.

| Entorno CI | DuckDB | pandas | PyArrow | NumPy | scikit-learn |
| --- | --- | --- | --- | --- | --- |
| Python 3.11 | 2.0.0 | 3.1.0 | 26.0.0 | 2.4.6 | 1.9.1 |
| Python 3.12 | 2.0.0 | 3.1.0 | 26.0.0 | 2.5.4 | 1.9.1 |

Son versiones observadas en los logs, no inferidas de los rangos. El artefacto de la demo de Python 3.12
incluye su registro completo `environment.txt`. El entorno local de referencia también pasó Ruff y
las 63 pruebas; no se presenta como la misma combinación de dependencias que la CI.

Los PR originales se cierran como sustituidos por el cambio conjunto después de su integración;
no se presentan como siete merges individuales. El PR de Azure pendiente queda fuera de esta revisión.

## Conservación de evidencia

Los archivos `requirements-verified-py311-windows.txt` y `requirements-verified-py312-linux.txt` documentan
ejecuciones anteriores, no son lockfiles vivos. Dependabot proponía cambiar también esos pines, sin
repetir la ejecución que describen. Se conservan sus versiones originales y se excluyen esos archivos
del escaneo de actualizaciones; `pyproject.toml` continúa monitorizado, igual que las Actions y Docker.
Las auditorías de la CI siguen comprobando el entorno instalado en cada ejecución.

La muestra de `examples/demo` y su manifiesto pertenecen a la entrega 0.2.0. Se conservan juntos;
no se reetiquetan sus métricas como resultados de 0.2.1. Para producir una muestra con la combinación
nueva, genera una ejecución con el código 0.2.1 y conserva su `environment.txt` y manifiesto.

## Política de Docker

Se mantiene el tag `python:3.12-slim` fijado por digest. Dependabot puede seguir proponiendo actualizaciones
de esa línea, incluidas actualizaciones del digest. Las versiones desde 3.13 se reservan para migraciones
explícitas del contenedor con su propia comprobación de compatibilidad; esto no cambia el rango Python
declarado del paquete ni desactiva la monitorización de la imagen actual.

## Fuentes primarias revisadas

- [checkout 7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1)
- [setup-python 7.1.0](https://github.com/actions/setup-python/releases/tag/v7.1.0)
- [upload-artifact 7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2)
- [pandas 3.1.0](https://pandas.pydata.org/docs/whatsnew/v3.1.0.html)
- [DuckDB 2.0.0 y cambios de API](https://github.com/duckdb/duckdb-python/releases/tag/v2.0.0)
- [API relacional de DuckDB 1.4](https://duckdb.org/docs/1.4/clients/python/reference/)
- [Apache Arrow 26.0.0](https://arrow.apache.org/release/26.0.0.html)
- [Opciones de Dependabot: exclusiones y rangos](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
- [Fallo de instalación con Python 3.15](https://github.com/krlokbrera/aegislake/actions/runs/41215900094)
