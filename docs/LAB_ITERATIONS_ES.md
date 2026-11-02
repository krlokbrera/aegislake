# Ciclo de pruebas, análisis y PRs

El generador ejecuta el ejercicio acotado solo después de 48 horas y con el
ciclo anterior revisado. Wazuh, el agente y el guardián de crédito mantienen
sus funciones mientras una nueva simulación está bloqueada.

## Secuencia

| Momento | Trabajo | Condición de cierre |
|---|---|---|
| Día de la ejecución | Guardar lote, sellar archivo, reconciliar y comparar | Evidencia completa o fallo explícito; análisis y PRs justificadas |
| Día natural siguiente, Madrid | Revisar, corregir y validar las PRs | CI y revisión del último SHA; replay privado y servicios sanos |
| Antes de la siguiente prueba | Comprobar versión y habilitación | Mínimo 48 h, archivos íntegros y revisión vigente |

Las tareas de análisis, revisión y cierre comprueban diariamente si hay trabajo.
No generan ejercicios adicionales. La revisión se asigna a la fecha real de
ejecución, no a la fecha de creación de una PR. Un cierre atrasado queda
registrado como tal. Si no hay una mejora respaldada por evidencia, se registra
esa conclusión y se revisa la versión existente sin crear PRs vacías.

Las mejoras quedan como **PRs abiertas**, sin merge automático. El laboratorio
puede probar el commit exacto de una PR después de su revisión y validación.
La validación offline y la salud se comprueban antes del siguiente ejercicio;
sus resultados no sustituyen la observación del siguiente ciclo.

## Almacenamiento privado

Cada ejecución conserva sus originales en
`/var/lib/aegislake/runs/activity-*/`. Un archivo independiente del lote queda en
`/var/lib/aegislake/archives/<run_id>/`:

- `batch.tar.gz`: solo ground truth, resumen, alertas, eventos adaptados,
  calidad y datos bronze/silver del lote.
- `manifest.json`: SHA-256 del archivo y de cada miembro, fecha real de
  ejecución, fecha de revisión y estado completo/parcial.
- `analysis.json`: reconciliación inicial; el análisis programado estudia
  causas y comparación con otros ciclos.
- `review.json`: evidencia de revisión, replay, CI, salud y versión desplegada.

Las carpetas de archivos son 0700 y los archivos 0600. No se incluyen claves,
credenciales ni logs del instalador. Se rechazan symlinks. No se extrae el
contenido del tar sobre el sistema de archivos al comprobar su integridad.

**Estos archivos están en el disco administrado de la VM: no son copias externas.**
Persisten al desasignar, siguen generando coste y deben exportarse de forma
privada antes de borrar el disco. No se han creado recursos facturables nuevos.

Los ciclos nuevos registran commit, huellas de código/configuración y versiones
de paquetes antes de actuar. Los lotes anteriores sin ese registro se marcan
como procedencia no registrada en el momento de la ejecución; no se atribuye
retrospectivamente un commit al que no hay evidencia.

## Control de la siguiente prueba

`scripts/lab_cycle.py` comprueba:

1. El último intento corresponde a un archivo verificado.
2. Hay análisis y revisión desde el día natural siguiente a la ejecución.
3. El manifiesto y el análisis conservan las huellas revisadas.
4. El código y la configuración desplegados conservan sus huellas.
5. El HEAD actual de la PR y un workflow CI completado con éxito coinciden
   con el commit desplegado.

Un push posterior, una modificación local o de configuración, un archivo
alterado, un fallo de API o un registro incompleto vuelven a bloquear la prueba.
La habilitación queda vinculada a un ciclo y una versión. Una ejecución nueva,
incluso fallida, necesita su propio cierre y no reutiliza la revisión anterior.
El parámetro `--force` del generador anterior ya no está disponible.

El guardián de gasto es independiente. Este control no puede arrancar VMs
detenidas por presupuesto ni sustituye la comprobación del crédito.

## Instalación en el manager existente

`scripts/install_lab_cycle.py` usa los permisos de operador ya autorizados.
Valida el HEAD de la PR y su CI antes de aplicar. Su destino es únicamente
`aegis-wazuh`; no crea recursos, roles ni accesos de red. Mantiene el generador
deshabilitado si falla la instalación.

```bash
python scripts/install_lab_cycle.py \
  --subscription "$AEGIS_SUBSCRIPTION" \
  --commit "$AEGIS_VALIDATED_COMMIT" --pr-number 15 \
  --ci-run-id "$AEGIS_SUCCESSFUL_CI_RUN" --apply
```

El código se obtiene en `/opt/aegislake-cycle`, fijado al commit comprobado.
Esta mejora utiliza el entorno Python existente: no añade dependencias.
Si una futura PR cambia dependencias, debe validar también el entorno real
y registrar sus versiones antes de habilitar la prueba.

El instalador conserva el servicio anterior como respaldo, archiva los lotes
existentes y cambia solo la ruta del generador. El temporizador sigue comprobando
cada hora; el generador conserva el mínimo de 48 h y el control de revisión.

## Comandos del revisor

Ejecutar como operador en el manager, con el mismo bloqueo que el generador:

```bash
PYTHON=/opt/aegislake/.venv/bin/python
CYCLE=/opt/aegislake-cycle/scripts/lab_cycle.py
$PYTHON $CYCLE seal --run-id activity-20261102T124343Z
$PYTHON $CYCLE analyze --run-id activity-20261102T124343Z
$PYTHON $CYCLE gate
# Solo después de completar las comprobaciones y llegar el día de revisión:
$PYTHON $CYCLE approve --run-id activity-20261102T124343Z \
  --validation-file /var/lib/aegislake/evidence/validation-candidate.json
```

El archivo privado de validación debe contener `commit`, `pr_number`,
`ci_run_id`, `offline_validation_passed: true`, `services_healthy: true`,
`review_complete: true` y una `rationale` concreta. No se deben marcar esos
campos para eludir un bloqueo. La revisión del ciclo base del 2/11/2026 vence
el 3/11/2026; aprobarlo el día de su ejecución se rechaza.

El registro `/var/lib/aegislake/evidence/iteration-state.json` comunica el estado
entre tareas. Un plan o una tarea programada no acredita un archivo guardado,
una PR creada, CI correcto o una versión desplegada: cada paso requiere prueba
de su resultado. Si falta la conexión de operador o GitHub rechaza escritura,
se registra BLOQUEADO y se comunica el paso pendiente; no se salta el control.
