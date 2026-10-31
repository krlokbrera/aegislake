# Verificación del frontend

## Dashboards 0.2.0

La nueva sección Dashboards utiliza las filas de `dashboard.json` tanto en HTML autónomo como en la
interfaz conectada a la API local. La revisión de navegador comprobó filtros enlazados por técnica
y fecha, selección de día/hora UTC, bins de puntuación, paginación, búsquedas vacías, conservación
de filtros al refrescar y selección exacta de identidad desde el gráfico.

Se probó además la detección de un lote nuevo de scoring: la API lo incorporó sin reiniciar y
la interfaz mostró sus 23 alertas sin precisión o recall. Los datos de esa prueba son una continuación
sintética, no telemetría de un SOC real. La importación válida se procesó dentro del navegador con la
actualización de API pausada; cinco entradas inválidas se rechazaron mediante el validador JavaScript.

La suite local completa pasa 61 pruebas con 90 % de cobertura Python. Incluye peticiones HTTP reales,
aislamiento de rutas y orígenes, descubrimiento de nuevos lotes y regresión del pipeline de scoring.
El panel copiable de exportación se comprobó en navegador: al filtrar T1078 produce cinco filas,
todas con esa hipótesis y sin métricas globales heredadas. La navegación MITRE → cola conserva
la clave del lote y el filtro de técnica. En un marco de 390 px el documento tiene 375 px útiles y
375 px de contenido, sin desbordamiento horizontal; el filtro T1078 y el panel de exportación
funcionan también dentro de ese marco. El gestor de descargas del navegador no se da por verificado;
el JSON copiable permite inspeccionar y recuperar la selección. Las comprobaciones móviles descritas
abajo corresponden a Overview/MITRE de la entrega anterior. Consulta [la guía de dashboards](DASHBOARDS_ES.md).

## Overview y MITRE de la entrega anterior

El informe offline utiliza dos páginas: `report.html` para métricas e investigación y `mitre.html`
para técnicas, tácticas candidatas y el traspaso de evaluación a DeTT&CT. Los archivos descargables
`attack-mapping.json` y `dettect-techniques.yaml` deben conservarse junto a las páginas.

## Comportamiento comprobado en navegador

- Búsqueda por identidad: la muestra seed-7 devuelve cuatro ventanas para employee-0043.
- Búsqueda sin coincidencias: estado vacío y paginación desactivada.
- Paginación: ocho alertas por página, con segunda página 9–16 de 146.
- Filtro T1078: cinco ventanas, todas con esa hipótesis.
- Orden temporal descendente y evidencias desplegables.
- Selección de técnica en MITRE y navegación a la cola filtrada correspondiente.
- Marco móvil de 390 px: ambas páginas sin desbordamiento horizontal del documento.
- Contenido y estilos integrados sin CDN, fuentes externas, analítica o peticiones de datos.

Las pruebas unitarias comprueban escape de HTML, preservación de métricas, recuentos por ventana,
estados vacíos, conservación de técnicas desconocidas y estructura del YAML. La integración
comprueba manifiestos y la publicación de todos los archivos enlazados antes del marcador cloud.

La muestra publicada se regenera con puntuaciones completas; no depende de la extracción de tarjetas
HTML utilizada para la primera revisión local. Los resultados describen datos sintéticos.

Consulta [el registro de ejecución](VALIDATION_STATUS.md) para los resultados medidos de CI y
[la guía DeTT&CT](DETTCT_ES.md) para el significado de las exportaciones y puntuaciones iniciales.
