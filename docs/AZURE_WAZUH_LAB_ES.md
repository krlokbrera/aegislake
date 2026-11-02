# Laboratorio Azure + Wazuh

Estado: desplegado el 2 de noviembre de 2026. Este laboratorio produce actividad
controlada en sistemas propios y recoge logs nativos de Ubuntu mediante Wazuh.
No demuestra detección de atacantes reales ni precisión de modelos en producción.

## Recursos desplegados

| Recurso | Configuración |
|---|---|
| `aegis-wazuh` | Poland Central, B4als_v2, 4 vCPU / 8 GiB, SSD 64 GiB |
| `aegis-endpoint` | Poland Central, B2ats_v2, 2 vCPU / 1 GiB, SSD 32 GiB, swap 2 GiB |
| Sistema | Ubuntu 24.04, imagen fijada, Trusted Launch, Secure Boot, vTPM |
| SIEM | Wazuh 4.14.9, servidor/indexador/dashboard y agente |
| Red | 10.77.0.0/24; IPs privadas .4 y .5; sin IP pública |
| Control | Logic App horaria en Spain Central con identidad administrada propia |

La NSG permite agente → Wazuh TCP 1514/1515 y Wazuh → endpoint TCP 22.
El resto de entrada está denegado. La salida predeterminada está habilitada
explícitamente para paquetes y actualizaciones; no hay NAT Gateway ni Bastion.
El dashboard Wazuh permanece privado. Las VMs no tienen identidad de facturación.

Azure Automation se descartó porque las ubicaciones admitidas por esta oferta
de estudiante no coincidían con la política regional de la suscripción.
La Logic App usa una identidad administrada de usuario y autenticación ARM,
sin contraseñas, claves de servicio ni tokens persistentes.

## Permisos verificados

`mi-aegislake-creditguard` tiene:

- Lector del perfil de facturación asociado al crédito.
- Un rol propio, limitado a `rg-aegislake-lab`, con lectura de VMs,
  lectura de su estado y `virtualMachines/deallocate/action`.

No puede arrancar VMs, ejecutar comandos, borrar recursos ni administrar roles.
La prueba con esa identidad pudo leer crédito y VMs del laboratorio; leer VMs
de otro grupo devolvió HTTP 403. Los identificadores de cuenta, saldos,
credenciales Wazuh y claves SSH no forman parte del repositorio.

## Actividad y evidencias

`scripts/install_lab_activity.py` instala un usuario sin privilegios y una clave
SSH dedicada. La clave solo admite una orden forzada, desde la IP del manager,
sin forwarding. La clave de host se obtiene mediante Azure Run Command y queda
fijada; nunca se desactiva su comprobación.

Cada ejercicio realiza dos sesiones autorizadas, ocho conexiones con usuarios
inexistentes y un cambio en el archivo monitorizado. Son operaciones acotadas,
sin malware, explotación, escaneo de terceros ni escritura de falsos incidentes.
El endpoint también ejecuta una actividad inocua cada quince minutos.

Un temporizador comprueba cada hora si han transcurrido al menos 48 horas desde
el último intento. Reiniciar la VM no elude ese intervalo. Si falla un ejercicio
también se registra su hora para evitar bucles de reintentos. No se reactiva
automáticamente una VM detenida por el control de crédito.

En el manager:

- `/var/lib/aegislake/runs/activity-*/ground-truth.json`: operaciones y resultados.
- `summary.json`: recuentos de reglas, sesiones y calidad del adaptador.
- `wazuh-alerts.ndjson`: alertas nativas privadas.
- `auth-events.ndjson`: eventos SSH seudonimizados para AegisLake.
- `/etc/aegislake/pseudonym.key`: clave HMAC privada, modo 0600.

El adaptador `python -m aegislake.wazuh` conserva MFA y país como desconocidos,
y las etiquetas como ausentes. Los eventos FIM se analizan en Wazuh, no se
convierten en autenticaciones. Las alertas de correlación con el mismo log se
deduplican. La cantidad de sesiones no tiene por qué coincidir con la cantidad
de alertas: Wazuh aplica filtros y correlaciones propios. No se calculan
precision/recall con esta muestra sin un protocolo de etiquetado adecuado.

## Presupuesto y parada

La Logic App consulta el crédito cada hora. Comprueba que el saldo estimado sea
numérico, no negativo y en EUR. Si no puede leerlo o validarlo, solicita la
desasignación de ambas VMs. Hace lo mismo al alcanzar el umbral o la fecha límite.

