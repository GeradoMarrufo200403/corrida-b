import logging
import os
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

CARRIER_BASE_URL = os.getenv("CARRIER_URL", "http://localhost:9100")


@dataclass
class ShippingResult:
    status: str  # PAID o SHIPPED
    shipping_status: str  # SHIPPED, PENDING_RETRY, UNKNOWN, FAILED
    tracking_number: str | None = None
    error: str | None = None


# Decisión 2 de auditoría: valores por defecto para destino y paquete
DEFAULT_CITY = "Merida"
DEFAULT_CP = "97000"
DEFAULT_WEIGHT_KG = 1.0


class CarrierClient:
    """Cliente para la paquetería externa con idempotencia y retroceso exponencial."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or CARRIER_BASE_URL).rstrip("/")

    def request_shipping(self, order_id: int) -> ShippingResult:
        url = f"{self.base_url}/v1/envios"
        headers = {
            "Content-Type": "application/json",
            "Idempotency-Key": f"envio-{order_id}",
        }
        payload = {
            "referencia": str(order_id),
            "destino": {"ciudad": DEFAULT_CITY, "cp": DEFAULT_CP},
            "peso_kg": DEFAULT_WEIGHT_KG,
        }

        # Intentos con retroceso exponencial (1s, 2s, 4s)
        backoffs = [1.0, 2.0, 4.0]
        last_exception = None

        for attempt, delay in enumerate(backoffs, start=1):
            try:
                # Decisión 1 de auditoría: timeouts separados (connect=1.0s, read=2.0s)
                response = requests.post(
                    url, json=payload, headers=headers, timeout=(1.0, 2.0)
                )

                # Éxito (200 o 201)
                if response.status_code in (200, 201):
                    try:
                        data = response.json()
                        guia = data.get("guia")
                        if guia:
                            return ShippingResult(
                                status="SHIPPED",
                                shipping_status="SHIPPED",
                                tracking_number=guia,
                            )
                        logger.warning(
                            "Intento %d: paquetería respondió HTTP %d pero sin guía",
                            attempt,
                            response.status_code,
                        )
                        last_exception = Exception("respuesta_sin_guia")
                    except ValueError as json_err:
                        logger.warning(
                            "Respuesta con JSON corrupto de paquetería: %s", json_err
                        )
                        # JSON roto pero conexión exitosa -> estado UNKNOWN
                        return ShippingResult(
                            status="PAID",
                            shipping_status="UNKNOWN",
                            tracking_number=None,
                            error="json_corrupto",
                        )

                # Rechazo definitivo por validación (4xx)
                if 400 <= response.status_code < 500:
                    err_msg = response.text or "rechazo_definitivo"
                    logger.error("Paquetería rechazó envío: %s", err_msg)
                    return ShippingResult(
                        status="PAID",
                        shipping_status="FAILED",
                        tracking_number=None,
                        error=err_msg,
                    )

                # Errores de servidor (5xx) -> reintentar si quedan intentos
                logger.warning(
                    "Intento %d: paquetería devolvió HTTP %d",
                    attempt,
                    response.status_code,
                )

            except requests.exceptions.Timeout as timeout_err:
                last_exception = timeout_err
                logger.warning(
                    "Intento %d: timeout al llamar paquetería: %s", attempt, timeout_err
                )
            except requests.exceptions.RequestException as req_err:
                last_exception = req_err
                logger.warning(
                    "Intento %d: error de red con paquetería: %s", attempt, req_err
                )

            # Esperar antes del siguiente reintento si no es el último
            if attempt < len(backoffs):
                time.sleep(delay)

        # Si se agotaron los reintentos ante timeout o 5xx
        is_timeout = isinstance(last_exception, requests.exceptions.Timeout)
        final_shipping_status = "UNKNOWN" if is_timeout else "PENDING_RETRY"

        return ShippingResult(
            status="PAID",
            shipping_status=final_shipping_status,
            tracking_number=None,
            error=str(last_exception) if last_exception else "reintentos_agotados",
        )
