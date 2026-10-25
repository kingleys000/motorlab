MOTORLAB · GUÍA DEL MODELO
========================

QUÉ ESTAMOS SIMULANDO

Un motor eléctrico de corriente continua convierte energía eléctrica en giro.
La corriente crea un par que acelera el rotor. Al girar, el motor genera una
tensión opuesta a la alimentación; por eso la corriente baja después del arranque.
Parte de la energía se pierde como calor. Si aumentamos la carga mecánica, el
motor se frena, aumenta su corriente y se calienta más.

Tres estados describen el sistema:
  i: corriente de armadura, en amperios (A).
  ω: velocidad angular, en radianes por segundo (rad/s).
  T: temperatura del bobinado, en grados Celsius (°C).

Sus entradas son el voltaje V, la carga resistente τ y la disipación térmica h.
Los parámetros son didácticos y no corresponden a un motor comercial calibrado.

LAS ECUACIONES

  L · di/dt = V − R(T)·i − ke·ω
  J · dω/dt = kt·i − b·ω − τ·tanh(ω/2)
  C · dT/dt = i²·R(T) + b·ω² − h·(T − Tamb)
  R(T) = R25 · [1 + α·(T − 25)]

La primera ecuación aplica el balance de tensiones. La segunda aplica el balance
de torques. La tercera aplica el balance de calor: pérdidas por efecto Joule y
fricción, menos enfriamiento al ambiente. tanh suaviza el cambio de signo de la
carga cerca de velocidad cero. Representa una carga resistente regularizada,
no un modelo exacto de fricción estática.

PARÁMETROS INICIALES

  R25 = 1.2 Ω       Resistencia a 25 °C.
  L   = 0.012 H     Inductancia de armadura.
  kt  = 0.08 N·m/A  Constante de par.
  ke  = 0.08 V·s/rad Constante de fuerza contraelectromotriz.
  J   = 0.0025 kg·m² Inercia del rotor y carga equivalente.
  b   = 0.0003 N·m·s/rad  Rozamiento viscoso.
  C   = 35 J/K      Capacidad térmica.
  α   = 0.00393 K⁻¹ Coeficiente de temperatura del cobre.
  Tamb = 25 °C     Temperatura ambiente constante.

Estado inicial: i = 0 A, ω = 0 rad/s, T = 25 °C.
Entrada inicial: V = 18 V, τ = 0.06 N·m, h = 0.55 W/K.

CÓMO SE CALCULAN LOS RESULTADOS

  RPM = ω·60/(2π)
  Par electromagnético = kt·i
  Potencia eléctrica = V·i
  Potencia útil en la carga = τ·tanh(ω/2)·ω

El campo exportado power_ratio es 100·potencia útil/potencia eléctrica cuando
la potencia de entrada supera 0.01 W; en otro caso se registra 0. Sólo debe
interpretarse como eficiencia en régimen estacionario. Durante un transitorio
la energía almacenada también entra o sale del motor.

UN PASO NUMÉRICO

El programa usa Runge–Kutta de cuarto orden (RK4) para avanzar 1 ms. Calcula
cuatro pendientes dentro del intervalo y combina sus valores. Así obtiene i,
ω y T en el siguiente instante. El dibujo utiliza el resultado, no determina
la física. Acelerar a 5× aumenta los pasos ejecutados por segundo real, sin
agrandar el paso de integración.

EXPERIMENTO GUIADO

Pulsa “Experimento guiado · 90 s”. Se crea una sesión nueva y el tiempo avanza
a 5×. Las sesiones anteriores permanecen guardadas.

  0–15 s: marcha nominal, 18 V, 0.06 N·m, 0.55 W/K.
 15–45 s: carga elevada, 18 V, 0.65 N·m, 0.55 W/K.
 45–75 s: refrigeración reducida, 24 V, 0.50 N·m, 0.15 W/K.
 75–90 s: desaceleración eléctrica, 0 V, 0.06 N·m, 0.55 W/K.

En el tercer tramo cambian voltaje, carga y refrigeración: muestra un escenario
combinado. Para estudiar una causa por separado, cambia una sola entrada con
los controles manuales. A 0 V el circuito permanece cerrado; existe frenado
eléctrico, no es un circuito abierto.

EJERCICIOS PARA APRENDER

1. Arranque: usa 18 V y observa cómo suben las RPM mientras la corriente baja.
2. Carga: cambia sólo la carga de 0.06 a 0.65 N·m. Compara corriente y velocidad.
3. Calor: conserva voltaje y carga, y reduce sólo h. Espera varios minutos
   simulados para observar la respuesta térmica, más lenta que la eléctrica.
4. Parada: aplica 0 V y observa el frenado y la corriente transitoria negativa.
5. Equilibrio: espera hasta que las curvas se estabilicen. Sustituye los valores
   en las ecuaciones y verifica que las derivadas se aproximan a cero.
6. Exportación: guarda un CSV y usa sim_time como eje temporal del análisis.

QUÉ MUESTRA CADA VENTANA

Visualizador: motor esquemático, RPM, amperios, temperatura y controles.
Dashboard: curvas, potencias, par, historial, bitácora y consulta a InfluxDB.
Ambas ventanas comparten una sola simulación. Cerrar una no detiene la otra.
Ctrl+Espacio inicia o pausa cuando una de las ventanas tiene el foco.

Los colores cálidos indican aumento de temperatura. La línea de 80 °C es una
referencia didáctica; no representa una especificación ni detiene el modelo.
La animación está ralentizada para poder ver las bobinas; no representa la
velocidad angular real de cada fotograma.

DATOS Y LÍMITES

Cada 0.1 s simulado se guarda una muestra en SQLite. Se sincroniza con la tabla
motor_dc de InfluxDB cuando se dispone del token. El historial del dashboard
lee la copia local y la pestaña “Datos en InfluxDB” consulta el servidor real.
La adquisición a 10 Hz no resuelve todo el pico eléctrico del arranque, cuya
escala de tiempo es del orden de L/R = 10 ms.

El modelo usa temperatura uniforme, un circuito promedio y constantes de
par e inductancia fijas. No incluye PWM, saturación magnética, ruido de sensores,
desgaste o una geometría electromagnética real. Los valores de temperatura
extremos quedan fuera de la validez de esta aproximación.
