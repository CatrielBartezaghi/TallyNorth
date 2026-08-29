# TallyNorth como ChatGPT Action

TallyNorth expone un OpenAPI curado para que un GPT privado pueda consultar y operar finanzas personales sin acceder al OpenAPI general del backend.

## OpenAPI público

Importar únicamente:

```text
https://TU_DOMINIO/api/v1/integrations/chatgpt/openapi.json
```

La versión 3 del contrato incluye flujo de caja, cuentas, recurrentes, inversiones y objetivos.

## Consultas

- `getFinanceContext`: IDs válidos de cuentas, categorías, tarjetas y monedas.
- `getFinancialSummary`: KPIs y dashboard financiero.
- `getCashflowProjection`: proyección de flujo de caja.
- `searchFinanceEntries`: movimientos y compras.
- `getUpcomingInstallments`: cuotas.
- `listRecurringEntries`: reglas recurrentes.
- `getAccountBalances`: saldos actuales.
- `listInvestments`: cartera actual, costo, cantidad, valuación y resultado realizado.
- `listInvestmentOperations`: historial de compras, ventas, dividendos, intereses y comisiones.
- `listInvestmentValuations`: historial de valuaciones de una posición.
- `listSavingGoals`: objetivos y asignaciones patrimoniales.

## Escrituras

### Finanzas generales

- `createTransaction`
- `createRecurringEntry`
- `createCreditCardPurchase`
- `createFinanceEntriesBatch`
- `setAccountBalance`
- `createCategory`

### Objetivos

- `createSavingGoal`
- `updateSavingGoalProgress`
- `allocateSavingGoal`

Una meta no es un activo adicional. Si tiene asignaciones, su progreso se deriva de las cuentas o inversiones asignadas y no se suma otra vez al patrimonio.

### Inversiones

- `createInvestmentAsset`: crea el activo/posición; acepta monto, cantidad y valuación inicial para migrar tenencias existentes.
- `createInvestmentOperation`: registra `buy`, `sell`, `dividend`, `interest` o `fee`.
- `recordInvestmentValuation`: agrega una valuación histórica y actualiza el valor vigente.

Las compras y ventas vinculadas a una cuenta son transferencias patrimoniales: modifican el saldo de la cuenta y la inversión, pero no se contabilizan como gasto/ingreso. Dividendos e intereses sí forman parte del ingreso; comisiones puras forman parte del gasto.

## Reglas del ledger de inversiones

Cada `Investment` representa una posición. El historial se conserva en `InvestmentOperation` y `InvestmentValuation`.

Para activos con unidades, enviar `quantity` y `unit_price` juntos, y `amount` debe coincidir aproximadamente con `quantity * unit_price`.

Ejemplo de compra:

```json
{
  "idempotency_key": "buy-spy-20260829-01",
  "investment_id": "UUID_INVERSION",
  "type": "buy",
  "account_id": "UUID_CUENTA_USD",
  "quantity": 3,
  "unit_price": 650,
  "amount": 1950,
  "fee": 2.5,
  "date": "2026-08-29",
  "notes": "Compra en broker"
}
```

Para fondos o renta fija sin unidades conocidas, `quantity` y `unit_price` pueden omitirse y `amount` representa el importe de la operación.

La cuenta vinculada debe usar la misma moneda que la inversión. Las conversiones implícitas quedan fuera de una única operación para evitar inventar tipos de cambio.

## Valuaciones

Las valuaciones son append-only:

```json
{
  "idempotency_key": "valuation-spy-20260829",
  "investment_id": "UUID_INVERSION",
  "value": 2180.25,
  "valuation_date": "2026-08-29",
  "source": "manual"
}
```

Actualizar una valuación no destruye el historial anterior.

## Objetivos y asignaciones

Una cuenta o inversión puede repartirse entre varios objetivos, pero la suma de sus porcentajes no puede superar 100%.

```json
{
  "idempotency_key": "goal-house-spy-01",
  "saving_goal_id": "UUID_META",
  "investment_id": "UUID_INVERSION",
  "allocation_percent": 50
}
```

Debe enviarse exactamente uno de `account_id` o `investment_id`.

## Autenticación y scopes

Los tokens de integración usan prefijo `tn_gpt_` y son revocables. Los scopes relevantes son:

```text
context:read
transactions:create
purchases:create
budgets:write
saving_goals:write
investments:write
installments:pay
```

## Confirmación e idempotencia

Antes de cualquier escritura, el GPT debe mostrar un resumen exacto y pedir confirmación explícita.

Cada escritura usa una `idempotency_key`. Un reintento con la misma clave y exactamente los mismos datos devuelve `already_processed`; reutilizar la clave con otros datos devuelve conflicto.

No afirmar que una operación fue guardada hasta recibir una respuesta exitosa.

## Instrucciones sugeridas para el GPT

```text
Sos el asistente financiero operativo de TallyNorth.

CONSULTAS
- Resolvé IDs con getFinanceContext y las operaciones de listado. Nunca inventes IDs.
- Para inversiones, usá listInvestments, listInvestmentOperations y listInvestmentValuations.
- Para metas, usá listSavingGoals.

ESCRITURAS
- Pedí confirmación explícita antes de escribir.
- Gastos/ingresos comunes: createTransaction.
- Recurrentes: createRecurringEntry.
- Compras de tarjeta: createCreditCardPurchase.
- Crear activo: createInvestmentAsset.
- Comprar/vender/cobrar dividendos/intereses/comisiones: createInvestmentOperation.
- Actualizar valor de mercado: recordInvestmentValuation.
- Crear meta: createSavingGoal.
- Asociar patrimonio a una meta: allocateSavingGoal.

INVERSIONES
- Una compra/venta desde una cuenta NO es gasto/ingreso: es una transferencia patrimonial.
- No uses createTransaction para representar una compra o venta de inversión.
- Si cantidad y precio unitario son conocidos, enviá ambos.
- Si sólo se conoce el importe de un fondo/renta fija, omití cantidad/precio.
- No inventes precios, cantidades, comisiones ni tipos de cambio.

IDEMPOTENCIA
- Generá una clave nueva por operación confirmada.
- Reutilizala solamente para reintentar exactamente la misma solicitud.
```

## Casos de prueba recomendados

1. Crear un activo vacío y registrar una compra desde una cuenta.
2. Verificar que el saldo de la cuenta disminuya pero el dashboard no registre un gasto.
3. Reintentar la misma compra con idéntica idempotency key y comprobar que no se duplique.
4. Registrar una valuación y comprobar que quede en el historial.
5. Registrar un dividendo y comprobar que aumente el saldo y el ingreso financiero.
6. Registrar una venta parcial y comprobar cantidad, costo abierto y resultado realizado.
7. Crear una meta y asignarle parte de una inversión.
8. Confirmar que la meta no incremente el KPI de patrimonio.
9. Intentar asignar más de 100% de un activo entre metas y esperar 422.
10. Probar acceso con un token sin `investments:write` o `saving_goals:write`.
