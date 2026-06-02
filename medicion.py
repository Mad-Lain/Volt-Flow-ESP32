# =============================================================
#  VoltFlow ESP32 – Lectura del ADC y cálculo de componentes
# =============================================================
#
#  Circuito divisor de voltaje:
#
#       VIN ── R1 ── PIN_ADC ── Rx ── GND
#
#  Modo RES: calcula resistencia con la fórmula del divisor.
#  Modo D/L: lee el voltaje directo (Vf) del diodo o LED.
#            Siempre usa rango bajo (R1≈1kΩ) para dar corriente
#            suficiente al componente.
# =============================================================

import machine
import time
from config import (PIN_ADC, PIN_R_BAJO, PIN_R_ALTO,
                    R1_BAJO, R1_ALTO, VIN,
                    BAJAR_RANGO, SUBIR_RANGO,
                    UMBRAL_REPOSO, VARIANZA_MAX,
                    VF_OFFSET)

# ── Configuración del ADC ─────────────────────────────────────
adc = machine.ADC(machine.Pin(PIN_ADC))
adc.atten(machine.ADC.ATTN_11DB)
adc.width(machine.ADC.WIDTH_12BIT)

# ── Pines de selección de rango ───────────────────────────────
pin_r_bajo = machine.Pin(PIN_R_BAJO, machine.Pin.IN)
pin_r_alto = machine.Pin(PIN_R_ALTO, machine.Pin.OUT, value=1)

rango_actual = "ALTO"


def set_rango(nuevo):
    global rango_actual
    if nuevo == rango_actual:
        return
    if nuevo == "BAJO":
        pin_r_bajo.init(machine.Pin.OUT, value=1)
        pin_r_alto.init(machine.Pin.IN)
    else:
        pin_r_alto.init(machine.Pin.OUT, value=1)
        pin_r_bajo.init(machine.Pin.IN)
    rango_actual = nuevo
    time.sleep_ms(400)


def leer_adc(n=50):
    """
    Toma n muestras y devuelve (mediana, varianza).
    Mediana: robusta ante picos de ruido.
    Varianza alta: señal inestable o sin componente.
    """
    muestras = []
    for _ in range(n):
        muestras.append(adc.read())
        time.sleep_ms(2)
    muestras.sort()
    mediana  = muestras[n // 2]
    promedio = sum(muestras) / n
    varianza = sum((x - promedio) ** 2 for x in muestras) / n
    return mediana, varianza


def auto_ranging(valor_adc, varianza):
    """Cambia de rango si el ADC está fuera de la zona precisa."""
    if rango_actual == "ALTO" and valor_adc < BAJAR_RANGO:
        set_rango("BAJO")
        return leer_adc()
    if rango_actual == "BAJO" and valor_adc > SUBIR_RANGO:
        set_rango("ALTO")
        return leer_adc()
    return valor_adc, varianza


def calcular_resistencia(valor_adc):
    """
    Calcula Rx en Ohms con la fórmula del divisor de voltaje.
    Devuelve None en cortocircuito.
    """
    if valor_adc <= 0:
        return None
    R1    = R1_BAJO if rango_actual == "BAJO" else R1_ALTO
    vout  = (valor_adc / 4095.0) * VIN
    denom = VIN - vout
    if denom <= 0.01:
        return None
    return R1 * (vout / denom)


def formatear_ohms(r):
    """Convierte Ohms a (valor_str, unidad_str) legibles."""
    if r >= 1_000_000:
        return "{:.2f}".format(r / 1_000_000), "MOhm"
    elif r >= 1000:
        return "{:.2f}".format(r / 1000), "kOhm"
    else:
        return "{:.1f}".format(r), "Ohm"


def rango_etiqueta():
    """Etiqueta corta del rango activo para mostrar en pantalla."""
    return "1k" if rango_actual == "BAJO" else "10k"


def leer_vf():
    """
    Lee el voltaje directo (Vf) de un diodo o LED (modo D/L).
    Siempre usa rango bajo para dar corriente suficiente al componente.
    Devuelve (vf_volts, tipo_str, varianza) o (None, None, varianza).
    """
    set_rango("BAJO")
    valor_adc, varianza = leer_adc()
    if valor_adc > UMBRAL_REPOSO or varianza > VARIANZA_MAX:
        return None, None, varianza
    vf   = (valor_adc / 4095.0) * VIN + VF_OFFSET
    tipo = 'LED' if vf >= 1.4 else 'DIODO'
    return vf, tipo, varianza
