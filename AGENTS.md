# OrderFlow: Reglas del Negocio y Contexto de Desarrollo

## Cómo trabajar
- Base de datos: PostgreSQL configurado en .env (DATABASE_URL).
- Cambios de esquema: Crear migración con `alembic revision -m "desc"` y aplicar con `alembic upgrade head`. Nunca modificar la BD a mano.
- Pruebas y verificación: Ejecutar `pytest` y `python setup_db.py` según corresponda.
- Si algo no está especificado en este documento, no inventes reglas: usa el criterio mínimo o pregunta.

## Reglas de Negocio
### Precios (PRE)
PRE-01 | Precios salen exclusivamente del catálogo de productos. El sistema calcula los totales; el cliente no define precios.
PRE-02 | Descuento por volumen: si el subtotal de la orden es mayor a 500, se aplica un descuento de 10%. Un subtotal de exactamente 500 no recibe descuento.
PRE-03 | Cliente VIP: si el correo del cliente es de dominio @vip.com, recibe un 5% adicional calculado sobre el monto que ya tiene el descuento anterior, no sobre el subtotal original.
PRE-04 | Redondeo: todos los montos se calculan con Decimal y se redondean a centavos, con el medio centavo hacia arriba.

### Inventario (INV)
INV-01 | Los lotes de producto se asignan en estricto orden FIFO por fecha de caducidad (primero lo que caduca antes).
INV-02 | Lotes vencidos nunca se venden ni se asignan a órdenes bajo ninguna circunstancia.
INV-03 | El apartado es 'todo o nada'. Si falta inventario para algún ítem, la orden no se procesa ni se aparta parcialmente.
INV-04 | Al editar una orden, el nuevo apartado reemplaza al anterior solo si hay disponibilidad total; si no alcanza, el pedido queda intacto.
INV-05 | La existencia física en bodega solo disminuye cuando el pedido cambia a estado 'shipped', nunca al apartar ni al pagar.

### Pedidos (ORD)
ORD-01 | Una orden debe tener al menos 1 producto. Las cantidades son números enteros mayores a cero (qty >= 1).
ORD-02 | Todo pedido nuevo nace en estado 'pending'.
ORD-03 | Códigos HTTP: Devolver 404 Not Found si el producto o pedido no existe. Devolver 409 Conflict si la acción viola el estado de la orden.
ORD-04 | Edición de órdenes: una orden solo se puede editar mientras su estado sea PENDING, y al editar se recalcula todo (precios, descuentos y total).
ORD-05 | Plazo de pago: una orden solo se puede pagar dentro de las 24 horas posteriores a su creación. A las 24 horas exactas todavía se acepta; pasadas las 24 horas se rechaza con 409. Editar la orden no reinicia el plazo.
ORD-06 | Transiciones de estado: Solo se paga una orden 'pending'. Solo se envía una orden 'paid'. Estados finales 'shipped' y 'canceled' no pueden cambiar a ningún otro.
ORD-07 | Cancelación: Una orden 'pending' sí se cancela (cambia a 'canceled') y libera su inventario apartado. Una orden 'paid' sí se cancela: si se cancela dentro de las 24 horas siguientes al pago, se devuelve el 100% (refund_amount = total, penalty = 0); si transcurrieron más de 24 horas del pago, se retiene el 10% por penalización (penalty = 10% del total, refund_amount = 90% del total). Devuelve refund_amount y penalty y libera inventario apartado. Una orden 'shipped' NO se cancela bajo ninguna circunstancia (409 Conflict).
ORD-08 | Notificaciones: Se envía notificación únicamente al pagar ('paid') y al enviar ('shipped'). NUNCA enviar avisos o correos al cancelar.

### Envíos con la paquetería (SHP)
SHP-01 | Solo se pide el envío de una orden pagada (estado PAID). Una orden en cualquier otro estado se rechaza con conflicto (409 Conflict).
SHP-02 | Una orden tiene a lo más un envío en toda su vida, sin importar cuántas veces se pida o se reintente. La clave del envío es estrictamente 'envio-{order_id}' y no cambia entre reintentos.
SHP-03 | Un producto perecedero se envía solo si le quedan al menos 10 días de vida. Si no, el envío se rechaza con conflicto (409 Conflict) y la orden sigue pagada.
SHP-04 | Una orden solo se muestra como enviada (status = SHIPPED) si el proveedor entregó un número de guía válido (tracking_number).
SHP-05 | Si el proveedor falla o no se sabe qué pasó (timeout, 500, desconexión), la orden no se pierde ni se cobra de nuevo: sigue pagada (PAID) y queda registrada en UNKNOWN o PENDING_RETRY para volver a intentarse.
SHP-06 | Si el proveedor rechaza el envío de forma definitiva (4xx de datos no recuperables), la orden queda en PAID con shipping_status en FAILED y su motivo, y no se reintenta.
- Espera máxima por llamada: 2.0 segundos.
- Se reintenta solo: fallas transitorias (timeouts, 500, 502, 503, caídas). Nunca se reintenta: errores 4xx definitivos.
- Máximo 3 intentos, con retroceso exponencial (1s, 2s, 4s).
- La clave del envío es envio-{order_id} y no cambia entre reintentos.
- Una orden solo pasa a SHIPPED con una guía válida.
- Si no se sabe el resultado, la orden queda en UNKNOWN y no se pierde.

## Claude NO debe
- No inventar reglas de negocio ni asumir políticas comerciales ausentes en este documento.
- No modificar esquemas en Postgres directamente; utilizar siempre Alembic.
- No enviar notificaciones en acciones de cancelación.
- No descontar inventario físico de bodega antes del envío ('shipped').
- No permitir cancelar órdenes con estado 'shipped'.

## Pendientes conocidos
- La liberación automática de apartado tras 24 horas sin pago aún no está implementada en el sistema.
- Aún no se soportan envíos de productos altamente perecederos a otros estados.
