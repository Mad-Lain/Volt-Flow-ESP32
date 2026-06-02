# =============================================================
#  VoltFlow ESP32 – Buzzer activo
# =============================================================
import machine
import time
from config import PIN_BUZZER

_pin = machine.Pin(PIN_BUZZER, machine.Pin.OUT, value=0)


def bep():
    """Un pitido corto — confirma cambio de modo."""
    _pin.value(1); time.sleep_ms(100)
    _pin.value(0)


def bep_bep():
    """Dos pitidos cortos — indica que se detectó un diodo o LED."""
    _pin.value(1); time.sleep_ms(120)
    _pin.value(0); time.sleep_ms(100)
    _pin.value(1); time.sleep_ms(120)
    _pin.value(0)


def bep_largo():
    """Pitido largo (1 s) — indica cambio de modo de calibración."""
    _pin.value(1); time.sleep_ms(1000)
    _pin.value(0); time.sleep_ms(80)
