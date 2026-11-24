# Diagnóstico sintético y motor 3D

Esta demostración utiliza datos generados y un motor didáctico. Una observación o una revisión de IA no identifica ni confirma una falla de un motor físico.

## Recorrido

1. En «Gemelo experimental», importe `examples/ajuste_saludable_sintetico.csv` y `examples/validacion_saludable_sintetica.csv` como ajuste y validación separados y pulse «Calibrar y comparar». Confirme el supuesto estacionario y que la temperatura corresponde al bobinado. No cargue el ensayo que desea evaluar como ajuste ni validación.
2. En «Motor 3D y diagnóstico», importe un tercer CSV de evaluación, por ejemplo `examples/combinada.csv`. Los controles iniciales son referencias del corpus sintético: 3 A, 40 °C, 0,5 V de residual, 1 s de persistencia y 0,5 s de limpieza. Son editables y no son límites de catálogo.
3. Si el ensayo de evaluación también es estacionario y es compatible con la calibración, declare esa condición en la casilla. Sin ambas condiciones se omite el diagnóstico de residual. Pulse «Detectar episodios»; seleccione un episodio para explorar su evidencia, el instante y el motor completo. La medición por sí sola no localiza una pieza averiada.
4. Para evaluar el detector, use «Evaluar etiquetas» y seleccione el archivo JSON complementario del CSV. Las etiquetas no se entregan al detector ni a los agentes. El nombre del CSV tampoco se envía a los agentes, porque puede revelar el caso esperado. Un pico marcado `expect_alert: false` no debe producir una alerta persistente.
5. Opcionalmente configure proveedor compatible con Chat Completions, URL base (por ejemplo `https://proveedor/v1`), modelo y clave, y pulse «Consultar diagnóstico y revisión IA». Las llamadas son secuenciales y ocurren solo por solicitud. La clave permanece en memoria. Con Google AI Studio se comprobó una consulta real a ambos agentes mediante `gemini-3.5-flash-lite`; la disponibilidad y las cuotas pueden variar.
6. La propuesta y la revisión citan IDs de evidencia y componentes del catálogo. Si el revisor falla, se conserva la propuesta sin revisión; esta no certifica una avería. Puede elegir un componente visualmente o abrir la vista explotada. Los datos o límites nuevos invalidan los resultados anteriores.
7. «Exportar informe JSON» incluye parámetros, episodios, interpretaciones y métricas disponibles, sin credenciales. El dashboard, las gráficas y la ventana 2D permanecen disponibles si falla el visor WebGL.

El visor usa Three.js 0.170.0 empaquetado bajo `web/vendor/three/` y Qt WebChannel local. La reproducción usa los intervalos temporales y las RPM registradas; es una ilustración, no una medición de vibración ni una reconstrucción física del movimiento.

## Corpus y evaluación reproducible

El generador `motorlab.synthetic.write_corpus` utiliza semilla base `20261104`, ensayos de 12 s con paso de 0,5 s, resistencia 1,7 Ω, constante 0,09 y coeficiente térmico de cobre 0,00393/K. Los puntos representan condiciones estacionarias independientes; no describen los transitorios entre ellos. Los intervalos anómalos persistentes van de 3 a 6 s; el pico breve dura una muestra. Ajuste, validación y evaluación saludable usan semillas o fases distintas. El caso de residual suma 2 V a la relación estacionaria. Los JSON en `examples/labels/` solo se usan en evaluación.

Para generar otra copia sin sobrescribir los ejemplos distribuidos:

```bash
.venv/bin/python -c "from motorlab.synthetic import write_corpus; write_corpus('/tmp/motorlab-corpus', seed=20261104)"
```

Para repetir la evaluación de los archivos distribuidos:

```bash
.venv/bin/python scripts/evaluate_synthetic.py
```

Con las referencias indicadas se detectaron 5 de 5 intervalos persistentes esperados, sin omisiones ni falsas alertas, y con demora de 1 s en cada detección. El ensayo saludable y el pico breve no generaron episodios. Son resultados de este corpus sintético y no estiman el desempeño con motores reales.

## Si falla la conexión con Gemini

Usa como URL base `https://generativelanguage.googleapis.com/v1beta/openai`, sin agregar `/chat/completions`. MotorLab informa los códigos HTTP comunes sin mostrar la respuesta cruda ni la clave. HTTP 400 puede indicar clave o solicitud inválida; 401 o 403 apuntan a autenticación o permisos; 404 a modelo o URL; 429 a cuota o límite. La disponibilidad del modelo y la cuota dependen del proyecto de Google.

El campo Modelo debe contener el identificador de API exacto, por ejemplo `gemini-3.5-flash-lite`, no un nombre con espacios. Google AI Studio puede listar modelos que no estén disponibles para todos los proyectos; ante errores de disponibilidad prueba un modelo habilitado para tu cuenta.
