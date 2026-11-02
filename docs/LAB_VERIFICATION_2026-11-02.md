# Verificación del laboratorio — 2/11/2026

Se ejecutó en Azure, con Ubuntu y Wazuh instalados en dos VMs propias.
Los logs proceden de operaciones controladas de SSH y del sistema de archivos;
no son logs de una organización en producción ni de un atacante externo.

## Resultados observados

Ejercicio completo: `activity-20261102T124343Z`, 12:43 UTC.
La evidencia detallada queda privada en el manager.

| Comprobación | Resultado |
|---|---|
| Sesiones SSH autorizadas | 2 de 2 completadas |
| Usuarios inexistentes | 8 conexiones rechazadas |
| Cambio del archivo monitorizado | Completado; alerta FIM 550 recibida |
| Alertas nativas exportadas | 18 |
| Autenticaciones adaptadas | 10: 2 válidas, 8 fallidas |
| Registros del adaptador | 0 malformados, 0 duplicados; 8 alertas no SSH ignoradas |
| Ingesta bronze/silver | 10 aceptados, 0 rechazados, 0 duplicados |
| Identidades y orígenes seudonimizados | 9 usuarios, 1 origen |
| Agente Wazuh después del reinicio | Active |
| Manager, indexador y dashboard | active |
| Temporizador de actividad | active; intervalo mínimo de 48 h |

El primer timestamp de alerta quedó aproximadamente 1,85 s después del inicio
del ejercicio. Es una observación de esa muestra, no una medida general de
latencia de extremo a extremo ni un SLA. El recolector esperó 45 segundos
después de las operaciones antes de crear el resumen.

Las reglas observadas fueron:

| Regla Wazuh | Cantidad | Significado de la regla |
|---|---:|---|
| 5715 | 1 | Autenticación SSH válida |
| 5710 | 7 | Usuario inexistente |
| 5712 | 1 | Correlación de intentos repetidos con usuarios inexistentes |
| 40112 | 1 | Fallos de autenticación seguidos de éxito |
| 550 | 1 | Cambio de checksum de un archivo |
| 5501 | 4 | Apertura de sesión PAM |
| 5502 | 3 | Cierre de sesión PAM |

Las descripciones de reglas no acreditan por sí mismas un ataque.
Las correlaciones explican por qué una sesión puede representarse mediante
una regla distinta de la alerta base. Los diez eventos SSH de esta muestra
coincidieron con los resultados del ejercicio tras la adaptación.

## Identidad y control de gasto

La identidad administrada leyó correctamente el crédito en EUR y las VMs del
grupo del laboratorio. Una consulta de VMs fuera de ese grupo devolvió 403.

Se activó temporalmente la condición de ensayo `ForceStop` del guardián.
La ejecución terminó en Succeeded; las acciones BudgetStopEndpoint y
BudgetStopWazuh también terminaron en Succeeded. Se verificó después el estado
real de ambas VMs: `PowerState/deallocated`.

Se restauró `ForceStop=false`, con guardián habilitado, revisión horaria,
umbral de 46,96 EUR y fecha límite 5/2/2027 UTC. Una ejecución sana validó
el crédito y entró en WithinBudget. El operador volvió a arrancar las VMs;
la identidad del guardián no tiene permisos de arranque.

Después se comprobaron `PowerState/running`, los servicios Wazuh activos,
el agente conectado y la persistencia del temporizador. La prueba del guardián
y su cronología se conservaron en
`/var/lib/aegislake/evidence/control-drill.json`.

La rama de crédito ilegible está cubierta por pruebas de estructura y contrato;
no se provocó un fallo real de la API de crédito en este ensayo. La prueba
física de desasignación utilizó la condición de ensayo explícita.

## Incidencias corregidas antes de la entrega

- El keyring público del repositorio APT de Wazuh necesitaba lectura para APT.
  Se corrigieron sus permisos y se mantuvo la verificación de firma.
- El usuario restringido podía autenticarse, pero no atravesar el directorio del
  archivo FIM. Se limitó el permiso de recorrido al grupo de ese usuario.
  El ejercicio completo posterior confirmó el cambio y la alerta.
- La primera muestra parcial se conserva por separado; las cifras de arriba
  corresponden únicamente al ejercicio completo posterior.

## Alcance de la validación

La cadena comprobada es actividad → logs Ubuntu → agente → reglas/correlación
Wazuh → adaptación HMAC → bronze/silver Parquet. Los logs, claves HMAC y
credenciales se conservan privados. El repositorio contiene código y recuentos.

El laboratorio permite revisar si los escenarios esperados se observan y si
la ingesta pierde información. Todavía no establece precisión, recall, tasas
de falsos positivos de una organización, rendimiento sostenido, ni mejora
de los modelos ML frente a un SIEM. No se ha entrenado un modelo con estos
diez eventos ni se han extrapolado los resultados sintéticos anteriores.

Las pruebas automáticas del código se pueden consultar en los
[checks de la PR](https://github.com/krlokbrera/aegislake/pull/14/checks).
Las simulaciones posteriores necesitan nuevas evidencias; esta prueba inicial
no debe presentarse como una verificación de una fecha futura.
