# Dashboards nativos dentro de AegisLake

La sección **Dashboards** calcula gráficos interactivos sobre las ventanas de alerta de una ejecución.
Comparte la navegación con Overview y MITRE ATT&CK; no incrusta capturas, iframes, Power BI o Grafana.
No requiere CDN, licencia de BI, API key ni servicios cloud adicionales.

## Abrir la interfaz conectada

```sh
python -m pip install -e '.[dev]'
aegislake demo --seed 7 --output runs
aegislake serve --runs runs --port 8767
```

Abre <http://127.0.0.1:8767/dashboard.html>. El servidor se enlaza exclusivamente a loopback.
Solo expone los informes permitidos y una API de lectura; no publica bronze, silver, Parquet, modelos,
credenciales ni listados del sistema de archivos. No implementa autenticación multiusuario y no debe
exponerse a Internet mediante túneles o proxies. La implantación cloud sigue siendo un trabajo separado.

## Exploración enlazada

- **Actividad temporal:** selecciona una barra para fijar las fechas UTC. Los intervalos extensos
  se agrupan en un máximo de 40 barras; el gráfico indica el tamaño de cada intervalo.
- **Hipótesis ATT&CK:** selecciona una técnica o el grupo sin mapeo curado. Las hipótesis de una misma
  ventana pueden solaparse; sus recuentos no se suman para obtener un total de incidentes.
- **Mapa horario:** selecciona una combinación de día de la semana y hora UTC, agregada entre semanas.
- **Identidades:** selecciona una identidad exacta de las ocho con más ventanas en el filtro actual.
- **Puntuaciones:** selecciona un intervalo de ranking. Los scores no son probabilidades ni severidades.
- Los controles de fecha, búsqueda, técnica y puntuación mínima afectan a todos los gráficos, KPIs
  y a la cola paginada. **Clear filters** elimina también las selecciones hechas en los gráficos.

Los KPIs cuentan ventanas en la cola y entidades distintas, no todas las autenticaciones ni ataques
confirmados. El pico diario pertenece a la selección actual. La precisión y el recall, cuando existen,
se muestran aparte como contexto de la evaluación etiquetada completa y no se recalculan con filtros.

## Datos nuevos y SOC/SIEM

El selector **Batch** cambia entre ejecuciones completas. La interfaz puede consultar cada 30 segundos
el catálogo local y seguir el lote más reciente. Es actualización de lotes, no streaming de eventos.
Puede pausarse y refrescarse manualmente. Si falla la API, conserva los últimos datos cargados y muestra
el estado de error; no genera valores nuevos ni borra la evidencia anterior.

El comando existente `score` genera ahora Overview, MITRE, `dashboard.html`, `dashboard.json` y los
mapeos en el directorio de salida. El archivo `scoring.json` se escribe al final como marcador de
finalización. El explorador ignora directorios `.partial` y lotes sin un marcador de finalización.

```sh
# Utiliza datos autorizados y una referencia entrenada/validada para tu dominio.
aegislake score --reference runs/REFERENCE --input data/future.jsonl --output runs/batch-2026-11-01
aegislake serve --runs runs
```

Las entradas deben cumplir el contrato canónico; para exportaciones locales de Microsoft Graph existe
`adapt-entra`, que seudonimiza identificadores mediante una clave local. Esta entrega no establece una
conexión activa con un tenant, Sentinel, Elastic o Splunk y no extrae telemetría de cuentas reales.
Los lotes sin etiquetas carecen de precisión/recall y la procedencia de su fuente debe revisarse.
El uso de una referencia sintética para datos nuevos continúa requiriendo `--allow-domain-shift`;
ese permiso no valida su eficacia operativa.

## Modo sin servidor e importación

Cada ejecución incluye un `dashboard.html` autónomo con su snapshot embebido. Puede abrirse desde
disco o desde el informe, con el mismo comportamiento de filtros y gráficos. No consulta la API.

**Open dashboard JSON** abre otro `dashboard.json` dentro del navegador. El archivo no se sube al
servidor y la actualización de API queda pausada. **Refresh now** recupera el lote seleccionado de la
API local. La procedencia de un archivo importado es declarada por ese archivo, no certificada.
Se rechazan versiones desconocidas, IDs duplicados, scores inválidos y archivos de más de 20 MiB
o 20 000 alertas. El contenido se inserta como texto y no como HTML ejecutable.

**Export selection** prepara una descarga y un panel con el JSON copiable de las filas que cumplen los filtros, sin limitarse a la página
de la cola. Incluye los criterios de selección y omite métricas globales de eficacia para que no se
confundan con resultados medidos sobre ese subconjunto. Puede volver a importarse.

## API y límites

| Ruta | Resultado |
| --- | --- |
| `GET /api/runs` | Catálogo de lotes completos y claves opacas; sin rutas del equipo |
| `GET /api/runs/{key}/dashboard` | Snapshot versionado `aegislake.dashboard.v1` |
| `GET /report.html?run={key}` | Overview del lote seleccionado |
| `GET /mitre.html?run={key}` | Mapa y mapeos del mismo lote |

Las respuestas usan `no-store`; no se habilita CORS. Se rechazan Host y Origin ajenos al servidor
local. Los identificadores de API no se convierten en rutas arbitrarias. Esto limita el alcance del
explorador local; no sustituye un backend autenticado apto para producción.

La versión 0.2.0 cambia el identificador de las nuevas evaluaciones. Regenera las referencias con esa
versión; el control de integridad sigue rechazando referencias creadas con otra versión del código.

Fuentes de diseño y límites:
[Python HTTP server](https://docs.python.org/3/library/http.server.html),
[Microsoft Sentinel Workbooks](https://learn.microsoft.com/en-us/azure/sentinel/monitor-your-data) y
[Azure Monitor: informes interactivos](https://learn.microsoft.com/en-us/azure/azure-monitor/visualize/workbooks-interactive-reports).
Los Workbooks son una alternativa dentro de Azure; no se presentan aquí como una integración desplegada.
