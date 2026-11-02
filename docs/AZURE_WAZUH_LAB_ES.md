# Laboratorio Wazuh en Azure: revisión previa

Estado: **no desplegado; simulaciones y parada automática no activadas**.

## Diseño propuesto

- Grupo exclusivo `rg-aegislake-lab`, separado de los recursos del máster.
- Ubuntu 22.04: servidor Wazuh (4 vCPU, mínimo 8 GiB, 64 GiB) y endpoint Linux (1–2 vCPU, 32 GiB).
- Comprobación del 2 de noviembre de 2026: Standard_D4ds_v4 (Wazuh) y Standard_D2_v4 (endpoint) figuran disponibles en Spain Central. Cuota total: 6 vCPU; cuota de cada familia: 4 vCPU, sin uso observado. Las familias B aparecen restringidas. La asignación efectiva sigue pendiente de despliegue.
- Sin IP pública ni entrada de administración desde Internet. Acceso de operación mediante Azure Run Command; puertos 1514/1515 limitados al endpoint.
- Instalar desde los repositorios oficiales de Wazuh. Mantener credenciales locales protegidas; no publicarlas en salidas, logs de CI ni GitHub.
- La salida a Internet requiere una decisión explícita de red en las API actuales. No asumir conectividad implícita.

## Validación de crédito

La sesión de Azure y Cloud Shell se comprobaron mediante consultas de lectura.
Se verificó que la suscripción activa está vinculada al perfil de facturación que contiene crédito de Azure for students. El nombre del plan es Microsoft Azure Plan: buscar únicamente 'student' en quotaId no acredita ni descarta este crédito.

Consulta autorizada, sin persistir ni imprimir tokens:

`GET {billingProfileId}/providers/Microsoft.Consumption/credits/balanceSummary?api-version=2023-05-01`

El control debe usar `properties.balanceSummary.estimatedBalanceInBillingCurrency`, exigir EUR y comparar el saldo estimado, no el importe original ni el saldo cerrado antes de cargos pendientes.
Los identificadores de cuenta, saldo personal y credenciales se conservan fuera del repositorio público.

## Estimación regional previa

La API pública de tarifas consultada el 2 de noviembre de 2026 devuelve Linux Consumption en Spain Central: D4ds_v4 = 0,2262 EUR/h; D2_v4 = 0,0961 EUR/h. Total de cómputo: 0,3223 EUR/h, aproximadamente 7,74 EUR/día. Es una estimación de tarifa pública, sin discos, operaciones, red, impuestos ni otras cargas. La duración del laboratorio será de pocos días con el margen de crédito disponible, no un despliegue mensual permanente. Verificar también los costes residuales y el precio efectivo antes de activar.

[API oficial de tarifas](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)

## Parada y permisos que se deben revisar antes de activar

Identidad administrada de Azure Automation, sin secretos compartidos:

1. Lectura del saldo de crédito en el perfil de facturación pertinente; no conceder edición de facturación.
2. Rol personalizado limitado a leer y desasignar las dos VMs del grupo exclusivo. Acciones previstas: `Microsoft.Compute/virtualMachines/read`, `Microsoft.Compute/virtualMachines/instanceView/read`, `Microsoft.Compute/virtualMachines/deallocate/action`. Sin ejecutar comandos, crear recursos ni modificar IAM.
3. Comprobación independiente cada hora. La desasignación del endpoint precede a la del servidor Wazuh. Confirmar los estados finales y registrar cualquier fallo.
4. Fallo de lectura, moneda no válida, fecha límite o saldo insuficiente => detener, sin continuar simulaciones.
5. Umbral conservador: **10 EUR + máximo coste horario × retraso de facturación + reserva para discos retenidos**. El precio y la reserva deben calcularse con tarifas regionales verificadas antes de activar.
6. Fecha límite independiente, inicialmente no superior a siete días; no ampliarla sin volver a comprobar crédito y costes.

`scripts/lab_budget_policy.py` implementa únicamente la decisión y dispone de regresiones. **No es todavía un servicio de parada ni realiza escrituras de Azure.**

Los presupuestos de Azure no detienen consumo por sí solos. La facturación tiene retraso y los discos siguen generando coste después de desasignar. No prometer una parada exactamente en 10 EUR ni mantener VMs indefinidamente con una simple alerta.
No borrar discos ni evidencias automáticamente; reservar su coste y planificar retirada después de exportar y revisar evidencias.

## Actividad y utilidad

Ejecutar el primer escenario manualmente y repetir cada **48 horas** después de probar todo el circuito.

- Actividad normal: procesos y cambios en ficheros de prueba.
- Actividad sospechosa controlada: fallos de autenticación sobre cuentas exclusivas del laboratorio, intentos de sudo denegados y cambios de integridad en una ruta de prueba.
- Sin malware, explotación, tráfico a terceros, robo de credenciales ni cambios de protección.
- Generar eventos mediante operaciones del sistema; no presentar líneas fabricadas con logger como ataques reales.
- Registrar ground truth (escenario, UTC, host, operación, resultado y expectativa) aparte de los logs observados.
- Medir detección por escenario, tiempo de llegada, duplicados, falsos positivos durante ventanas normales y calidad de la correlación. Distinguir eventos del SO reales de actividad adversaria real.
- Probar primero Wazuh y su agente; después verificar el adaptador y el dashboard AegisLake. Su esquema de identidad actual no equivale a todos los eventos de host de Wazuh.
- No mostrar precision/recall sobre logs sin etiquetas. Conservar artefactos privados y publicar solamente estadísticas revisadas.

## Criterios de aceptación pendientes

- Precio regional completo, tamaños disponibles, cuota y vista previa de infraestructura.
- Permisos exactos revisados; lectura del crédito usando la identidad del guard.
- Prueba real de desasignación con reserva amplia y confirmación de ambos estados.
- Wazuh operativo; agente conectado; log real recibido y alerta correlacionada.
- Escenario etiquetado visible en AegisLake.
- Solo entonces activar recurrencia y anunciar el laboratorio como operativo.

## Fuentes primarias

- [Wazuh Quickstart](https://documentation.wazuh.com/current/quickstart.html)
- [API de saldo de créditos](https://learn.microsoft.com/en-us/rest/api/consumption/credits/get?view=rest-consumption-2023-05-01)
- [Datos y retraso de costes](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data)
- [Presupuestos](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)
- [Identidad de Azure Automation](https://learn.microsoft.com/en-us/azure/automation/enable-managed-identity-for-automation)
- [Conectividad saliente](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access)
