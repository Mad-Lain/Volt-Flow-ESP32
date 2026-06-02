# =============================================================
#  VoltFlow ESP32 – Script de calibración
# =============================================================
#  Instrucciones:
#    1. Edita los valores conocidos (Rx y Vf) con los que
#       mediste con tu multímetro.
#    2. Ejecuta:  mpremote run calibrar.py
#
#  Controles:
#    SW corto  → confirma la medición actual
#    SW largo  → (después de resistencias) entra a calibrar D/L
#
#  Fases resistencias (Pac-Man persigue fantasmas):
#    1 beep  → rango bajo   (~560 Ω)
#    2 beeps → rango alto   (~10 kΩ)
#    3 beeps → rango extra  (~47 kΩ)  [futuro]
#
#  Fase D/L (fantasmas persiguen a Pac-Man):
#    bep largo + bep → calibrar diodo/LED
#
#  Fórmula resistencias:  R1 = Rx × (4095 − ADC) / ADC
# =============================================================

import machine
import time
import framebuf
import ssd1306
from config import PIN_ADC, PIN_R_BAJO, PIN_R_ALTO, PIN_MODO, PIN_SCL, PIN_SDA, VIN
from buzzer import bep, bep_bep, bep_largo

# ── Valores medidos con multímetro ────────────────────────────
RX_BAJO_CONOCIDO  = 563.4    # Ohms
RX_ALTO_CONOCIDO  = 9900.0   # Ohms
# RX_EXTRA_CONOCIDO = 47000.0  # descomentar cuando tengas la resistencia

VF_DIODO_CONOCIDO = 0.650    # Vf real del diodo de referencia (ej. 1N4007)
VF_LED_CONOCIDO   = 2.000    # Vf real del LED de referencia   (ej. LED rojo)

N = 100   # muestras para medición final

# ── Hardware ──────────────────────────────────────────────────
adc      = machine.ADC(machine.Pin(PIN_ADC))
adc.atten(machine.ADC.ATTN_11DB)
adc.width(machine.ADC.WIDTH_12BIT)

pin_bajo = machine.Pin(PIN_R_BAJO, machine.Pin.IN)
pin_alto = machine.Pin(PIN_R_ALTO, machine.Pin.IN)
btn_sw   = machine.Pin(PIN_MODO, machine.Pin.IN, machine.Pin.PULL_UP)

i2c  = machine.I2C(0, scl=machine.Pin(PIN_SCL), sda=machine.Pin(PIN_SDA))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# ── Sprites 8×8  (MONO_HLSB: bit 7 = pixel izquierdo) ────────
#
#  PAC_R  boca derecha              PAC_L  boca izquierda
#  ..####..  0x3C                   ..####..  0x3C
#  .######.  0x7E                   .######.  0x7E
#  ######..  0xFC                   ..######  0x3F
#  ###.....  0xE0                   .....###  0x07
#  ##......  0xC0                   ......##  0x03
#  ###.....  0xE0                   .....###  0x07
#  ######..  0xFC                   ..######  0x3F
#  .######.  0x7E                   .######.  0x7E
#
#  GHOST
#  ..####..  0x3C
#  .######.  0x7E
#  ########  0xFF
#  #.####.#  0xBD  (ojos)
#  ########  0xFF
#  ########  0xFF
#  ########  0xFF
#  ##.##.##  0xDB  (flecos)

def _fb(data):
    return framebuf.FrameBuffer(bytearray(data), 8, 8, framebuf.MONO_HLSB)

PAC_R = _fb([0x3C, 0x7E, 0xFC, 0xE0, 0xC0, 0xE0, 0xFC, 0x7E])
PAC_L = _fb([0x3C, 0x7E, 0x3F, 0x07, 0x03, 0x07, 0x3F, 0x7E])
PAC_C = _fb([0x3C, 0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E, 0x3C])
GHOST = _fb([0x3C, 0x7E, 0xFF, 0xBD, 0xFF, 0xFF, 0xFF, 0xDB])

