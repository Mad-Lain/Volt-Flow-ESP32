# =============================================================
#  VoltFlow ESP32 – Detección de pulsación de botón
# =============================================================
#  La clase Button detecta dos tipos de interacción:
#    · clicked      → presión corta  (< LONG_MS ms)
#    · long_pressed → presión larga  (≥ LONG_MS ms)
#
#  Uso en el loop principal:
#    btn.update()
#    if btn.clicked:      ...
#    if btn.long_pressed: ...
# =============================================================

import machine
import time
from config import PIN_BOTON, LONG_MS


class Button:
    def __init__(self, pin=PIN_BOTON):
        # PULL_UP: el pin lee HIGH en reposo y LOW al presionar
        self._pin     = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self._down_at = None   # momento en que se presionó
        self._prev    = True   # estado anterior del pin
        self.clicked      = False
        self.long_pressed = False

    def update(self):
        """Lee el estado del botón. Llama esto en cada iteración del loop."""
        self.clicked      = False
        self.long_pressed = False
        now = time.ticks_ms()
        cur = self._pin.value()

        if not cur and self._prev:       # flanco bajada → empieza pulsación
            self._down_at = now
        elif cur and not self._prev:     # flanco subida → termina pulsación
            if self._down_at is not None:
                duracion = time.ticks_diff(now, self._down_at)
                if duracion >= LONG_MS:
                    self.long_pressed = True
                else:
                    self.clicked = True
            self._down_at = None

        self._prev = cur
