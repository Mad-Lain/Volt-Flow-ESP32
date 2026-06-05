# VoltFlow ESP32 – TODO

## Hardware pendiente

- [ ] **Tercer rango de medición (15 kΩ – 100 kΩ)**
  - Requiere resistencia de 47 kΩ (conseguir el componente)
  - Requiere espacio libre en la protoboard (sin puentes)
  - Cambios en: `config.py`, `medicion.py`, `calibrar.py`

---

## Firmware ESP32

- [ ] **Activar BLE automáticamente al arrancar**
  - Llamar `ble.activate()` antes del loop en `main.py`
  - Útil cuando el dispositivo siempre está conectado a la app

- [ ] **Soporte de tercer rango**
  - Implementar cuando esté disponible el hardware

---

## Seguridad BLE

- [ ] **Emparejamiento por PIN (Passkey Entry)**
  - El ESP32 genera un código de 6 dígitos y lo muestra en el OLED
  - El usuario lo ingresa en la app VoltFlow para autorizar la conexión
  - Una vez emparejados el bonding se guarda; reconexiones futuras son automáticas
  - Implementación en ESP32: manejar `_IRQ_PASSKEY_ACTION` en `ble_volt.py`
  - Implementación en Flutter: usar el flujo de pairing de `flutter_blue_plus`
  - Evita que dispositivos no autorizados lean las mediciones

- [ ] **Validación de datos entrantes**
  - Actualmente el ESP32 solo envía datos (notify), nunca recibe comandos
  - Si en el futuro se agrega una característica de escritura desde la app,
    validar que los datos recibidos sean texto plano con formato esperado
    y descartar cualquier otro contenido

---

## App Flutter (VoltFlow)

- [ ] Pendiente de definir

---

## VoltFlow v2 — Mejoras futuras (post-intro)

- [ ] **Modo SERIE — rango extendido con 2 GPIOs**
  - Usar dos GPIOs libres (ej. GPIO32 y GPIO33) con topología serie:
    `GPIO_A ──Ra── nodo_medio ──Rb── Nodo A` y `GPIO_B → nodo_medio` (bypass Ra)
  - GPIO_A=HIGH, GPIO_B=INPUT → Ra+Rb en serie (rango muy alto)
  - GPIO_B=HIGH, GPIO_A=INPUT → solo Rb (rango normal)
  - El switch GPIO17 ciclaría: RES → D/L → SERIE
  - Nueva función `leer_serie()` en `medicion.py`, constantes `R_SERIE_A/B` en `config.py`
  - Requiere actualizar `calibrar.py` (etapa 4) y animación OLED para el nuevo modo
  - Diseñado como "VoltFlow v2" — no rompe el flujo intro para estudiantes
