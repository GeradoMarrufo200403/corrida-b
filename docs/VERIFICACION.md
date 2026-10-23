# Reporte de Verificación y Defensas: OrderFlow API
**Estudiante:** Gerardo Marrufo  
**Proyecto:** OrderFlow API (Clase 6 - Actividad 1: Sabotaje a OrderFlow)  
**Fecha:** 2026-10-23  

---

## 1. Nuestras Defensas (Una línea por capa)
* **Capa 1 (El Escudo):** Suite de 8 pruebas en `tests/test_precios_escudo.py` sobre PostgreSQL real y reloj inyectable (`FixedClock`), con valores esperados derivados estrictamente de las 5 reglas de negocio de `AGENTS.md`.
* **Capa 2 (Obligar - Hook Stop):** Hook configurado en `.claude/settings.json` y `.claude/hooks/verificar.sh` que ejecuta `ruff check .` y la suite del escudo, frena con código de salida 2 devolviendo stderr ante fallos, evita bucles y registra `PASO` o `BLOQUEO` en `.claude/verificacion.log`.
* **Capa 3 (Revisor Independiente):** Subagente `revisor-de-reglas` con permisos exclusivos de solo lectura (`Read`, `Grep`, `Glob`) que audita `git diff` contra `AGENTS.md` bajo el formato estricto *Problema, Evidencia, Riesgo, Recomendación*.

---

## 2. Marcador de los 4 Sabotajes y Evidencias
A continuación se presenta el resultado observable tras someter las capas de defensa a los 4 ataques de sabotaje:

| Sabotaje | Capa que lo atrapó | Evidencia (Línea del log y capturas) | Qué aprendí |
| :--- | :--- | :--- | :--- |
| **M1:** Descuento por volumen aplica también en subtotal == 500 (cambiar `>` por `>=`) | **Capa 1 y 2** (Pruebas del escudo y Hook) | Log: `BLOQUEO` (`E3.M1b`). Falla `test_volumen_limite_exacto_500_sin_descuento`. Captura: `E3.M1a`, `E3.M1b`. | Las pruebas de límite estricto (*boundary testing*) son indispensables en reglas comerciales para evitar fugas de margen en umbrales exactos. |
| **M2:** 5% VIP calculado sobre subtotal original y no sobre monto con descuento | **Capa 1 y 2** (Pruebas del escudo y Hook) | Log: `BLOQUEO` (`E3.M2b`). Falla `test_cliente_vip_descuento_compuesto`. Captura: `E3.M2a`, `E3.M2b`. | El cálculo de descuentos compuestos requiere aserciones exactas para evitar inconsistencias contables en clientes preferenciales. |
| **M3:** Redondeo cambiado a par más cercano (`ROUND_HALF_EVEN`) en lugar de half-up | **Capa 1 y 2** (Pruebas del escudo y Hook) | Log: `BLOQUEO` (`E3.M3b`). Falla `test_redondeo_medio_centavo_hacia_arriba`. Captura: `E3.M3a`, `E3.M3b`. | La regla financiera de redondeo hacia arriba en medios centavos (`.005`) debe contrastarse contra el redondeo bancario por defecto de Python. |
| **M4:** Plazo de 24h para pagar se reinicia al editar la orden | **Capa 3** (Subagente Revisor). *Se escapó de las pruebas.* | Log: `PASO` (`E3.M4b`). Revisor detectó violación a regla `ORD-05` (`E3.M4c`). | El límite de 8 pruebas dejó fuera el caso combinado de edición y plazo; la revisión estructural de diffs por un agente aislado salvó al negocio. |

---

## 3. Lo que se Escapó y la Prueba que lo Cierra
* **Lo que se escapó:** El sabotaje **M4** introdujo la línea `order.created_at = self.clock.now()` dentro del método `update_items` en `app/orders/service.py`. Esto permitía que un cliente que editara su orden a las 20 horas pudiera pagarla a las 25 horas desde la creación original, violando la regla `ORD-05`.
* **Por qué se escapó:** Para cumplir con la restricción de diseño de máximo 8 pruebas en `tests/test_precios_escudo.py`, se priorizaron los límites directos de volumen, VIP, redondeo, edición y vencimiento simple de 24h, descartando el caso adversarial combinado (caso C12).
* **Prueba que lo cierra:** Se implementó `test_edicion_no_reinicia_plazo_de_pago_de_24h` en `tests/test_regresiones.py`. Dicha prueba crea una orden en $T_0$, la edita a las 20 horas y avanza el reloj a las 25 horas totales ($T_0 + 25\text{h}$). Con el sabotaje activo la prueba falla (`E4.1`), y con el código limpio pasa exitosamente exigiendo `409 Conflict` (`E4.2`).

---

## 4. Dos Cosas que Nuestras Defensas No Cubren
1. **Liberación automática de inventario apartado expirado:** El sistema valida y bloquea pagos pasadas las 24 horas con `409 Conflict`, pero no existe un mecanismo activo (proceso cron o tarea asíncrona en segundo plano) que libere automáticamente las reservas en la tabla `lots` si el cliente abandona la orden sin intentar pagar.
2. **Restricciones geográficas y de transporte para productos perecederos:** La base de datos clasifica productos perecederos (`perishable`), pero las capas actuales no validan el destino del envío ni bloquean traslados interestatales que comprometan la caducidad del chocolate.

---

## 5. Justificación de Elección (Skill vs Subagente) y Tabla de Ajustes

### ¿Por qué elegí Subagente en lugar de Skill?
> *Elegí un **subagente** (`revisor-de-reglas`) porque permite aplicar con rigor el principio de menor privilegio, restringiendo sus herramientas a solo lectura (`Read`, `Grep`, `Glob`), evitando que la IA modifique accidentalmente el código o las pruebas durante la auditoría.*

### Tabla 3.8 — Tabla de ajustes de su AGENTS.md
| Regla (con sus palabras) | Estado en mi AGENTS.md | Qué hice |
| :--- | :--- | :--- |
| **Descuento por volumen:** subtotal > 500 aplica 10%; subtotal == 500 no recibe descuento. | Ya estaba igual (en PRE-02) | Mantuve la regla y reforcé la etiqueta explícita de la sección 3.1.1. |
| **Cliente VIP:** correo `@vip.com` recibe 5% adicional compuesto sobre el monto con descuento previo. | Ya estaba igual (en PRE-03) | Mantuve la regla y reforcé la etiqueta explícita de la sección 3.1.1. |
| **Redondeo:** montos con `Decimal` y redondeo a centavos hacia arriba (`ROUND_HALF_UP`). | Decía algo distinto (en PRE-04 hablaba de fracción de medio centavo). | Reemplacé el texto por la redacción oficial exacta de la sección 3.1.1. |
| **Edición de órdenes:** solo se edita en `PENDING` y al editar se recalcula todo. | Decía algo distinto (estaba combinada con el plazo en ORD-04). | Separé la regla en ORD-04 con la redacción oficial de la sección 3.1.1. |
| **Plazo de pago:** pago dentro de 24h de creación; 24h exactas se acepta; pasadas 24h rechaza con 409. Editar no reinicia. | Decía algo distinto (no explicitaba las 24 horas exactas ni el código 409). | Creé la regla ORD-05 dedicada con el texto exacto de la sección 3.1.1. |

### Defectos previos corregidos
* Se ajustaron advertencias de linter con `ruff check --fix .` en los archivos de migración y configuración de esquema inicial.
* Se agregó `pytest.ini` con `pythonpath = .` para garantizar la resolución adecuada del módulo `app` al correr pytest en entornos limpios.