def scale2x(src):
    buf = bytearray(16 * 2)
    dst = framebuf.FrameBuffer(buf, 16, 16, framebuf.MONO_HLSB)
    for row in range(8):
        for col in range(8):
            v = src.pixel(col, row)
            dst.pixel(col * 2,     row * 2,     v)
            dst.pixel(col * 2 + 1, row * 2,     v)
            dst.pixel(col * 2,     row * 2 + 1, v)
            dst.pixel(col * 2 + 1, row * 2 + 1, v)
    return dst

PAC_R_2X = scale2x(PAC_R)
PAC_L_2X = scale2x(PAC_L)
PAC_C_2X = scale2x(PAC_C)
GHOST_2X  = scale2x(GHOST)

HEADER_H  = 14
SPRITE_SZ = 16
GHOST_GAP = 22
SPRITE_Y  = HEADER_H + 1 + (63 - HEADER_H - 1 - SPRITE_SZ) // 2


def mostrar_header(label, ref=""):
    oled.fill_rect(0, 0, 128, HEADER_H, 0)
    oled.text("CAL  " + label, 0, 3, 1)
    if ref:
        oled.text(ref, 128 - len(ref) * 8, 3, 1)
    oled.hline(0, HEADER_H, 128, 1)
    oled.show()


def update_anim(pac_x, mouth_open, num_ghosts, pac_caza=True):
    """
    pac_caza=True  → Pac-Man corre a la derecha persiguiendo fantasmas.
    pac_caza=False → Fantasmas corren a la izquierda persiguiendo a Pac-Man.
    En ambos casos los fantasmas están al lado derecho de pac_x.
    """
    oled.fill_rect(0, HEADER_H + 1, 128, 64 - HEADER_H - 1, 0)

    sprite = (PAC_R_2X if pac_caza else PAC_L_2X) if mouth_open else PAC_C_2X
    oled.blit(sprite, pac_x, SPRITE_Y)

    for n in range(num_ghosts):
        oled.blit(GHOST_2X, pac_x + (n + 1) * GHOST_GAP, SPRITE_Y)

    oled.show()


# ── Detección de pulsación larga/corta ────────────────────────
LONG_PRESS_MS = 1000

def leer_sw():
    """
    Espera una pulsación del SW.
    Retorna True si fue larga (≥1 s), False si fue corta.
    """
    while btn_sw.value() == 0:   # soltar si estaba presionado
        time.sleep_ms(10)
    while btn_sw.value() == 1:   # esperar presión
        time.sleep_ms(20)
    t = time.ticks_ms()
    while btn_sw.value() == 0:   # esperar soltar
        time.sleep_ms(10)
    time.sleep_ms(50)            # debounce
    return time.ticks_diff(time.ticks_ms(), t) >= LONG_PRESS_MS


