# =============================================================
#  VoltFlow ESP32 – Script de calibración
# =============================================================
#  Instrucciones:
#    1. Edita RX_BAJO_CONOCIDO y RX_ALTO_CONOCIDO con los
#       valores reales medidos con tu multímetro.
#    2. Ejecuta:  mpremote run calibrar.py
#    3. Conecta cada resistencia cuando el buzzer lo indique:
#         1 beep  → conecta rango bajo   (~560 Ω)
#         2 beeps → conecta rango alto   (~10 kΩ)
#         3 beeps → conecta rango extra  (~47 kΩ)  [futuro]
#    4. Espera que el valor ADC se estabilice y presiona SW.
#    5. Copia R1_BAJO / R1_ALTO en config.py.
#
#  Fórmula:  R1 = Rx × (4095 − ADC) / ADC
# =============================================================

import machine
import time
import framebuf
import ssd1306
from config import PIN_ADC, PIN_R_BAJO, PIN_R_ALTO, PIN_MODO, PIN_SCL, PIN_SDA
from buzzer import bep

# ── Valores medidos con multímetro ────────────────────────────
RX_BAJO_CONOCIDO  = 563.4    # Ohms
RX_ALTO_CONOCIDO  = 9900.0   # Ohms
# RX_EXTRA_CONOCIDO = 47000.0  # descomentar cuando tengas la resistencia

N = 100   # muestras para la medición final

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
#  PAC_R  boca abierta derecha     PAC_L  boca abierta izquierda
#  ..####..  0x3C                  ..####..  0x3C
#  .######.  0x7E                  .######.  0x7E
#  ######..  0xFC                  ..######  0x3F
#  ###.....  0xE0                  .....###  0x07
#  ##......  0xC0                  ......##  0x03
#  ###.....  0xE0                  .....###  0x07
#  ######..  0xFC                  ..######  0x3F
#  .######.  0x7E                  .######.  0x7E
#
#  PAC_C  cerrado (círculo)        GHOST
#  ..####..  0x3C                  ..####..  0x3C
#  .######.  0x7E                  .######.  0x7E
#  ########  0xFF                  ########  0xFF
#  ########  0xFF                  #.####.#  0xBD  (ojos)
#  ########  0xFF                  ########  0xFF
#  ########  0xFF                  ########  0xFF
#  .######.  0x7E                  ########  0xFF
#  ..####..  0x3C                  ##.##.##  0xDB  (flecos)

def _fb(data):
    return framebuf.FrameBuffer(bytearray(data), 8, 8, framebuf.MONO_HLSB)

PAC_R = _fb([0x3C, 0x7E, 0xFC, 0xE0, 0xC0, 0xE0, 0xFC, 0x7E])
PAC_L = _fb([0x3C, 0x7E, 0x3F, 0x07, 0x03, 0x07, 0x3F, 0x7E])
PAC_C = _fb([0x3C, 0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E, 0x3C])
GHOST = _fb([0x3C, 0x7E, 0xFF, 0xBD, 0xFF, 0xFF, 0xFF, 0xDB])

# ── Escala 2× (8×8 → 16×16): cada píxel se convierte en bloque 2×2 ──
def scale2x(src):
    buf = bytearray(16 * 2)   # 16 filas × 2 bytes (16 bits/fila)
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
PAC_C_2X = scale2x(PAC_C)
GHOST_2X  = scale2x(GHOST)

HEADER_H  = 14
SPRITE_SZ = 16
GHOST_GAP = 22   # separación entre sprites
SPRITE_Y  = HEADER_H + 1 + (63 - HEADER_H - 1 - SPRITE_SZ) // 2


def mostrar_header(label):
    oled.fill_rect(0, 0, 128, HEADER_H, 0)
    oled.text("CAL  " + label, 0, 3, 1)
    oled.hline(0, HEADER_H, 128, 1)
    oled.show()


def update_anim(pac_x, mouth_open, num_ghosts):
    oled.fill_rect(0, HEADER_H + 1, 128, 64 - HEADER_H - 1, 0)

    # Pac-Man siempre corre hacia la derecha persiguiendo a los fantasmas
    oled.blit(PAC_R_2X if mouth_open else PAC_C_2X, pac_x, SPRITE_Y)

    # Fantasmas delante de Pac-Man (escapando a la derecha)
    for n in range(num_ghosts):
        oled.blit(GHOST_2X, pac_x + (n + 1) * GHOST_GAP, SPRITE_Y)

    oled.show()


