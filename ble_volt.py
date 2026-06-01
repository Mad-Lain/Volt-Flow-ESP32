# =============================================================
#  VoltFlow ESP32 – Comunicación Bluetooth BLE
# =============================================================
#  La clase VoltBLE implementa un servidor GATT mínimo:
#    · Un servicio con una característica notificable.
#    · La app Flutter se suscribe y recibe el valor de la
#      resistencia como texto (ej. "4.97 kOhm").
#
#  Ciclo de vida del BLE:
#    BLE_OFF → activate() → BLE_ADV → (conexión) → BLE_CON
#    BLE_CON → deactivate() o desconexión → BLE_OFF / BLE_ADV
# =============================================================

import bluetooth
from config import BLE_NOMBRE, BLE_SVC_UUID, BLE_CHAR_UUID

# Estados del módulo BLE
BLE_OFF = 0   # apagado
BLE_ADV = 1   # anunciando, esperando conexión
BLE_CON = 2   # conectado a un dispositivo

_IRQ_CONNECT    = 1
_IRQ_DISCONNECT = 2


class VoltBLE:
    def __init__(self):
        self._ble    = bluetooth.BLE()
        self._conn   = None    # handle de la conexión activa
        self._handle = None    # handle de la característica GATT
        self.state   = BLE_OFF

    def activate(self):
        """Enciende el BLE y comienza a anunciar el dispositivo."""
        if self.state != BLE_OFF:
            return
        svc_uuid  = bluetooth.UUID(BLE_SVC_UUID)
        char_uuid = bluetooth.UUID(BLE_CHAR_UUID)
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle,),) = self._ble.gatts_register_services((
            (svc_uuid, ((char_uuid, bluetooth.FLAG_NOTIFY | bluetooth.FLAG_READ),)),
        ))
        self._ble.gatts_write(self._handle, b'---')
        self._advertise()
        self.state = BLE_ADV
        print("BLE: activado, esperando conexion...")

    def deactivate(self):
        """Desconecta y apaga el módulo BLE."""
        try:
            if self._conn is not None:
                self._ble.gap_disconnect(self._conn)
        except:
            pass
        self._ble.active(False)
        self._conn = None
        self.state = BLE_OFF
        print("BLE: desactivado")

    def send(self, text):
        """Envía un texto por BLE. Devuelve True si se envió."""
        if self.state == BLE_CON and self._handle is not None:
            try:
                self._ble.gatts_notify(self._conn, self._handle, text.encode())
                return True
            except:
                pass
        return False

    def _irq(self, event, data):
        """Callback interno: responde a conexión y desconexión."""
        if event == _IRQ_CONNECT:
            self._conn = data[0]
            self.state = BLE_CON
            print("BLE: conectado")
        elif event == _IRQ_DISCONNECT:
            self._conn = None
            self.state = BLE_ADV
            self._advertise()
            print("BLE: desconectado, buscando...")

    def _advertise(self):
        """Construye el paquete de anuncio BLE y comienza a emitirlo."""
        payload = (
            bytes([2, 0x01, 0x06]) +
            bytes([len(BLE_NOMBRE) + 1, 0x09]) +
            BLE_NOMBRE
        )
        self._ble.gap_advertise(100_000, adv_data=payload)
