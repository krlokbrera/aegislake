# Cómo convertir AegisLake en evidencia para tu CV

## Posicionamiento

El proyecto conecta experiencia de consultoría de ciberseguridad con trabajo técnico de datos. Es especialmente útil para conversar sobre ingeniería de datos, analítica avanzada, security analytics y ML aplicado, siempre que puedas ejecutar y explicar lo que has publicado.

No incluyas resultados medidos, despliegues o capacidades futuras hasta verificarlos. La tabla de estado del repositorio es la referencia.

## Entrada de CV tras verificar la versión local

**AegisLake — Ingeniería de datos e IA aplicada a ciberseguridad**

- Desarrollé un pipeline de eventos de identidad con contratos de datos, deduplicación, cuarentena, particiones Parquet y agregaciones SQL sobre DuckDB.
- Comparé reglas, Isolation Forest, regresión logística y un ranking híbrido mediante evaluación temporal y límites diarios de revisión.
- Incorporé trazabilidad de ejecuciones, seudonimización de exportaciones de identidad y una cola de evidencia para revisión humana.

Añade una cuarta viñeta sobre Azure solo después del despliegue verificado:

- Desplegué una demostración batch en Azure con Bicep, Container Apps Jobs, identidad administrada y publicación privada de informes.

## English version after verification

**AegisLake — Security Data Engineering and Applied Machine Learning**

- Built an identity-event pipeline with data contracts, deduplication, quarantine, partitioned Parquet storage, and SQL feature engineering.
- Evaluated rules, Isolation Forest, logistic regression, and hybrid ranking with temporal holdouts and daily analyst capacity constraints.
- Added reproducible run manifests, keyed identity pseudonymization, and a human review workflow.

After cloud verification:

- Deployed a finite batch demonstration on Azure using Bicep, Container Apps Jobs, managed identity, and private report storage.

## Cómo añadir cifras sin exagerar

Usa únicamente números del informe de una ejecución concreta. Registra semilla, datos, fechas y capacidad. Una frase adecuada sería: “Procesé N eventos sintéticos y comparé cuatro métodos con un límite de K ventanas por día”.

Para una métrica de detección, especifica que se midió sobre simulación o sobre el conjunto real correspondiente. No transformes AP en accuracy ni describas una reducción de falsos positivos sin comparar la misma muestra y política.

Si el híbrido no mejora las reglas, explica el resultado y la razón para mantener la referencia sencilla. Esa decisión puede demostrar más criterio que elegir siempre el modelo más complejo.

## Guion de entrevista de diez minutos

| Tiempo | Mostrar | Idea que defender |
| --- | --- | --- |
| 0–1 min | Problema y unidad de análisis | La salida debe caber en la capacidad del analista |
| 1–3 min | Contrato y calidad | Un detector depende de eventos fiables |
| 3–5 min | SQL y cortes temporales | Las variables deben existir cuando se toma la decisión |
| 5–7 min | Comparación y limitaciones | El modelo compite contra reglas y se evalúa sin ajustar con test |
| 7–8 min | Alerta y revisión | La señal no es una confirmación de incidente |
| 8–9 min | Azure y permisos | Compute finito y acceso a datos acotado |
| 9–10 min | Siguiente experimento | Validar transferencia con datos autorizados |

## Preguntas que debes poder responder

**¿Por qué DuckDB y no Spark?**

Porque la primera entrega debe poder reproducirse con un volumen pequeño. Parquet y SQL dan una base portable. Migraría tras medir memoria, volumen y tiempo, manteniendo pruebas de equivalencia.

**¿Por qué una separación temporal?**

Porque el uso previsto puntúa periodos posteriores al entrenamiento. Una división aleatoria puede repartir patrones de una misma campaña a ambos lados y favorecer la evaluación.

**¿Una anomalía es un ataque?**

No. Puede ser una migración, un servicio o un usuario legítimo. La cola presenta evidencia y necesita contexto.

**¿Por qué el score no es probabilidad?**

El percentil de anomalía compara rareza contra una referencia. El híbrido es una fórmula y la regresión tiene pesos de clase. Haría falta calibración y validación con prevalencia real.

**¿Cuál es la mayor limitación de la demo?**

Los datos proceden del mismo simulador que define sus etiquetas. La transferencia a una organización no está validada.

**¿Qué has hecho para evitar fuga de etiquetas?**

Allowlist explícita de variables, exclusión de identificadores y escenarios, transformaciones ajustadas en train y selección de umbrales en validación.

**¿La cola es en tiempo real?**

No. Las variables usan ventanas cerradas y el límite diario ordena un lote completo. Para streaming necesitaría tiempo de llegada, watermarks y una política de capacidad online.

**¿Qué parte es IA?**

La detección de anomalías y clasificación para priorizar ventanas. No depende de un LLM ni necesita enviar eventos a un proveedor de modelos.

**¿Qué harías con feedback de analistas?**

Separaría decisiones provisionales y adjudicadas, mediría sesgo de selección y evaluaría un nuevo entrenamiento. No reciclaría etiquetas de la cola automáticamente.

## Portfolio y README

Fija el repositorio independiente en tu perfil cuando la CI esté validada. Incluye una captura solo con datos sintéticos y una explicación breve del problema. Una captura bonita acompaña al código; no sustituye el protocolo de evaluación.

No publiques una certificación de cumplimiento, efectividad empresarial o ahorro de costes si lo único verificado es una demo local.
