# Estado del proyecto — 25 de octubre de 2026

Ubicación: `/home/jd/Documents/Proyecto`.

Se construyó MotorLab con un motor eléctrico DC didáctico. La elección del motor
es una propuesta de implementación: el documento de migración no incluía el
enunciado específico de la asignatura ni las ecuaciones de un sistema existente.

## Implementado

- Dos ventanas Qt independientes: visualizador y dashboard.
- Modelo eléctrico, mecánico y térmico con RK4 a paso fijo.
- Escenarios manuales, pausa, velocidad del tiempo y experimento guiado de 90 s.
- Historial durable, exportación CSV y cola de sincronización a InfluxDB 3.
- Configuración de conexión y consulta real al servidor desde la interfaz.
- Guía de aprendizaje, ecuaciones y recorrido por el código.

## Verificado

- Doce pruebas de física, persistencia, HTTP e interacción gráfica.
- Experimento completo con 900 muestras; respuesta a cambios de carga y frenado.
- Renderizado de las dos ventanas y guardado local en modo gráfico sin pantalla.
- Ejecución nativa con Qt en Wayland; pantalla del equipo: 1920 × 1080.
- Dependencias del entorno virtual sin incompatibilidades reportadas por pip.

## Conexión pendiente del usuario

InfluxDB 3 Core 3.11.5 está activo en el puerto 8181 y exige autenticación.
No se proporcionó un token. Los envíos y consultas se comprobaron contra un
servidor HTTP controlado; aún no se ha verificado una escritura autenticada en
la instancia real. Introducir el token desde “Conectar InfluxDB” permite enviar
las muestras pendientes.

Los datos originales en `~.influxdb/` y el paquete `paho-mqtt` del entorno virtual
se conservaron. MQTT no se utiliza en esta primera versión.
