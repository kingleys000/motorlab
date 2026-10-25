# CHANGELOG

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato se inspira en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)
y el proyecto aún no usa versiones numeradas; se agrupa por fecha.

## 2026-10-25

### Documentación
- Se crea este CHANGELOG.
- `README.md`: corrección de la ruta del proyecto a `/home/jd/Documents/Proyecto`.
- `docs/ESTADO_DEL_PROYECTO.md`: fecha actualizada, ruta corregida y
  número de pruebas ajustado a doce.

### Verificación
- 12/12 pruebas unitarias en verde (física, persistencia, HTTP e interfaz).
- Prueba de humo gráfica (`main.py --smoke`) correcta: dos ventanas,
  217 muestras y registro local.

## 2026-09-30

### Implementado
- Versión inicial de MotorLab: dos ventanas Qt independientes
  (visualizador y dashboard).
- Modelo eléctrico, mecánico y térmico de motor DC con integración
  RK4 a paso fijo de 1 ms.
- Escenarios manuales, pausa, velocidad del tiempo (2×, 5×) y
  experimento guiado de 90 s.
- Historial durable en SQLite, exportación CSV y cola de sincronización
  a InfluxDB 3.
- Configuración de conexión y consulta al servidor desde la interfaz.
- Guía de aprendizaje con ecuaciones (`docs/MODELO_Y_GUIA.md`).
- Modo claro/oscuro compartido entre ventanas y persistente.
- Pruebas unitarias y de interfaz (física, persistencia y HTTP).