def leer_adc_mediana(n=N):
    muestras = []
    for _ in range(n):
        muestras.append(adc.read())
        time.sleep_ms(2)
    muestras.sort()
    return muestras[n // 2]


def calcular_r1(rx, adc_val):
    if adc_val <= 0 or adc_val >= 4095:
        return None
    return rx * (4095 - adc_val) / adc_val


def beeps(n):
    for i in range(n):
        bep()
        if i < n - 1:
            time.sleep_ms(150)


# ── Medición de resistencia ───────────────────────────────────
def medir_rango(nombre, rx_label, rx_conocido,
                pin_activo, pin_inactivo, num_beep, num_ghosts):
    """
    Muestra lecturas en vivo y espera SW.
    Retorna el ADC mediano, o None si el usuario hizo SW largo
    (señal para cambiar a calibración D/L).
    """
    pin_inactivo.init(machine.Pin.IN)
    pin_activo.init(machine.Pin.OUT, value=1)
    time.sleep_ms(100)

    beeps(num_beep)
    mostrar_header(rx_label)

    print("\n--- {} ---".format(nombre))
    print("Rx = {:.1f} Ohms  —  SW corto=confirmar  SW largo=ir a D/L\n".format(rx_conocido))

    while btn_sw.value() == 0:
        time.sleep_ms(10)

    pac_x      = -(num_ghosts * GHOST_GAP + SPRITE_SZ)
    mouth_open = True
    frame      = 0

    while True:
        update_anim(pac_x, mouth_open, num_ghosts, pac_caza=True)

        pac_x += 4
        if pac_x > 128:
            pac_x = -(num_ghosts * GHOST_GAP + SPRITE_SZ)
        if frame % 3 == 0:
            mouth_open = not mouth_open
        frame += 1

        if frame % 4 == 0:
            val = adc.read()
            r1  = calcular_r1(rx_conocido, val)
            if r1:
                print("  ADC {:4d}  |  R1 ~ {:.1f} Ohms".format(val, r1))
            else:
                print("  ADC {:4d}  |  fuera de rango".format(val))

        time.sleep_ms(100)

        if btn_sw.value() == 0:
            t = time.ticks_ms()
            while btn_sw.value() == 0:
                time.sleep_ms(10)
            time.sleep_ms(50)
            largo = time.ticks_diff(time.ticks_ms(), t) >= LONG_PRESS_MS

            if largo:
                pin_activo.init(machine.Pin.IN)
                return None          # señal: cambiar a D/L
            else:
                print("  [SW] Tomando medicion final...")
                result = leer_adc_mediana()
                pin_activo.init(machine.Pin.IN)
                return result


# ── Medición de Vf (D/L) ─────────────────────────────────────
def medir_vf_ref(nombre, vf_label, vf_conocido, num_ghosts):
    """Mide Vf de un componente conocido para calcular VF_OFFSET."""
    pin_alto.init(machine.Pin.IN)
    pin_bajo.init(machine.Pin.OUT, value=1)   # D/L siempre usa rango bajo
    time.sleep_ms(100)

    mostrar_header(vf_label, "{:.3f}V".format(vf_conocido))

    print("\n--- {} ---".format(nombre))
    print("Vf real = {:.3f} V  —  SW corto=confirmar\n".format(vf_conocido))

    while btn_sw.value() == 0:
        time.sleep_ms(10)

    # Fantasmas persiguen a Pac-Man: movimiento hacia la izquierda
    pac_x      = 128
    mouth_open = True
    frame      = 0

    while True:
        update_anim(pac_x, mouth_open, num_ghosts, pac_caza=False)

        pac_x -= 4
        if pac_x < -(SPRITE_SZ + num_ghosts * GHOST_GAP):
            pac_x = 128
        if frame % 3 == 0:
            mouth_open = not mouth_open
        frame += 1

        if frame % 4 == 0:
            val    = adc.read()
            vf_raw = (val / 4095.0) * VIN
            print("  ADC {:4d}  |  Vf raw ~ {:.3f} V  (offset ~ {:.3f} V)".format(
                  val, vf_raw, vf_conocido - vf_raw))

        time.sleep_ms(100)

        if btn_sw.value() == 0:
            time.sleep_ms(60)
            while btn_sw.value() == 0:
                time.sleep_ms(10)
            print("  [SW] Tomando medicion final...")
            muestras = []
            for _ in range(N):
                muestras.append(adc.read())
                time.sleep_ms(2)
            muestras.sort()
            val_final = muestras[N // 2]
            pin_bajo.init(machine.Pin.IN)
            return (val_final / 4095.0) * VIN   # Vf raw sin offset


# ── Pantalla de transición a D/L ─────────────────────────────
def pantalla_ir_dl():
    oled.fill(0)
    oled.hline(0, HEADER_H, 128, 1)
    oled.text("Resistencias OK", 0, 3, 1)
    oled.text("SW largo: D/L", 8, 22, 1)
    oled.text("SW corto: fin", 8, 34, 1)
    oled.show()


# ── Calibración ───────────────────────────────────────────────
oled.fill(0)
oled.show()

ir_a_dl   = False
r1_bajo   = None
r1_alto   = None
adc_bajo  = None
adc_alto  = None

# — Rango bajo —
adc_bajo = medir_rango(
    "RANGO BAJO  (R1 ~1 kOhm)", "R-560 Ohm",
    RX_BAJO_CONOCIDO, pin_bajo, pin_alto,
    num_beep=1, num_ghosts=1)

if adc_bajo is None:
    ir_a_dl = True
else:
    r1_bajo = calcular_r1(RX_BAJO_CONOCIDO, adc_bajo)

    # — Rango alto —
    adc_alto = medir_rango(
        "RANGO ALTO  (R1 ~10 kOhm)", "R-10k Ohm",
        RX_ALTO_CONOCIDO, pin_alto, pin_bajo,
        num_beep=2, num_ghosts=2)

    if adc_alto is None:
        ir_a_dl = True
    else:
        r1_alto = calcular_r1(RX_ALTO_CONOCIDO, adc_alto)

        # Descomentar para rango extra:
        # from config import PIN_R_EXTRA
        # pin_extra = machine.Pin(PIN_R_EXTRA, machine.Pin.IN)
        # adc_extra = medir_rango(
        #     "RANGO EXTRA (R1 ~47 kOhm)", "R-47k Ohm",
        #     RX_EXTRA_CONOCIDO, pin_extra, pin_alto,
        #     num_beep=3, num_ghosts=3)
        # if adc_extra is None:
        #     ir_a_dl = True
        # else:
        #     r1_extra = calcular_r1(RX_EXTRA_CONOCIDO, adc_extra)

        # — Ofrecer calibración D/L al terminar resistencias —
        pantalla_ir_dl()
        ir_a_dl = leer_sw()   # largo=True → ir a D/L, corto=False → fin

# ── Resultado resistencias ────────────────────────────────────
print("\n========================================")
print("RESISTENCIAS — COPIA EN config.py:")
print("========================================")
if r1_bajo:
    print("R1_BAJO = {:.1f}".format(r1_bajo))
    print("  verif. Rx = {:.1f} Ohms".format(r1_bajo * adc_bajo / (4095 - adc_bajo)))
if r1_alto:
    print("R1_ALTO = {:.1f}".format(r1_alto))
    print("  verif. Rx = {:.1f} Ohms".format(r1_alto * adc_alto / (4095 - adc_alto)))

# ── Calibración D/L ──────────────────────────────────────────
vf_offset = None

if ir_a_dl:
    bep_largo()
    bep()

    # — Diodo de referencia —
    vf_diodo_raw = medir_vf_ref(
        "D/L  diodo de referencia", "DIODO",
        VF_DIODO_CONOCIDO, num_ghosts=1)
    offset_diodo = VF_DIODO_CONOCIDO - vf_diodo_raw

    # — LED de referencia —
    vf_led_raw = medir_vf_ref(
        "D/L  LED de referencia", "LED",
        VF_LED_CONOCIDO, num_ghosts=2)
    offset_led = VF_LED_CONOCIDO - vf_led_raw

    # Promedio de ambos puntos
    vf_offset = (offset_diodo + offset_led) / 2.0

    print("\n========================================")
    print("D/L — COPIA EN config.py:")
    print("========================================")
    print("  Offset diodo : {:.3f} V".format(offset_diodo))
    print("  Offset LED   : {:.3f} V".format(offset_led))
    print("VF_OFFSET = {:.3f}".format(vf_offset))

# ── Pantalla final ────────────────────────────────────────────
oled.fill(0)
oled.text("Calibracion OK!", 8, 20, 1)
if vf_offset is not None:
    oled.text("VF={:.3f}V".format(vf_offset), 24, 36, 1)
oled.show()
