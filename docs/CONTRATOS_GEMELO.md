# Contratos y plan del prototipo

1. Perfiles versionados: identidad, parámetros SI, fuente y estado; el perfil existente es didáctico, no identifica un motor real.
2. Ensayos CSV: adquisición en segundos relativos crecientes, voltage (V), current (A), rpm, temperature (°C), sensor_type y sensor_location; load (N m) y ambient (°C) opcionales. Datos importados son medidos o sintéticos explícitos. La temperatura de carcasa no representa bobinado.
3. Calibración offline sobre ensayos saludables separados para ajuste y validación; parámetros no identificables permanecen fijos. Pruebas sintéticas verifican software, no un motor real.
4. Diagnóstico usa evidencia y persistencia, límites conocidos y modelo congelado; incertidumbre y ausencia de carga o sensor equivalente limitan las conclusiones.
5. Integrar interfaz y agentes optativos asincrónicos sin acceso a control físico; verificar sin servicios externos ni datos reales.

Propiedad: física/calibración y diagnóstico se asignan por separado; integración, importación y perfiles corresponden al integrador. Datos reales, identificación del motor y calibración experimental siguen pendientes.

Estado actual y uso: `docs/GEMELO_EXPERIMENTAL.md`. El ajuste implementado es estacionario eléctrico y no cubre todavía identificación dinámica ni previsión.
