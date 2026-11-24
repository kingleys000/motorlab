# CHANGELOG

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato se inspira en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)
y el proyecto aún no usa versiones numeradas; se agrupa por fecha.

## Cómo mantener este registro

Al completar cada cambio, agregarlo a la fecha correspondiente, con su efecto y
la verificación realizada. Mantener el historial en orden del más reciente al más
antiguo y conservar las entradas anteriores. Los planes se registran como pendientes,
no como cambios terminados.

Actualizar también la nota «MotorLab - Changelog» en el vault de Obsidian
`University/Modelado Continuo/MotorLab`. La sincronización entre ambos archivos
es manual y forma parte del registro de cada cambio.



## 2026-11-04 · Verificación real con Google AI Studio

- Se comprobó la conexión real mediante la API compatible de Google y `gemini-3.5-flash-lite`: diagnóstico y revisión devolvieron JSON válido con evidencia sintética. También se verificó el flujo desde la ventana de MotorLab.
- El campo Modelo requiere el identificador exacto, por ejemplo `gemini-3.5-flash-lite`, no su nombre de presentación. En la prueba, otros modelos devolvieron error o agotaron el tiempo de espera.
- No se guardó ninguna credencial en documentación ni registros de la aplicación. Una prueba de API real no valida un motor físico.

## 2026-11-04 · Resultado del análisis IA del ensayo combinado

- Se documenta la salida trazable de los dos agentes ejecutados desde la interfaz sobre el CSV sintético combinado: dos episodios persistentes (corriente y temperatura), ambos referenciados por ID y revisión sin error.
- La revisión sustenta únicamente que las señales superan los límites didácticos configurados. Las hipótesis de causas, los componentes mencionados y las comprobaciones sugeridas no se presentan como diagnóstico físico confirmado.
- Se actualizan las notas de Obsidian de diagnóstico, estado verificado y changelog. No hubo ensayos físicos ni se ejecutaron las comprobaciones sugeridas.

## 2026-11-04 · Comprobaciones físicas pendientes

- Se anotan como trabajo futuro el diseño y la ejecución documentada de comprobaciones de aislamiento, fricción mecánica y carga nominal, después de identificar el motor y revisar su ficha técnica y condiciones de seguridad.
- Las tres comprobaciones fueron sugeridas por el agente, pero no se han realizado; su inclusión no implica una falla confirmada.

## 2026-11-04 · Diagnóstico de conexión con proveedores IA

- MotorLab distingue errores HTTP de clave, permisos, modelo, cuota y servicio, además de errores de red y tiempo de espera, sin mostrar la respuesta cruda ni credenciales.
- El tiempo de espera predeterminado sube de 10 a 60 s y se advierte si la URL base incluye `/chat/completions`.
- La URL de compatibilidad de Google respondió desde el equipo; una prueba con clave deliberadamente inválida confirmó la identificación del HTTP 400. No se ha probado la clave personal ni una consulta autenticada real.

## 2026-11-04 · Demostración IA y motor 3D

- Se añade una pestaña de diagnóstico separada del dashboard y el motor 2D, con límites didácticos editables, navegación temporal y exportación JSON sin credenciales.
- Se empaqueta Three.js 0.170.0 localmente y se conecta el visor mediante QWebChannel; se añaden selección de componentes, controles de vista y adaptación al tema.
- Se incorpora una pareja secuencial de agentes compatibles con Chat Completions, con validación de referencias JSON, descarte de respuestas obsoletas y conservación de la propuesta si falla la revisión.
- Se documenta el recorrido y se enlaza desde README; se generan ensayos sintéticos reproducibles con etiquetas separadas; la evaluación conserva episodios repetidos y mide detecciones, omisiones, falsas alertas y demora.
- 43 pruebas correctas, incluidas las 23 preexistentes y las pruebas simuladas de IA. El corpus detectó 5/5 intervalos persistentes, sin omisiones ni falsas alertas y con demora de 1 s; salud y pico breve no generaron alertas.
- Visor y puente Qt comprobados en Wayland en ambos temas, con selección, vista explotada, reproducción y restauración. El contexto WebGL falló en una ejecución sin pantalla y el resto de la aplicación permaneció disponible. No se ha verificado un proveedor IA real.

## 2026-11-04

### Documentación

- Se crean diez notas iniciales de MotorLab en Obsidian, dentro de
  `University/Modelado Continuo/MotorLab`, con índice y enlaces internos.
- Se documentan ecuaciones, parámetros, integración numérica, arquitectura,
  uso, experimentos, almacenamiento, InfluxDB, ensayos, calibración,
  diagnóstico, asesor IA y pendientes.
- Se añade una nota de changelog enlazada desde el índice y la bitácora,
  con el historial previo y una plantilla para registrar los próximos cambios.
- Se contrasta la documentación con el código local actual y se distingue
  entre funciones implementadas, resultados verificados y trabajo pendiente.

### Cambiado

- Se rediseñan las flechas y los botones de los desplegables y controles numéricos
  para mejorar su contraste, sus estados de foco y su aspecto en ambos temas.
  Se aplica a escenarios, velocidad, sesiones y campos numéricos.
- Se añaden iconos específicos para los modos claro y oscuro y se ajusta la
  presentación de las opciones desplegadas.

### Corregido

- Las alertas se invalidan al cambiar un ensayo o perfil, recalibrar o ejecutar
  un nuevo diagnóstico. Si una consulta IA termina después de que cambien los
  datos, su respuesta se descarta para evitar atribuirla al análisis actual.
- Se evita iniciar una segunda consulta IA mientras la anterior espera ser procesada.

### Estado local documentado

Estas funciones ya estaban presentes al revisar el proyecto; esta fecha registra
su documentación, no atribuye una fecha de implementación ni una nueva versión.

- Importación de ensayos CSV con origen y metadatos de sensor explícitos.
- Perfiles JSON y calibración eléctrica estacionaria de R y K con validación separada.
- Diagnóstico de corriente persistente desde la interfaz; límites de temperatura
  y residual disponibles en la API Python.
- Asesor IA opcional y asíncrono; visor web 3D separado de la simulación Python.
- El motor integrado sigue siendo didáctico y los ensayos incluidos son sintéticos.
  La validación de un motor real continúa pendiente.

### Verificación

- Suite actual: 23 pruebas correctas, incluida una prueba de cambio de ensayo durante una consulta IA.
- Revisión visual del motor en modo claro y comprobación de apertura de los
  desplegables y de los botones de incremento y decremento en ambos temas.
- Suite completa: 22 pruebas correctas; smoke gráfico: dos ventanas y 222 muestras.
- 22/22 pruebas existentes correctas en la revisión del 4 de noviembre.
- Prueba de humo gráfica correcta: dos ventanas, 224 muestras y registro local temporal.
- Ajuste sintético comprobado: R≈1.7 Ω y K≈0.09; alerta de corriente a los 2 s
  con umbral de 2 A en el ejemplo de validación.
- No se verificaron en esta revisión un motor físico, el servidor InfluxDB real
  ni un proveedor IA real.

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
