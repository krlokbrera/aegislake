# Verificación del frontend

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