def beeps(n):
    for i in range(n):
        bep()
        if i < n - 1:
            time.sleep_ms(150)


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


def medir_rango(nombre, rx_label, rx_conocido,
                pin_activo, pin_inactivo, num_beep, num_ghosts):
    pin_inactivo.init(machine.Pin.IN)
    pin_activo.init(machine.Pin.OUT, value=1)
    time.sleep_ms(400)

    beeps(num_beep)
    mostrar_header(rx_label)

    print("\n--- {} ---".format(nombre))
    print("Rx = {:.1f} Ohms  —  presiona SW cuando el ADC sea estable.\n".format(rx_conocido))

    while btn_sw.value() == 0:   # soltar si quedó presionado
        time.sleep_ms(10)

    # Pac-Man entra por la izquierda; al salir por la derecha vuelve a entrar
    pac_x      = -(num_ghosts * GHOST_GAP + SPRITE_SZ)
    mouth_open = True
    frame      = 0

    while True:
        update_anim(pac_x, mouth_open, num_ghosts)

        pac_x += 4
        if pac_x > 128:                                    # sale por la derecha
            pac_x = -(num_ghosts * GHOST_GAP + SPRITE_SZ) # vuelve por la izquierda
        if frame % 3 == 0:
            mouth_open = not mouth_open
        frame += 1

        if frame % 4 == 0:   # consola cada ~400 ms
            val = adc.read()
            r1  = calcular_r1(rx_conocido, val)
            if r1:
                print("  ADC {:4d}  |  R1 ~ {:.1f} Ohms".format(val, r1))
            else:
                print("  ADC {:4d}  |  fuera de rango".format(val))

        time.sleep_ms(100)

        if btn_sw.value() == 0:
            time.sleep_ms(60)
            print("  [SW] Tomando medicion final...")
            result = leer_adc_mediana()
            while btn_sw.value() == 0:
                time.sleep_ms(10)
            pin_activo.init(machine.Pin.IN)
            return result


# ── Calibración ───────────────────────────────────────────────
oled.fill(0)
oled.show()

adc_bajo = medir_rango(
    "RANGO BAJO  (R1 ~1 kOhm)", "R-560 Ohm",
    RX_BAJO_CONOCIDO, pin_bajo, pin_alto,
    num_beep=1, num_ghosts=1)
r1_bajo = calcular_r1(RX_BAJO_CONOCIDO, adc_bajo)

adc_alto = medir_rango(
    "RANGO ALTO  (R1 ~10 kOhm)", "R-10k Ohm",
    RX_ALTO_CONOCIDO, pin_alto, pin_bajo,
    num_beep=2, num_ghosts=2)
r1_alto = calcular_r1(RX_ALTO_CONOCIDO, adc_alto)

# Descomentar cuando tengas la resistencia de ~47 kΩ y PIN_R_EXTRA en config:
# from config import PIN_R_EXTRA
# pin_extra = machine.Pin(PIN_R_EXTRA, machine.Pin.IN)
# adc_extra = medir_rango(
#     "RANGO EXTRA (R1 ~47 kOhm)", "R-47k Ohm",
#     RX_EXTRA_CONOCIDO, pin_extra, pin_alto,
#     num_beep=3, num_ghosts=3)
# r1_extra = calcular_r1(RX_EXTRA_CONOCIDO, adc_extra)

# ── Resultado ─────────────────────────────────────────────────
print("\n========================================")
print("COPIA ESTOS VALORES EN config.py:")
print("========================================")
if r1_bajo:
    print("R1_BAJO = {:.1f}".format(r1_bajo))
    print("  verif. Rx = {:.1f} Ohms".format(r1_bajo * adc_bajo / (4095 - adc_bajo)))
else:
    print("R1_BAJO: ERROR (ADC={})".format(adc_bajo))

if r1_alto:
    print("R1_ALTO = {:.1f}".format(r1_alto))
    print("  verif. Rx = {:.1f} Ohms".format(r1_alto * adc_alto / (4095 - adc_alto)))
else:
    print("R1_ALTO: ERROR (ADC={})".format(adc_alto))

# if r1_extra:
#     print("R1_EXTRA = {:.1f}".format(r1_extra))

oled.fill(0)
oled.text("Calibracion OK!", 8, 28, 1)
oled.show()
