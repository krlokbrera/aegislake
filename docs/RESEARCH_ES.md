# Investigación y justificación de AegisLake

Fecha de revisión: 31 de octubre de 2026. Fuentes primarias al final. Las decisiones de arquitectura, prioridades y estimaciones de esfuerzo son propuestas originales para este proyecto; no son conclusiones atribuidas a los proveedores.

## 1. Objetivo profesional

El proyecto debe demostrar que puedes convertir un problema de ciberseguridad en un producto de datos evaluable. Tu experiencia en ingeniería de datos y consultoría de ciberseguridad permite explicar tanto la construcción del pipeline como el uso de sus resultados por un analista.

La evidencia útil para un proceso de selección no es solo un algoritmo: también incluye un contrato de datos, calidad, trazabilidad, SQL legible, una evaluación que evite el uso del futuro, decisiones cloud razonadas y una demostración reproducible.

El nombre AegisLake resume el caso: un lago de eventos de identidad con modelos de priorización. No se plantea como sustituto de una plataforma comercial de identidad, EDR o SIEM.

## 2. Alternativas estudiadas

| Caso | Qué demostraría | Principal dificultad | Encaje en esta entrega |
| --- | --- | --- | --- |
| Clasificador de correos de phishing | NLP y clasificación supervisada | Datasets repetidos, contaminación y escasa ingeniería de datos si se limita a un notebook | Útil como segundo proyecto |
| Priorización de vulnerabilidades | Integración de fuentes y scoring de exposición | El impacto depende de inventario, contexto y etiquetas que no suelen estar disponibles | Buen proyecto posterior |
| Copiloto de SOC con recuperación documental | Recuperación y evaluación de respuestas | Puede terminar en una interfaz sobre un modelo sin una evaluación convincente | No es el núcleo elegido |
| Detección de tráfico de red | Extracción de características y ML | Datasets desactualizados, escenarios fáciles y poca transferencia al entorno objetivo | Posible benchmark complementario |
| Analítica de identidades | Pipelines, SQL, series temporales, anomalías y revisión | Etiquetas incompletas, VPN/NAT, calidad de MFA y contexto de usuario | Caso elegido |

Esta comparación es una valoración de diseño. La elección no implica que los otros casos sean menos importantes en un SOC.

## 3. Caso de uso y amenaza

MITRE describe el password spraying como intentos sobre múltiples cuentas utilizando una contraseña o una lista reducida. Eso inspira la variable de identidades por fuente y ventana, combinada con la tasa de fallos [S1].

MITRE también recoge el abuso de cuentas válidas [S2]. En AegisLake, acceder a varios destinos o a recursos nuevos genera una hipótesis de investigación. Esos patrones no prueban compromiso: un administrador, una migración o una tarea automática pueden producirlos.

La salida está dirigida a revisión humana. No existe un permiso para bloquear usuarios, resetear contraseñas o ejecutar una respuesta en endpoints.

El alcance es autenticación y acceso a recursos. Quedan fuera robo de tokens sin cambios de patrón, abuso de aplicaciones sin usuario, contexto de dispositivo real y correlación con incidentes. El simulador contiene además un acceso malicioso deliberadamente parecido a uno benigno para hacer visible esta limitación.

## 4. Pregunta analítica

La pregunta elegida es: ¿qué método identifica más ventanas sospechosas útiles dentro de una capacidad diaria de revisión?

La unidad de análisis es una identidad en una ventana cerrada de quince minutos. Esa unidad permite relacionar una agregación SQL con una decisión operativa concreta. No se debe presentar el número de ventanas como número de incidentes o de atacantes.

La capacidad por defecto es una configuración de la demo. No representa la dotación de un SOC real ni una recomendación universal.

## 5. Datos: realismo y límites

La demo utiliza un generador propio para que cualquiera pueda ejecutarla sin permisos sobre un tenant o datos de una empresa. El generador produce actividad rutinaria, fallos legítimos, lotes de servicio y escenarios maliciosos superpuestos.

Las etiquetas del simulador provienen de su lógica de generación. Por tanto, los resultados pueden estar favorecidos por la estructura del generador. Se documenta esa dependencia y se impide describir los resultados como una validación de detección empresarial.

Como benchmark futuro se ha estudiado LANL: contiene 58 días de eventos de varias fuentes, autenticación y referencias de actividad red team. La autenticación ocupa unos 7,2 GB comprimidos. La fuente publica una renuncia a derechos y pide citar sus datos y trabajo asociado [S3]. Su época relativa y entorno no equivalen a Entra actual; la ausencia de una marca red team tampoco garantiza una etiqueta benigna.

No se descarga el conjunto por defecto. Antes de incorporarlo harían falta un adaptador por bloques, una prueba del enlace de etiquetas y un plan de muestreo que no elimine las campañas.

