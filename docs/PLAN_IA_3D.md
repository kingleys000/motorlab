# Plan de implementación: diagnóstico con IA y motor 3D

Decisiones acordadas el 4 de noviembre de 2026. Conservar dashboard y motor 2D; añadir pestaña «Motor 3D y diagnóstico». Primera entrega: demostración reproducible con CSV sintéticos, dos agentes por API configurable y visor explotado.

## Datos y diagnóstico

- Preparar ensayos separados saludables para ajuste y validación y ensayos sintéticos etiquetados para evaluación: sobrecorriente, temperatura, residual estacionario, combinaciones y picos breves. Guardar las etiquetas esperadas aparte, sin enviarlas a la IA.
- Conservar el contrato CSV existente. Configurar límites y persistencia explícitos; habilitar residual solo con calibración compatible y supuesto estacionario declarado.
- Registrar episodios con ID único, señal, unidad, valor, límite, intervalo, procedencia y versión del análisis; incluir eventos repetidos. Evaluar detecciones, omisiones, falsas alertas y demora.

## Agentes

- Agente de diagnóstico: hipótesis, evidencia, alternativas, componentes posiblemente relacionados y comprobaciones. Agente revisor: evaluar sustento y contradicciones por separado.
- Respuestas JSON verificadas contra IDs de evidencia y componentes conocidos; evitar porcentajes y vida útil inventados. Llamadas secuenciales y asíncronas solo bajo solicitud; errores y reintento visibles. Si falla la revisión, mantener la propuesta señalada como no revisada.
- Configurar proveedor, URL, modelo y clave en la aplicación, con clave en memoria. Invalidar evidencias y resultados ante cambios del análisis; rechazar respuestas antiguas. Exportar informe JSON sin credenciales.

## Visor 3D

- Integrar el visor Three.js existente en QWebEngineView y QWebChannel con dependencias locales; preservar cámara, corte, vista explotada, etiquetas y temas.
- Nueva pestaña con visor, lista de episodios y evidencias. Navegar y reproducir el CSV, con giro ilustrativo según RPM. Seleccionar una alerta para enfocar componentes asociados y abrir la vista explotada.
- Identificar bobinado, rotor/eje, carcasa, estator, escobillas, conmutador y rodamientos. Separar observación de hipótesis y de componente seleccionado; si la evidencia no localiza la falla, señalar el motor completo. Si falla WebGL, conservar diagnóstico y dashboard.

## Verificación y entrega

- Mantener las 23 pruebas existentes y añadir pruebas para importación, episodios, evaluación y respuestas IA válidas, inválidas, fallidas y obsoletas.
- Verificar visualmente ambos temas, selección, vista explotada, reproducción y conservación de funciones 2D; comprobar ejecución local sin Internet.
- Probar integración con proveedor real cuando haya configuración disponible. No afirmar validación de motor físico sin ensayos reales independientes.
- Actualizar documentación y changelogs del proyecto y Obsidian por bloque terminado.
