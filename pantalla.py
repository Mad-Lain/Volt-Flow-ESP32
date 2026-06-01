# =============================================================
#  VoltFlow ESP32 – Renderizado en pantalla OLED (128×64)
# =============================================================
#  Distribución de la pantalla:
#    y =  0–15  → cabecera: icono BLE + unidad (centro) + modo (derecha) + línea
#    y = 16–55  → valor principal (texto escalado)
#    y = 56–63  → etiqueta del rango activo (micro fuente 3×5)
# =============================================================

import machine
import ssd1306
import framebuf
import time
from config   import PIN_SCL, PIN_SDA
from ble_volt import BLE_OFF, BLE_ADV, BLE_CON

# ── Inicialización del OLED ───────────────────────────────────
i2c  = machine.I2C(0, scl=machine.Pin(PIN_SCL), sda=machine.Pin(PIN_SDA))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# ── Iconos 8×8 px ─────────────────────────────────────────────
_icono_bt = framebuf.FrameBuffer(
    bytearray([0x08, 0x18, 0x54, 0x30, 0x54, 0x18, 0x08, 0x00]),
    8, 8, framebuf.MONO_HLSB)

_icono_alerta = framebuf.FrameBuffer(
    bytearray([0x08, 0x1c, 0x2a, 0x49, 0x49, 0x08, 0x7f, 0x00]),
    8, 8, framebuf.MONO_HLSB)

# ── Micro fuente 3×5 px ───────────────────────────────────────
_MICRO = {
    '0': [0b111, 0b101, 0b101, 0b101, 0b111],
    '1': [0b010, 0b110, 0b010, 0b010, 0b111],
    'k': [0b100, 0b101, 0b110, 0b101, 0b101],
}

# ── Forma de onda ECG (128 puntos) ────────────────────────────
_ECG_Y = bytes([
    40,40,40,40,40,40,40,40,40,40,40,40,40,40,40,
    38,36,36,37,39,40,
    40,40,40,40,40,40,40,40,40,40,40,40,
    42,44,43, 33,26,27, 36,47,48,
    44,42,41,40,40,40,
    40,39,38,37,36,35,34,35,36,37,38,39,40,40,40,
    40,40,40,40,40,40,40,40,40,40,
    40,40,40,40,40,40,40,40,40,40,
    40,40,40,40,40,40,40,40,40,40,
    40,40,40,40,40,40,40,40,40,40,
    40,40,40,40,40,40,40,40,40,40,
    40,40,40,40,40,40,40,40,40,40,
    40,40,40,40,40,40,40,40,40,40,
    40,40,40,40,40,
])

_ecg_off  = 0
_modo_txt = "RES"   # se actualiza desde main con set_modo()


# ── API pública de modo ───────────────────────────────────────

def set_modo(txt):
    """Actualiza la etiqueta de modo que aparece en el header."""
    global _modo_txt
    _modo_txt = txt


# ── Funciones privadas de dibujo ──────────────────────────────

def _draw_micro(text, x, y):
    cx = x
    for ch in text:
        filas = _MICRO.get(ch)
        if filas:
            for fila_idx, bits in enumerate(filas):
                for bit_idx in range(3):
                    if bits & (4 >> bit_idx):
                        oled.pixel(cx + bit_idx, y + fila_idx, 1)
        cx += 4


def _draw_scaled(text, x, y, scale):
    w   = len(text) * 8
    buf = bytearray(((w + 7) // 8) * 8)
    fb  = framebuf.FrameBuffer(buf, w, 8, framebuf.MONO_HLSB)
    fb.text(text, 0, 0, 1)
    for ty in range(8):
        for tx in range(w):
            if fb.pixel(tx, ty):
                oled.fill_rect(x + tx * scale, y + ty * scale, scale, scale, 1)


def _dibujar_header(unidad=None, ble_state=BLE_OFF):
    """Cabecera: icono BLE (izq) + unidad (centro) + modo (der) + línea."""
    if ble_state == BLE_CON:
        oled.blit(_icono_bt, 2, 4)
    elif ble_state == BLE_ADV:
        oled.rect(2, 4, 8, 8, 1)
    if unidad:
        u_x = (128 - len(unidad) * 8) // 2
        oled.text(unidad, u_x, 4)
    oled.text(_modo_txt, 128 - len(_modo_txt) * 8, 4)
    oled.hline(0, 15, 128, 1)


# ── Pantallas públicas ────────────────────────────────────────

def animar_modo(nombre):
    """
    Desliza el nombre del modo de derecha a izquierda.
    Al terminar la animación el loop retoma el ECG normalmente.
    """
    scale = 2
    ancho = len(nombre) * 8 * scale
    y     = (64 - 8 * scale) // 2
    x     = 128
    while x > -ancho:
        oled.fill(0)
        _draw_scaled(nombre, x, y, scale)
        oled.show()
        x -= 6
        time.sleep_ms(35)


def mostrar_reposo(ble_state=BLE_OFF):
    """Animación ECG — se llama en cada iteración sin componente."""
    global _ecg_off
    oled.fill(0)
    _dibujar_header(ble_state=ble_state)
    py = _ECG_Y[_ecg_off]
    oled.pixel(0, py, 1)
    for x in range(1, 128):
        cy = _ECG_Y[(x + _ecg_off) % 128]
        lo, hi = min(py, cy), max(py, cy)
        for y in range(lo, hi + 1):
            oled.pixel(x, y, 1)
        py = cy
    _ecg_off = (_ecg_off + 6) % 128
    oled.show()
    time.sleep_ms(50)


def mostrar_sin_componente(rango_txt, ble_state=BLE_OFF):
    """Señal inestable o sin componente conectado."""
    oled.fill(0)
    _dibujar_header(ble_state=ble_state)
    oled.text("Sin componente", 0, 28)
    oled.text("Conecta la R",  12, 44)
    _draw_micro(rango_txt, 2, 58)
    oled.show()


def mostrar_cortocircuito(rango_txt, ble_state=BLE_OFF):
    """Rx ≈ 0 Ω — puntas en cortocircuito."""
    oled.fill(0)
    _dibujar_header(ble_state=ble_state)
    oled.text("CORTOCIRCUITO", 0, 28)
    oled.text("R < 1 Ohm",   20, 44)
    _draw_micro(rango_txt, 2, 58)
    oled.show()


def mostrar_diodo(vf_txt, tipo, ble_state=BLE_OFF):
    """Muestra el voltaje directo (Vf) de un diodo o LED."""
    oled.fill(0)
    _dibujar_header(unidad=tipo, ble_state=ble_state)
    scale = 3
    num_w = len(vf_txt) * 8 * scale
    n_x   = max(0, (128 - num_w) // 2)
    n_y   = 16 + (40 - 8 * scale) // 2
    _draw_scaled(vf_txt, n_x, n_y, scale)
    oled.text("V", (128 - 8) // 2, n_y + 8 * scale + 2)
    oled.show()


def mostrar_medicion(numero, unidad, rango_txt, ble_state=BLE_OFF):
    """Muestra el valor de resistencia centrado en pantalla."""
    oled.fill(0)
    _dibujar_header(unidad=unidad, ble_state=ble_state)
    scale = 3 if len(numero) <= 5 else 2
    num_w = len(numero) * 8 * scale
    n_x   = max(0, (128 - num_w) // 2)
    n_y   = 16 + (40 - 8 * scale) // 2
    _draw_scaled(numero, n_x, n_y, scale)
    _draw_micro(rango_txt, 2, 58)
    oled.show()