Para interoperabilidad se incluye un adaptador local de exportaciones Graph. La documentación de Microsoft distingue resultado, identidad, dirección IP, recurso y campos de riesgo [S4]. Estos últimos no se usan como verdad terreno: reproducir la etiqueta de otro detector sería una evaluación diferente de detectar incidentes.

El acceso a los logs de Graph puede depender de licencias y permisos del tenant [S4]. Los créditos de Azure no se tratan como garantía de disponer de esas licencias. La demo sigue funcionando sin ellas.

## 6. Ingeniería de datos

Se aplica una estructura bronze/silver/gold como organización del proyecto:

- Bronze conserva el archivo de entrada de la ejecución.
- Silver contiene eventos validados en Parquet, particionados por fecha UTC.
- Gold contiene variables, alertas y resultados.
- La cuarentena guarda referencias de línea y motivos acotados de rechazo.

Parquet y DuckDB permiten separar almacenamiento columnar y consulta SQL. DuckDB documenta lectura y escritura de Parquet y consulta directa sobre estos archivos [S5]. Elegir este motor aquí responde a reproducibilidad y simplicidad; no se afirma una ventaja de rendimiento sin un benchmark.

Cada línea tiene una disposición reconciliable. Se diferencia la repetición exacta de un identificador del conflicto de contenido bajo ese identificador. El conflicto conserva el primer evento aceptado y rechaza la versión posterior; una solución empresarial necesitaría reconciliarlo con el sistema origen.

Los manifiestos registran hashes, configuración y versiones. El directorio de salida se publica al completarse el lote. Esto ofrece trazabilidad local y facilita repetir experimentos, pero no sustituye un catálogo empresarial, un registro firmado o transacciones distribuidas.

La implementación actual mantiene los datos aceptados en memoria. La evolución hacia Spark, almacenamiento incremental o streaming debe justificarse con un volumen medido y probar equivalencia de resultados.

## 7. Tiempo y fuga de información

La documentación de scikit-learn advierte que ajustar transformaciones con datos que pertenecen a la evaluación puede producir estimaciones optimistas [S6]. Esta advertencia se traduce en tres decisiones del proyecto:

1. Separar por fechas, en lugar de mezclar eventos del futuro y del pasado.
2. Aprender escalado y referencia de anomalías únicamente en entrenamiento.
3. Usar validación para umbrales y selección, reservando test para informar resultados.

Las ventanas se puntúan una vez cerradas. El fanout de una fuente puede usar todos sus eventos de la ventana porque la decisión ocurre al final. Sería incorrecto reutilizarlo para afirmar detección en tiempo real en el primer evento de esa ventana.

La referencia de destinos conocidos permanece fija tras entrenamiento. Eso impide que un destino futuro se convierta retrospectivamente en conocido para la evaluación. En las filas de entrenamiento, la referencia es retrospectiva dentro de su propio periodo; no se presenta como un feature store causal online.

No se modelan llegada tardía, watermarks o datos ausentes al cerrar una ventana. Un piloto online debe definirlos y repetir un replay con tiempo de disponibilidad, además de tiempo del evento.

## 8. Variables y mecanismos de confusión

El volumen y los fallos ayudan a identificar cambios de patrón, pero también responden a incidencias legítimas. El número de destinos puede crecer durante trabajo administrativo. Compartir una IP puede ser normal detrás de NAT o de un proxy.

La falta de MFA exige un tratamiento especial: ausencia observada y evidencia desconocida no son equivalentes. El adaptador mantiene null cuando no puede observar un paso y calcula una variable separada de desconocimiento. No considera que una política que requiere MFA pruebe que ese factor se completó.

La variable horaria utiliza UTC para la demo. Aplicarla sin adaptación a empleados en distintos husos horarios podría introducir falsos positivos sistemáticos. Por eso la tarjeta de modelo exige revisar calendario, rol y localización antes de un uso real.

No se usan nombres de escenario, identificadores o etiquetas como predictores. Evitar esas columnas es necesario, aunque no elimina por sí mismo las correlaciones artificiales del simulador.

## 9. Métodos comparados

Las reglas son una referencia interpretable y barata de mantener. Permiten comprobar si un algoritmo aporta algo más que combinar volumen, fanout y fallos.

Isolation Forest aporta una señal de anomalía. Su documentación explica que el aislamiento de observaciones se utiliza para construir puntuaciones de anomalía [S7]. En este proyecto, esa señal se transforma a un percentil empírico frente al entrenamiento. Un evento raro puede ser legítimo; percentil alto no significa probabilidad alta de ataque.

La regresión logística ofrece una referencia supervisada sencilla. Se usa escalado aprendido sobre entrenamiento y pesos de clase. Su salida se trata como ranking; no se afirma calibración de probabilidades.

El híbrido combina un 60% de percentil de anomalía y un 40% de reglas. Los pesos son una decisión fija de la primera versión, no una optimización probada ni una recomendación general.

