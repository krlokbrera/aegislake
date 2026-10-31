# Mapeo SOC/SIEM con ATT&CK y DeTT&CT

AegisLake relaciona sus señales de identidad con dos técnicas: **T1110.003 Password Spraying** y
**T1078 Valid Accounts**. Cada técnica contiene sus tácticas candidatas con identificador y nombre,
los campos necesarios y la referencia oficial. El catálogo vive en `src/aegislake/attack.py` y se
reutiliza en las alertas de evaluación, las de scoring de lotes nuevos y el informe visual.

| Técnica | Tácticas asociadas en el catálogo consultado | Señal implementada |
| --- | --- | --- |
| T1110.003 | TA0006 Credential Access | Fanout de al menos 8 identidades por fuente y tasa de fallos de al menos 50 % |
| T1078 | TA0001 Initial Access; TA0003 Persistence; TA0004 Privilege Escalation; TA0005 Stealth | Al menos 4 destinos por identidad en una ventana cerrada de 15 minutos |

Las tácticas son pertenencias del catálogo: una alerta con T1078 **no demuestra** que hayan ocurrido
persistencia, elevación de privilegios o todos los objetivos asociados. El fanout por sí solo tampoco
demuestra movimiento lateral; por eso no se añade una táctica de movimiento lateral a esa señal.

La semántica de la señal y sus falsos positivos posibles están visibles en la página MITRE. La página
muestra una selección de identidad de cinco columnas, no una medida de cobertura de toda la matriz.
Los nombres se comprobaron el **31 de octubre de 2026**; TA0005 aparece como Stealth en las fuentes
consultadas. Las versiones antiguas pueden mostrar Defense Evasion. El catálogo no se actualiza en red.

## Qué aporta DeTT&CT

DeTT&CT es un proyecto de Rabobank CDC que utiliza ATT&CK para administrar fuentes de datos, visibilidad
y capacidad de detección. No es un clasificador de alertas y su puntuación no equivale al score de ML.
Una técnica puede generar muchas alertas de simulación y seguir careciendo de evidencia de cobertura
operativa en una organización.

Cada ejecución de evaluación genera dos archivos adicionales, enlazados desde `mitre.html`:

- `attack-mapping.json`: evidencia por identificador de alerta, técnica, tácticas candidatas y campos
  canónicos requeridos. No duplica nombres de usuarios o direcciones de origen. Conserva técnicas
  desconocidas como no mapeadas. Cuenta cada ventana una vez por técnica; los recuentos pueden solaparse.
- `dettect-techniques.yaml`: plantilla de administración de técnicas v1.2 para una implantación SOC aún
  no evaluada. Se utiliza `file_type: technique-administration`, según el ejemplo oficial del proyecto.

El YAML conserva **detección -1** (ninguna detección desplegada registrada) y **visibilidad 0** (ninguna
visibilidad operativa registrada). Son valores iniciales conservadores de una plantilla sin evaluación,
no una afirmación de que tu SOC real carezca de controles. No se inventa una fecha de despliegue, una
ubicación de regla SIEM ni una puntuación positiva. Antes de utilizarla operativamente, el responsable
debe editar el ámbito, plataformas, fuentes y calidad de datos, localización de las reglas, comentarios
y logbook de puntuaciones con evidencia de su entorno.

El alcance `Unassessed SOC deployment (AegisLake candidate)` mantiene esa plantilla separada de una
evaluación de activos reales. `platform: all` es un valor de compatibilidad de la plantilla: no acredita
que el detector funcione en todas las plataformas. Debe ajustarse antes de generar una capa operacional.

## Flujo de uso

1. Ejecuta `aegislake demo --output runs` o una evaluación sobre datos etiquetados autorizados.
2. En `mitre.html`, selecciona una técnica, lee su regla y revisa las alertas enlazadas.
3. Descarga el YAML y el JSON. Los archivos también están en el directorio de la ejecución.
4. Abre el YAML en el editor de DeTT&CT y sustituye la plantilla por una evaluación documentada del SOC.
5. Con una instalación de DeTT&CT revisada y compatible con la versión de ATT&CK utilizada, genera sus
   capas para Navigator. Ejemplo del CLI oficial: `python dettect.py d -ft dettect-techniques.yaml -l`.
6. Versiona la evaluación y conserva evidencia de pruebas de reglas y de la calidad de los datos.

Mientras el YAML mantenga los valores iniciales -1/0, la visualización de cobertura de DeTT&CT no debe
interpretarse como un heatmap de detecciones acreditadas. El informe AegisLake muestra volumen de
hipótesis; DeTT&CT administra capacidad evaluada. No se convierten entre sí mediante una fórmula.

La exportación se contrasta con el ejemplo oficial de administración y se comprueba con un parser YAML.
Esto valida estructura y semántica propia, no la ejecución completa del CLI externo ni la eficacia en
un SIEM real. No se añaden credenciales o conectores de un SOC ni se envían datos a servicios externos.

## Fuentes primarias

- [DeTT&CT: repositorio y propósito](https://github.com/rabobank-cdc/DeTTECT)
- [Administración de técnicas](https://github.com/rabobank-cdc/DeTTECT/wiki/YAML-administration-techniques)
- [Ejemplo oficial v1.2](https://github.com/rabobank-cdc/DeTTECT/blob/master/sample-data/techniques-administration-endpoints.yaml)
- [Puntuación de detección](https://github.com/rabobank-cdc/DeTTECT/wiki/Detection-scoring)
- [Puntuación de visibilidad](https://github.com/rabobank-cdc/DeTTECT/wiki/Visibility-scoring)
- [MITRE: Password Spraying](https://attack.mitre.org/techniques/T1110/003/)
- [MITRE: Valid Accounts](https://attack.mitre.org/techniques/T1078/)
- [MITRE: tácticas Enterprise](https://attack.mitre.org/tactics/enterprise/)
