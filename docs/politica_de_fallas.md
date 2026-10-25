# Política de Fallas y Resiliencia en Envíos: OrderFlow API
**Proyecto:** OrderFlow API  
**Fase:** Fase 2 - Política de Fallas (Clase 7)  
**Fecha:** 2026-10-25  

---

## 1. Tabla de Política de Fallas ante el Proveedor de Paquetería

**Tiempo máximo total dispuesto a esperar al proveedor:** 7 segundos acumulados por ciclo de sincronización.

| Situación | ¿Se reintenta? | Cuántas veces y con qué espera | Estado en que queda la orden | Qué ve el usuario |
| :--- | :--- | :--- | :--- | :--- |
| **1. Timeout de conexión o lectura (> 2.0s)** | Sí | 3 intentos con espera exponencial (1 s, 2 s, 4 s) usando `Idempotency-Key` fija | `PAID` (shipping_status: `UNKNOWN`) | "Tu pedido está pagado. La paquetería tarda en responder; estamos gestionando tu guía de envío." |
| **2. Error de servidor 500 / 502 / 503 (Caída temporal)** | Sí | 3 intentos con retroceso exponencial (1 s, 2 s, 4 s) | `PAID` (shipping_status: `PENDING_RETRY`) | "Tu pago fue recibido exitosamente. La paquetería reporta saturación; reintentaremos en unos momentos." |
| **3. Error 400 Bad Request por datos no recuperables (ej. peso fuera de rango)** | No | 0 reintentos (fallo definitivo de validación) | `PAID` (shipping_status: `FAILED`) | "No fue posible procesar el envío debido a un problema con los datos del paquete. Soporte revisará tu orden." |
| **4. Respuesta con cuerpo corrupto o JSON roto (JSONDecodeError)** | Sí | 2 intentos previa consulta de verificación (`GET /v1/envios?referencia=...`) esperando 1 s y 2 s | `PAID` (shipping_status: `UNKNOWN`) | "Tu pedido está pagado y estamos validando la asignación de tu guía con la paquetería." |
| **5. Respuesta exitosa 200/201 pero sin número de guía válido (guía nula o vacía)** | Sí | 2 intentos consultando el estado por referencia esperando 1 s y 2 s | `PAID` (shipping_status: `PENDING_RETRY`) | "Tu pedido está pagado. Esperando confirmación de la guía por parte de la paquetería." |

---

## 2. Registro de Decisión de Arquitectura (ADR): Resiliencia e Idempotencia en Envíos

### 1. La Decisión (qué se reintenta y cómo)
* **Idempotencia fija obligatoria:** Todas las peticiones `POST /v1/envios` deben incluir obligatoriamente el encabezado HTTP `Idempotency-Key: envio-{order_id}`. Esta clave es estrictamente inmutable entre reintentos para evitar que una desconexión o reintento genere guías duplicadas o cobros adicionales.
* **Manejo de reintentos y timeouts:** Timeout por llamada de 2.0 segundos. Reintentar únicamente ante fallas transitorias (timeouts, desconexiones, 500, 502, 503) hasta un máximo de 3 intentos con retroceso exponencial (1s, 2s, 4s).
* **Consistencia de estados:** Una orden solo transiciona a `SHIPPED` si el proveedor devuelve un `tracking_number` válido. Si la llamada falla o el resultado es incierto, la orden jamás se pierde ni se cobra de nuevo: permanece en `PAID` con `shipping_status` en `PENDING_RETRY` o `UNKNOWN`. Si el rechazo es definitivo (4xx irrecuperable), queda en `FAILED`.

### 2. La Alternativa Descartada y por qué
* Se descartó el **reintento agresivo inmediato en bucle** (reintentar 5 a 10 veces seguidas sin tiempo de espera).
* **Razón técnica:** Reintentar sin pausa satura y amplifica la caída del proveedor (*efecto estampida / thundering herd*), y si la red sufre pérdida de paquetes, incrementa exponencialmente el riesgo de duplicación de guías en la paquetería.

### 3. La Consecuencia que se Acepta
* Se acepta que en periodos de degradación severa o caída de la paquetería externa, la orden no transicione inmediatamente a `SHIPPED`, manteniéndose en `PAID` con estado pendiente hasta que un proceso de reintento confirme la guía válida.
