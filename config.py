# =============================================================
#  VoltFlow ESP32 – Configuración de hardware y calibración
# =============================================================
#  Este es el único archivo que deberías necesitar modificar
#  para adaptar el proyecto a tu propio circuito.
# =============================================================

# ── Pines ─────────────────────────────────────────────────────
PIN_ADC    = 34   # Entrada analógica: lee el voltaje del divisor
PIN_R_BAJO = 25   # Activa R1 del rango bajo  (~1 kΩ)
PIN_R_ALTO = 26   # Activa R1 del rango alto  (~10 kΩ)
PIN_BOTON  = 0    # GPIO0 = botón BOOT del ESP32
PIN_SCL    = 22   # I2C reloj (OLED)
PIN_SDA    = 21   # I2C datos (OLED)

# ── Calibración ───────────────────────────────────────────────
#  Valores obtenidos con calibrar.py. Cópialos aquí después
#  de correr ese script con tu circuito.
R1_BAJO = 1272.0    # Ohms – resistencia interna del rango bajo
R1_ALTO = 12192.9   # Ohms – resistencia interna del rango alto
VIN     = 3.2       # Voltios – tensión de referencia del ADC

# ── Umbrales de auto-ranging ──────────────────────────────────
#  El ADC entrega valores de 0 a 4095. Estos umbrales indican
#  cuándo la lectura se aleja demasiado del centro y hay que
#  cambiar de rango para mantener la precisión.
BAJAR_RANGO   = 450    # ADC < 450  en rango ALTO  → cambiar a BAJO
SUBIR_RANGO   = 3000   # ADC > 3000 en rango BAJO  → cambiar a ALTO
UMBRAL_REPOSO = 3900   # ADC > 3900 → sin componente conectado
VARIANZA_MAX  = 30000  # Varianza alta → señal inestable

# ── Buzzer y switch de modo ───────────────────────────────────
PIN_BUZZER = 18   # Buzzer activo: GVS → S=(+), G=(-)
PIN_MODO   = 17   # Switch de modo: GVS → S=patita, G=patita (pull-up interno)

# ── Botón ─────────────────────────────────────────────────────
LONG_MS = 1000   # Milisegundos mínimos para una pulsación larga

# ── Bluetooth BLE ─────────────────────────────────────────────
#  La app Flutter busca exactamente estos UUIDs. No los cambies
#  a menos que también actualices la app.
BLE_NOMBRE    = b'VoltFlow'
BLE_SVC_UUID  = '4fafc201-1fb5-459e-8fcc-c5c9c331914b'
BLE_CHAR_UUID = 'beb5483e-36e1-4688-b7f5-ea07361b26a8'
