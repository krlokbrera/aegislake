# Guía de uso y configuración

## Qué vas a poder enseñar

Una demostración de principio a fin: generar eventos, validar su calidad, construir un lago de datos pequeño, calcular variables con SQL, evaluar modelos con una separación temporal y revisar una cola de alertas. El interés del proyecto está en poder justificar las decisiones de datos y de evaluación.

No necesita una API de modelos generativos ni una suscripción a Sentinel para ejecutar la demo. La IA aplicada es aprendizaje automático para detección y priorización. Azure es una extensión opcional y finita del mismo paquete.

## Instalación en Windows

Abre PowerShell en la carpeta del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install ".[dev]"
aegislake demo --output runs
```

Si tu equipo bloquea la activación por su política de ejecución, invoca directamente `.venv\Scripts\python.exe` y `.venv\Scripts\aegislake.exe`. No es necesario cambiar la política del equipo.

El último comando muestra la ruta del resultado. Abre `report.html`. En `report.json` están las métricas exactas; no copies cifras de una captura antigua si has cambiado la semilla, las dependencias o el conjunto de datos.

## Recorrido de cinco minutos

1. Explica qué problema resuelve: priorizar identidades sospechosas con una capacidad limitada de revisión.
2. Muestra la reconciliación: entradas = aceptadas + duplicadas + rechazadas.
3. Abre las tres particiones de variables y sus fechas, para demostrar que el futuro no entra en el entrenamiento.
4. Compara el modelo elegido con las reglas. Un resultado inferior también es un resultado útil.
5. Abre una alerta y conecta cada explicación con una variable observable.
6. Registra `needs_context` o `false_positive` con la CLI; enseña que el sistema no bloquea cuentas.

## Configuración reproducible

| Parámetro | Valor por defecto | Consecuencia |
| --- | --- | --- |
| days | 30 | Horizonte del simulador |
| users | 50 | Número de identidades humanas simuladas |
| seed | 42 | Aleatoriedad repetible |
| train-days | 18 | Periodo para referencia y entrenamiento |
| validation-days | 6 | Periodo para umbrales y selección |
| capacity | 25 | Máximo de ventanas por día en la cola |
| Ventana SQL | 15 minutos | Se modifica en código, con nueva versión y pruebas |
| Horario de demo | 07:00–20:00 UTC | Convención pedagógica; no calendario laboral de España |

Ejemplo alternativo:

```powershell
aegislake demo --days 45 --users 80 --seed 7 --train-days 27 --validation-days 9 --capacity 40 --output runs
```

No compares estos resultados con los valores por defecto sin describir el cambio de prevalencia, volumen, periodo y capacidad.

## Reejecución y errores

El identificador de ejecución depende del hash del archivo y la configuración. Una ejecución completa se reutiliza si sus artefactos conservan sus hashes. Una ejecución incompleta termina en `.partial` y no se presenta como válida. Inspecciona ese directorio antes de retirarlo o usa otro directorio de salida para reintentar.

La implementación no soporta varios escritores sobre el mismo directorio. Para ejecutar experimentos concurrentes, usa carpetas diferentes. Los hashes permiten comprobar integridad frente al manifiesto local; no son una firma ni prueban quién produjo el archivo.

## Exportaciones de Microsoft Entra

El adaptador recibe un archivo JSON local, con una lista de eventos o un objeto Graph con `value`. No descarga registros ni solicita permisos de tu tenant.

La clave de seudonimización se configura solo en tu sesión local mediante `AEGIS_PSEUDONYM_KEY`. Debe tener al menos 32 bytes y mantenerse estable si necesitas enlazar lotes. Genera una clave aleatoria y consérvala en un gestor de secretos; no la pegues en GitHub, capturas o incidencias. El código no imprime la clave.

Usuarios, fuentes, recursos e identificadores de evento se convierten en HMAC con espacios de nombres separados. La fecha y el país permanecen para el análisis. La seudonimización no convierte automáticamente el conjunto en datos anónimos.

La propiedad de política `authenticationRequirement` no se interpreta como prueba de MFA completado. Si faltan los detalles del paso, el adaptador registra MFA desconocido y las variables lo distinguen de MFA ausente observado.

Los datos reales se puntúan sin etiquetas. Eso no produce precision, recall ni una validación de efectividad. Los resultados del simulador no se transfieren como una garantía a tu tenant.

## Revisión humana

```powershell
aegislake review --run runs/RUN_ID --alert-id ALERT_ID --decision needs_context --reviewer analyst-01 --note "Pendiente de contrastar con cambio aprobado"
```

Las decisiones válidas son `true_positive`, `false_positive` y `needs_context`. Usa alias y notas sin información sensible. La aplicación añade filas a SQLite; un usuario con acceso al archivo puede modificarlo. No se presenta como un registro inmutable con valor forense.

Las decisiones no se convierten automáticamente en etiquetas de entrenamiento: harían falta una política de adjudicación, revisión de casos dudosos y una nueva evaluación temporal.

## Lectura de resultados

- AP resume el ranking precision–recall; no es la accuracy ni exactamente el área trapezoidal bajo esa curva.
- Precision indica la proporción de ventanas positivas entre las seleccionadas.
- Recall indica qué parte de las ventanas positivas se revisaría.
- Los falsos positivos por mil ventanas benignas ayudan a visualizar la carga.
- La matriz de confusión utiliza la cola final, después del límite diario.
- La capacidad está medida en ventanas de usuario, no en incidentes ni campañas.

La selección diaria se realiza al terminar el lote: no se promete respuesta inmediata a cada evento. Un atacante puede repartir actividad entre ventanas; esa limitación está documentada.