El campeón se decide por F1 de validación bajo capacidad. Esa función puede cambiar si el coste relativo de omisiones y falsos positivos se concreta; el cambio debe aprobarse como una decisión de producto y evaluarse sin reutilizar test para ajustarlo.

## 10. Métricas operativas

Average precision es la métrica principal de ranking. scikit-learn define AP como una suma ponderada sobre el incremento de recall, diferenciada de la integración trapezoidal [S8]. En datos desbalanceados, resulta útil mostrarla junto a la prevalencia.

Precision, recall y F1 se calculan sobre la cola final, después de aplicar el límite diario. Se muestran también falsos positivos por mil ventanas benignas, volumen total y máximo diario.

Un umbral que cumple la capacidad en validación puede incumplirla en un periodo posterior. Por eso el proyecto aplica además un límite duro por día al lote de prueba. Esta decisión protege el presupuesto de revisión a costa de poder omitir una amenaza desplazada por otras puntuaciones.

Una clase ausente no se oculta con un número arbitrario: ROC AUC puede ser null y la calibración exige ambas clases. Las estimaciones de incertidumbre y la evaluación por campaña están pendientes.

Una evaluación más sólida debería añadir folds temporales, varios generadores y entornos, una separación por campaña o tenant y adjudicación independiente de las etiquetas.

## 11. Explicación y supervisión

Las explicaciones son plantillas que describen señales observadas. No se presentan como explicación causal del modelo. Una alerta puede mostrar múltiples destinos, fanout elevado, MFA ausente o actividad fuera de la convención horaria.

Las etiquetas ATT&CK son hipótesis para organizar una investigación. El analista debe contrastar contexto, cambios aprobados y otros registros.

La revisión se guarda en SQLite con decisiones acotadas. La aplicación añade filas, pero el archivo no es inmutable. Esta distinción permite discutir la diferencia entre una funcionalidad de colaboración y un registro con requisitos forenses.

Como orientación de gobernanza, NIST AI RMF organiza actividades en Govern, Map, Measure y Manage [S9]. La documentación del proyecto usa esas ideas para separar propósito, medición, responsables y gestión de limitaciones; no declara una certificación.

## 12. Seguridad del propio sistema

Un modelo de ciberseguridad también puede abrir una superficie de ataque. Se aplican consultas fijas, escape de HTML, seudonimización con clave y una lista de artefactos publicables.

Scikit-learn documenta riesgos de ejecución de código al cargar ciertos formatos basados en pickle [S10]. La versión actual reconstruye modelos pequeños desde datos de entrenamiento y un entorno coincidente. Esto evita ese mecanismo de deserialización a costa de tiempo de arranque.

Los hashes detectan cambios respecto a un manifiesto de confianza; no firman al autor. Una futura cadena de suministro debería incorporar procedencia de builds, firma de artefactos y una política de confianza.

Las dependencias están acotadas por versiones mayores y se auditan en CI. Todavía debe generarse un lock exacto revisado tras la primera ejecución correcta. No se confunde una restricción de versión con reproducibilidad exacta.

## 13. Azure y créditos de estudiante

Microsoft documenta Azure for Students como una oferta de crédito de 100 USD válido durante un año, sujeto a sus condiciones y elegibilidad [S11]. Eso describe la oferta, no confirma saldo, vigencia o servicios disponibles en tu cuenta.

La arquitectura mínima crea almacenamiento y permisos sobre un contenedor. El cómputo es opcional y manual. Container Apps Jobs permite tareas finitas [S12]; encaja con generar la demo y publicar informes antes de que desaparezca el disco efímero.

La facturación de Container Apps depende del plan y del consumo [S13]. Se propone Consumption por la naturaleza intermitente de la demo. El ahorro esperado debe comprobarse frente a los recursos ya usados por la suscripción y a los cargos de almacenamiento, operaciones y red.

La autenticación a Blob se hace mediante Entra y las bibliotecas oficiales [S14]. La identidad del job recibe un rol acotado al contenedor de informes. No se almacenan claves compartidas ni credenciales de Azure en el repositorio.

La red de almacenamiento se cierra a una IP explícita en el modo local. El modo de job usa el endpoint público autenticado por la limitación de egress de este diseño mínimo; no convierte el contenedor en público. Una implantación más sensible requiere revisar conectividad privada.

## 14. Control de gasto

Se separa el cálculo de recursos de una cotización monetaria. Treinta ejecuciones de cinco minutos a 0,5 vCPU y 1 GiB equivalen a 4.500 vCPU-segundos y 9.000 GiB-segundos. El precio se obtiene introduciendo tarifas regionales vigentes en el script de costes.

No se afirma que ese consumo sea gratuito: existen consumos compartidos, condiciones, almacenamiento y otros conceptos. La documentación de facturación debe revisarse al desplegar.

