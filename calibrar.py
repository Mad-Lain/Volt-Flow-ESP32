# =============================================================
#  VoltFlow ESP32 – Script de calibración
# =============================================================
#  ¿Por qué calibrar?
#  Las resistencias R1 del circuito tienen tolerancia (±1 %),
#  y el ADC del ESP32 también tiene pequeñas variaciones.
#  Este script mide R1 con tu circuito real y calcula el valor
#  exacto que debes usar en config.py.
#
#  Instrucciones:
#    1. Conecta una resistencia conocida entre las puntas.
#    2. Ejecuta:  mpremote connect /dev/ttyUSB0 run calibrar.py
#    3. Copia los valores R1_BAJO y R1_ALTO que imprime en config.py
#
#  ¿Qué resistencias usar?
#    · Rango bajo : entre 200 Ω y 2 kΩ   (ej. 560 Ω)
#    · Rango alto : entre 4 kΩ y 15 kΩ   (ej. 10 kΩ)
#    · Mide cada resistencia con un multímetro antes de usarla
#      y escribe el valor real (no el nominal) abajo.
#
#  Fórmula usada:
#    Del divisor de voltaje:  Vout = VIN × Rx / (R1 + Rx)
#    Despejando R1:           R1 = Rx × (4095 - ADC) / ADC
# =============================================================

import machine
import time
from config import PIN_ADC, PIN_R_BAJO, PIN_R_ALTO

# ── Escribe aquí los valores medidos con tu multímetro ────────
RX_BAJO_CONOCIDO = 563.4    # Ohms – resistencia para calibrar rango bajo
RX_ALTO_CONOCIDO = 9900.0   # Ohms – resistencia para calibrar rango alto

N = 100   # número de muestras (más muestras = más precisión)

# ── Hardware ──────────────────────────────────────────────────
adc = machine.ADC(machine.Pin(PIN_ADC))
adc.atten(machine.ADC.ATTN_11DB)
adc.width(machine.ADC.WIDTH_12BIT)

pin_bajo = machine.Pin(PIN_R_BAJO, machine.Pin.IN)
pin_alto = machine.Pin(PIN_R_ALTO, machine.Pin.IN)


def leer_adc_mediana(n=N):
    """Toma n muestras y devuelve la mediana para mayor estabilidad."""
    muestras = []
    for _ in range(n):
        muestras.append(adc.read())
        time.sleep_ms(2)
    muestras.sort()
    return muestras[n // 2]


def calcular_r1(rx_conocido, adc_val):
    """Calcula R1 a partir de Rx conocido y la lectura del ADC."""
    if adc_val <= 0 or adc_val >= 4095:
        return None
    return rx_conocido * (4095 - adc_val) / adc_val


# ── Calibración rango bajo (Pin R_BAJO activo) ────────────────
print("\n=== RANGO BAJO (R1 ~1 kΩ) ===")
print("Conecta el resistor de {:.0f} Ω entre las puntas...".format(RX_BAJO_CONOCIDO))
print("Tienes 8 segundos.")
time.sleep(8)

pin_alto.init(machine.Pin.IN)
pin_bajo.init(machine.Pin.OUT, value=1)
time.sleep_ms(50)

adc_bajo = leer_adc_mediana()
r1_bajo  = calcular_r1(RX_BAJO_CONOCIDO, adc_bajo)

print("  ADC leido    : {}".format(adc_bajo))
if r1_bajo:
    print("  R1_BAJO      : {:.1f} Ohms".format(r1_bajo))
    print("  Comprobacion : Rx = {:.1f} Ohms".format(r1_bajo * adc_bajo / (4095 - adc_bajo)))
else:
    print("  ERROR: ADC fuera de rango ({}). Verifica la conexion.".format(adc_bajo))

pin_bajo.init(machine.Pin.IN)
time.sleep_ms(50)

# ── Calibración rango alto (Pin R_ALTO activo) ────────────────
print("\n=== RANGO ALTO (R1 ~10 kΩ) ===")
print("Conecta el resistor de {:.0f} Ohms entre las puntas...".format(RX_ALTO_CONOCIDO))
print("Tienes 8 segundos.")
time.sleep(8)

pin_alto.init(machine.Pin.OUT, value=1)
time.sleep_ms(50)

adc_alto = leer_adc_mediana()
r1_alto  = calcular_r1(RX_ALTO_CONOCIDO, adc_alto)

print("  ADC leido    : {}".format(adc_alto))
if r1_alto:
    print("  R1_ALTO      : {:.1f} Ohms".format(r1_alto))
    print("  Comprobacion : Rx = {:.1f} Ohms".format(r1_alto * adc_alto / (4095 - adc_alto)))
else:
    print("  ERROR: ADC fuera de rango ({}). Verifica la conexion.".format(adc_alto))

pin_alto.init(machine.Pin.IN)

# ── Resultado final ───────────────────────────────────────────
print("\n=== COPIA ESTOS VALORES EN config.py ===")
if r1_bajo:
    print("R1_BAJO = {:.1f}".format(r1_bajo))
if r1_alto:
    print("R1_ALTO = {:.1f}".format(r1_alto))
