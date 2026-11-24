# MotorLab — Modelado y Simulación Continua

Laboratorio de escritorio con **dos ventanas independientes**: un motor DC animado
y un dashboard de telemetría. Se ejecuta en Linux con Python, PySide6 y PyQtGraph.

El motor es una propuesta didáctica de 24 V: el documento de migración no
especificaba un fenómeno ni un motor real. Sus parámetros están declarados en
`motorlab/model.py` y pueden adaptarse al enunciado de la asignatura.

## Ejecutar

```bash
cd /home/jd/Documents/Proyecto
bash iniciar.sh
```

También puedes usar `.venv/bin/python main.py` desde la carpeta del proyecto.
El entorno virtual existente ya tiene instaladas las dependencias de esta aplicación.
Para reconstruirlo en otro equipo: crea un entorno Python compatible e instala
`requirements.txt`. Las versiones fijadas corresponden al Python 3.14 de este equipo.

Pulsa **Iniciar simulación** o **Experimento guiado · 90 s**. El experimento guiado
usa velocidad 5×, por lo que dura aproximadamente 18 segundos de reloj. Las dos
ventanas muestran el mismo motor. Puedes distribuirlas entre monitores y recuperar
una ventana cerrada con “Abrir dashboard” o “Ver motor”. Cerrar ambas finaliza la app.

Para elegir el aspecto, abre **Apariencia → Modo claro / Modo oscuro** en cualquiera
de las ventanas. Ambas cambian juntas, incluidas las gráficas y el visualizador,
y la elección se conserva para el siguiente inicio en `data/preferences.json`.

## Lo que puedes hacer

- Cambiar voltaje (0–24 V), carga (0–1.2 N·m) y disipación térmica (0.1–2 W/K).
- Observar RPM, corriente, temperatura, par y potencias eléctricas y mecánicas.
- Pausar y reanudar el tiempo, o acelerarlo a 2× y 5×.
- Ejecutar cuatro escenarios o un experimento que los recorre automáticamente.
- Recuperar sesiones previas del historial local y exportarlas completas a CSV.
- Sincronizar datos con InfluxDB 3 y consultar las diez muestras más recientes.
- Abrir la explicación del modelo desde cualquiera de las dos ventanas.

## Conectar InfluxDB 3 Core

El servidor local existente responde en `http://127.0.0.1:8181` y solicita
autenticación. Abre **Conectar InfluxDB**, usa la base `modelado_simulacion` e
introduce tu token con permisos de escritura y consulta. La casilla de guardado
es opcional; guarda la configuración en `.env` con permisos `0600`.

También puedes configurar `.env` siguiendo `.env.example` o usar las variables
`INFLUX_HOST`, `INFLUX_DATABASE`, `INFLUX_TOKEN`, `INFLUX_ENABLED`.
Se reconocen `INFLUXDB3_HOST_URL`, `INFLUXDB3_DATABASE_NAME` e
`INFLUXDB3_AUTH_TOKEN` como valores alternativos. El entorno tiene prioridad sobre
el archivo al arrancar. Desde la ventana, una nueva configuración se aplica a la
ejecución actual.

La app escribe mediante `POST /api/v3/write_lp` y consulta por
`POST /api/v3/query_sql`. No requiere instalar un cliente v2 ni usar Flux.
Documentación oficial:

- https://docs.influxdata.com/influxdb3/core/write-data/http-api/
- https://docs.influxdata.com/influxdb3/core/query-data/execute-queries/influxdb-v3-api/

No se requiere conexión para simular. Cada muestra se guarda primero en
`data/telemetry.sqlite3`; esta base local también funciona como cola durable de
sincronización. Los envíos se realizan en segundo plano, en lotes de hasta 500
muestras. Una respuesta exitosa marca las muestras como enviadas. Si falla la red
o el token, quedan pendientes para reintentar. Su timestamp se conserva, haciendo
que los reintentos escriban el mismo punto de InfluxDB.

El estado de conexión y las muestras pendientes aparecen abajo en ambas ventanas.
La app no arranca ni detiene el servicio de InfluxDB. Los datos existentes bajo
`~.influxdb/` se conservan; es una carpeta cuyo nombre comienza literalmente con `~`.

Si cambias la base o el servidor, las muestras aún pendientes se enviarán al
nuevo destino. Las ya sincronizadas no se copian automáticamente a otro destino.

## Tiempo y datos

- Integración del modelo: RK4, paso fijo de **1 ms**.
- Muestreo persistido: **10 Hz de tiempo simulado**.
- Dibujo del motor: aproximadamente 30 fotogramas/s.
- Gráficas: actualización hasta 10 veces/s.
- Gráficas en vivo: ventana visible de 60 s, memoria de hasta 600 s.
- Historial y exportación: todas las muestras guardadas de la sesión.

El timestamp de InfluxDB representa el instante real de adquisición. El campo
`sim_time` representa el tiempo de la simulación y debe usarse para analizar las
ecuaciones, especialmente al usar 2× o 5×. Una muestra cada 100 ms no captura todo
el transitorio eléctrico inicial de milisegundos; el integrador sí lo calcula.

Tabla de InfluxDB: `motor_dc`. Etiquetas: `session`, `motor`. Campos:
`sim_time`, `rpm`, `current`, `temperature`, `voltage`, `load`, `cooling`, `torque`,
`power_in`, `power_out`, `power_ratio`. Las unidades se documentan en la guía.

## Cómo estudiar el código

La pestaña «Motor 3D y diagnóstico» permite explorar ensayos sintéticos y consultar
dos agentes configurables. El recorrido, los límites didácticos y la evaluación
reproducible se describen en [Diagnóstico IA y 3D](docs/DIAGNOSTICO_IA_3D.md).
Los agentes se comprobaron con respuestas simuladas y con una consulta real a Google AI Studio; sus respuestas no validan una falla física.

1. `docs/MODELO_Y_GUIA.md`: fenómeno, ecuaciones, unidades y experimentos.
2. `motorlab/model.py`: ecuaciones e integración numérica, sin interfaz ni base.
3. `motorlab/controller.py`: reloj, cambios de escenario y muestreo.
4. `motorlab/visualizer.py`: dibujo del motor con Qt.
5. `motorlab/ui.py`: controles, gráficas e historial.
6. `motorlab/storage.py`: persistencia local y comunicación con InfluxDB.
7. `main.py`: reúne los componentes y abre las dos ventanas.

## Comprobaciones

```bash
cd /home/jd/Documents/Proyecto
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python main.py --smoke
```

La comprobación gráfica abre dos ventanas fuera de pantalla, simula, comprueba el
guardado y sale. Usa una base temporal y no envía datos a InfluxDB. Para obtener
capturas: `--smoke --capture-dir /ruta/de/salida`.

Las pruebas comprueban equilibrio, balance energético, convergencia del integrador,
respuesta a la carga, exportación y el protocolo HTTP con un servidor local
controlado. La conexión autenticada con tu servidor real requiere tu token.

## Alcance

Es un modelo educativo de parámetros concentrados, sin calibración experimental.
El dibujo es un corte esquemático 2D con giro ralentizado; las RPM indicadas sí
proceden del modelo. El umbral visual de 80 °C es una referencia didáctica, no una
protección automática. No se simulan conmutación por escobillas, PWM, saturación,
desgaste ni daños. La aplicación no controla hardware real.