Los presupuestos generan alertas y pueden integrarse con automatizaciones de control; no se consideran por sí solos un apagado del sistema [S15]. Esta versión no crea destinatarios de correo ni automatizaciones sin configuración explícita.

El job tiene un límite de duración y cero reintentos por defecto. Lanzar repetidamente ejecuciones manuales todavía puede generar coste. La política de retención se limita a informes sintéticos.

## 15. CI/CD y revisión

La primera CI debe ejecutar pruebas, lint, auditoría de dependencias, demo, compilación Bicep y construcción del contenedor. Los resultados deben inspeccionarse; definir un workflow no equivale a haberlo superado.

Las PRs tienen que describir problema, comportamiento resultante y evidencia real. Las tareas sin acceso cloud deben quedar identificadas, sin atribuirles un estado de despliegue.

GitHub documenta OIDC para evitar credenciales cloud duraderas [S16]. En una evolución de CI/CD, la confianza debe restringirse a repositorio, entorno y condiciones concretas. La documentación consultada incluye cambios recientes del formato de subject para repositorios nuevos: debe verificarse el claim real, sin copiar plantillas antiguas.

La versión inicial mantiene CI sin credenciales de cloud. El despliegue es una operación separada con sesión Azure del usuario y comprobación de oferta de estudiante.

## 16. Plan de evolución

| Etapa | Entrega concreta | Prueba para aceptarla |
| --- | --- | --- |
| Verificación inicial | Ejecutar la versión y generar resultados | CI observada y demo inspeccionada |
| Piloto de datos autorizados | Adaptador, minimización y etiquetas adjudicadas | Contrato, calidad y trazabilidad de la muestra |
| Evaluación robusta | Folds temporales, incertidumbre y métricas por campaña | Protocolo congelado antes del test |
| Operación batch | Planificación, entrega fiable y observabilidad | Fallos y reintentos inyectados |
| Escala | Portar cómputo solo si el volumen lo exige | Equivalencia de variables y coste medido |
| Integración SOC | Crear casos con evidencia y revisión | Evaluación de carga con analistas |

Las etapas posteriores son trabajo pendiente. No deben aparecer en el CV como capacidades ya desplegadas.

## 17. Fuentes primarias

Todas consultadas para esta preparación el 31 de octubre de 2026. La interpretación de su encaje en AegisLake es del proyecto.

| ID | Fuente | Uso |
| --- | --- | --- |
| S1 | [MITRE: Password Spraying T1110.003](https://attack.mitre.org/techniques/T1110/003/) | Hipótesis de campaña |
| S2 | [MITRE: Valid Accounts T1078](https://attack.mitre.org/techniques/T1078/) | Contexto de abuso de cuentas |
| S3 | [LANL: Comprehensive Multi-Source Cyber-Security Events](https://csr.lanl.gov/data/cyber1/) | Investigación de benchmark y condiciones |
| S4 | [Microsoft Graph: signIn](https://learn.microsoft.com/en-us/graph/api/resources/signin?view=graph-rest-1.0) | Semántica y disponibilidad del export |
| S5 | [DuckDB: Parquet](https://duckdb.org/docs/stable/data/parquet/overview) | Persistencia y SQL |
| S6 | [scikit-learn: Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) | Prevención de fuga |
| S7 | [scikit-learn: IsolationForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html) | Interpretación de anomalías |
| S8 | [scikit-learn: average_precision_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html) | Definición de AP |
| S9 | [NIST: AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) | Gobernanza y evaluación |
| S10 | [scikit-learn: Model persistence](https://scikit-learn.org/stable/model_persistence.html) | Riesgo de artefactos ejecutables |
| S11 | [Microsoft: Azure for Students](https://learn.microsoft.com/en-us/azure/education-hub/about-azure-for-students) | Oferta y requisitos |
| S12 | [Microsoft: Container Apps Jobs](https://learn.microsoft.com/en-us/azure/container-apps/jobs) | Tareas finitas |
| S13 | [Microsoft: Container Apps billing](https://learn.microsoft.com/en-us/azure/container-apps/billing) | Unidades de consumo |
| S14 | [Microsoft: Blob authorization with Entra](https://learn.microsoft.com/en-us/azure/storage/blobs/authorize-access-azure-active-directory) | Identidades y permisos |
| S15 | [Microsoft: Cost alerts](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/cost-mgt-alerts-monitor-usage-spending) | Control de presupuesto |
| S16 | [GitHub: OIDC in Azure](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure) | Evolución de despliegue seguro |

Referencia LANL para una futura publicación: A. D. Kent, “Comprehensive, Multi-Source Cybersecurity Events,” Los Alamos National Laboratory, DOI 10.17021/1179829, 2015. No se afirma haber realizado experimentos con este conjunto.