Para esta ejecución:

```text
umbral = 10 EUR de reserva
       + 0,18 EUR/h × 72 h de posible retraso de facturación
       + 24 EUR para discos retenidos hasta el vencimiento del crédito
       = 46,96 EUR
```

Este umbral conservador detiene el cómputo antes de ver 10 EUR en el portal.
No promete detenerse exactamente en 10 EUR: el dato de consumo llega con retraso,
hay gastos ajenos al laboratorio y desasignar no elimina discos. La reserva para
discos no es un gasto ya realizado ni una tarifa de Azure.

Las tarifas públicas Linux consultadas el 2/11/2026 sumaban aproximadamente
3,53 EUR/día de cómputo, más unos 6,46 EUR/mes de discos, operaciones y otros
consumos. Son referencias, no una cotización de la factura particular.
No se ha activado una ampliación de crédito ni una actualización a pago por uso.

La fecha límite final es el 5/2/2027 UTC, anterior al vencimiento del crédito.
Los discos y las evidencias se conservan al detener las VMs. Su exportación
y posterior eliminación deben completarse antes de que venza la reserva;
el rol del guardián no tiene permisos de borrado.

## Reproducir

Usar Azure CLI autenticada con los permisos expresamente aprobados. Revisar
cuotas, disponibilidad regional, políticas y precios de la cuenta antes de aplicar.

```bash
python scripts/create_lab_identity.py --help
# Usar --standalone, el perfil correcto y --apply solo en la cuenta autorizada.
python scripts/deploy_lab_guard.py --help
# Desplegar/verificar el guardián ANTES de crear cómputo facturable.
ssh-keygen -t ed25519 -f /tmp/aegis-operator-key -N ''
python scripts/lab_parameters.py \
  --ssh-public-key /tmp/aegis-operator-key.pub \
  --output /tmp/aegis-lab-parameters.json
az bicep build --file infra/lab.bicep
az deployment group what-if -g rg-aegislake-lab \
  --template-file infra/lab.bicep --parameters @/tmp/aegis-lab-parameters.json
az deployment group create -g rg-aegislake-lab -n aegislake-wazuh-lab \
  --template-file infra/lab.bicep --parameters @/tmp/aegis-lab-parameters.json
# Esperar bootstrap.ok y comprobar servicios y agent_control -l en el manager.
python scripts/install_lab_activity.py --subscription "$AEGIS_SUBSCRIPTION"
```

El estado privado de la identidad se escribe en `/tmp`; guardarlo en un destino
privado persistente si se necesita otro día. Las claves de administración,
contraseñas del instalador y logs de bootstrap deben permanecer privados.
No publicar el archivo de credenciales generado por el instalador Wazuh.

Para consultar el ejercicio desde Cloud Shell o una terminal autorizada:

```bash
az vm run-command invoke -g rg-aegislake-lab -n aegis-wazuh \
  --command-id RunShellScript --scripts \
  'systemctl is-active aegis-activity.timer; find /var/lib/aegislake/runs -name summary.json -exec cat {} \;'
```

Las operaciones de Run Command pertenecen al operador, no a la identidad del
guardián. Mantener acceso privado al dashboard; cualquier acceso web posterior
requiere una conexión privada autorizada y no abrir 443 a Internet.

## Validación

La suite comprueba el contrato del adaptador, la política de reserva, el alcance
de las peticiones de parada, el manejo de errores, la cadencia y la conservación
de los heredocs en cloud-init. CI compila ambas plantillas Bicep, valida los
scripts Bash, ejecuta Python 3.11/3.12, audita dependencias y prueba el contenedor
sin privilegios. Las comprobaciones de CI no despliegan recursos Azure.

Las pruebas funcionales del laboratorio y la parada real se documentan en
`LAB_VERIFICATION_2026-11-02.md`. Una prueba de laboratorio no valida la
utilidad del producto frente a toda la actividad de una organización.

## Fuentes oficiales

- [Wazuh quickstart y requisitos](https://documentation.wazuh.com/current/quickstart.html)
- [Créditos: Balance Summary](https://learn.microsoft.com/en-us/rest/api/consumption/credits/balance-summary?view=rest-consumption-2023-05-01)
- [Logic Apps e identidades administradas](https://learn.microsoft.com/en-us/azure/logic-apps/authenticate-with-managed-identity)
- [Precios públicos de Azure](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)
- [Estados y facturación de VMs](https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing)
