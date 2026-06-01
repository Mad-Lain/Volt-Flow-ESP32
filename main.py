# =============================================================
#  VoltFlow – Ohmímetro + Medidor de Diodos con ESP32
# =============================================================
#  Controles:
#    Botón BOOT (GPIO0):
#      · Click corto     → activa BLE / reenvía el último valor
#      · Pulsación larga → desactiva BLE
#    Switch de modo (GPIO17):
#      · Click           → alterna RES ↔ D/L con animación
# =============================================================

from config   import UMBRAL_REPOSO, VARIANZA_MAX, PIN_MODO
from medicion import (leer_adc, auto_ranging, calcular_resistencia,
                      formatear_ohms, rango_etiqueta, leer_vf)
from pantalla import (mostrar_reposo, mostrar_sin_componente,
                      mostrar_cortocircuito, mostrar_medicion,
                      mostrar_diodo, animar_modo, set_modo)
from ble_volt import VoltBLE, BLE_OFF, BLE_CON
from boton    import Button
from buzzer   import bep, bep_bep

print("VoltFlow | BOOT: click=BLE  hold=BLE off  |  SW: modo RES/D/L")

ble        = VoltBLE()
btn        = Button()
btn_modo   = Button(pin=PIN_MODO)
ult_txt    = ""
modo       = "RES"   # "RES" o "DIL"
_tipo_prev = None

set_modo("RES")

while True:

    # ── 1. Botón BLE (BOOT) ───────────────────────────────────
    btn.update()
    if btn.long_pressed:
        ble.deactivate()
    elif btn.clicked:
        if ble.state == BLE_OFF:
            ble.activate()
        elif ble.state == BLE_CON:
            ble.send(ult_txt)

    # ── 2. Switch de modo ─────────────────────────────────────
    btn_modo.update()
    if btn_modo.clicked:
        modo = "DIL" if modo == "RES" else "RES"
        if modo == "RES":
            set_modo("RES")
            nombre = "Resistencia"
        else:
            set_modo("D/L")
            nombre = "Diodo / LED"
        bep()
        animar_modo(nombre)
        _tipo_prev = None

    # ── 3. Medición ───────────────────────────────────────────
    if modo == "RES":

        valor_adc, varianza = leer_adc()
        valor_adc, varianza = auto_ranging(valor_adc, varianza)

        if valor_adc > UMBRAL_REPOSO:
            mostrar_reposo(ble_state=ble.state)

        elif varianza > VARIANZA_MAX:
            mostrar_sin_componente(rango_etiqueta(), ble_state=ble.state)

        else:
            resistencia = calcular_resistencia(valor_adc)
            if resistencia is None:
                mostrar_cortocircuito(rango_etiqueta(), ble_state=ble.state)
            else:
                numero, unidad = formatear_ohms(resistencia)
                ult_txt = "{} {}".format(numero, unidad)
                ble.send(ult_txt)
                mostrar_medicion(numero, unidad, rango_etiqueta(), ble_state=ble.state)

    else:  # modo DIL

        vf, tipo, varianza = leer_vf()

        if vf is None:
            _tipo_prev = None
            if varianza > VARIANZA_MAX:
                mostrar_sin_componente("D/L", ble_state=ble.state)
            else:
                mostrar_reposo(ble_state=ble.state)

        else:
            if tipo != _tipo_prev:
                bep_bep()
            _tipo_prev = tipo
            vf_txt  = "{:.2f}".format(vf)
            ult_txt = "{} {} V".format(tipo, vf_txt)
            ble.send(ult_txt)
            mostrar_diodo(vf_txt, tipo, ble_state=ble.state)
