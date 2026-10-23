# Clase 6. Actividad 1. Prompts de la Fase 3

**Práctica evaluatoria individual (100 puntos).** Unidad II. IA como colaborador configurado (Sesión 2 de 4).

> Este archivo se entrega cuando el profesor lo indica. No lo busque ni aplique sus prompts antes. Siga el procedimiento de la sección 3.4 del documento de la actividad.

## Cómo se usa

Para cada uno de los cuatro prompts, en este orden:

1. Abra una sesión nueva de Claude Code con el mismo modelo y esfuerzo de siempre: `claude --model claude-sonnet-5-5 --effort medium`.
2. Pegue el prompt tal cual, sin cambiarle una sola palabra.
3. Mire la última línea de `.claude/verificacion.log`. BLOQUEO significa que su suite lo detectó y el hook lo frenó. PASO significa que se escapó de las dos primeras capas.
4. Si se escapó, invoque su revisor sobre `git diff`.
5. Registre el resultado en la tabla 3.10 y pegue sus capturas en las indicaciones E3 del documento.
6. Ejecute `git checkout -- .` para volver a su commit del escudo antes del siguiente prompt.

No corrija el código en esta fase. Si Claude se niega a hacer el cambio o lo modifica, no insista: capture lo que respondió, anótelo y siga con el siguiente. Su análisis se califica, no la suerte.

## Prompt M1

```
Haz un solo cambio en la lógica de precios de OrderFlow: el descuento por volumen de 10% debe aplicarse también cuando el subtotal sea exactamente 500, no solo cuando sea mayor a 500. No cambies nada más. No modifiques, borres ni agregues pruebas. Al terminar dime en qué archivo y en qué línea hiciste el cambio.
```

## Prompt M2

```
Haz un solo cambio en la lógica de precios de OrderFlow: el 5% adicional del cliente VIP debe calcularse sobre el subtotal original de la orden, en lugar de calcularse sobre el monto que ya tiene aplicado el descuento por volumen. No cambies nada más. No modifiques, borres ni agregues pruebas. Al terminar dime en qué archivo y en qué línea hiciste el cambio.
```

## Prompt M3

```
Haz un solo cambio en la lógica de precios de OrderFlow: el redondeo a centavos debe usar redondeo al par más cercano (ROUND_HALF_EVEN) en lugar de redondear el medio centavo hacia arriba. No cambies nada más. No modifiques, borres ni agregues pruebas. Al terminar dime en qué archivo y en qué línea hiciste el cambio.
```

## Prompt M4

```
Haz un solo cambio en la lógica de órdenes de OrderFlow: cuando una orden se edita, el plazo de 24 horas para pagarla debe contarse desde el momento de la última edición, en lugar de contarse desde la creación de la orden. No cambies nada más. No modifiques, borres ni agregues pruebas. Al terminar dime en qué archivo y en qué línea hiciste el cambio.
```

## Recordatorio de entrega

Cada prompt tiene tres indicaciones de captura en el documento (E3.M1a a E3.M4c): el prompt pegado con la respuesta de Claude, el resultado del hook con la última línea del log, y la salida del revisor si el cambio se escapó de las pruebas. Un paso sin captura no suma los puntos de su criterio.
