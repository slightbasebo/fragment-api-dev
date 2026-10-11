const baseUrl = process.env.FRAGMENT_API_URL ?? "https://api-stars.duckdns.org";
async function request(path, options) {
  const response = await fetch(`${baseUrl}${path}`, { ...options, signal: AbortSignal.timeout(30000) });
  const body = await response.json();
  if (!response.ok) {
    throw new Error([body.code, body.error, body.action].filter(Boolean).join(": "));
  }
  return body;
}

const purchaseFields = {
  product: process.env.PRODUCT ?? "stars",
  username: process.env.TELEGRAM_USERNAME ?? "@telegram_user",
  amount: Number(process.env.AMOUNT ?? "50"),
  payment_method: process.env.PAYMENT_METHOD ?? "gram",
};

const availability = await request("/api/v1/availability/check", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(purchaseFields),
});
if (!availability.available) {
  console.error(availability.message, availability.action ?? "");
  process.exit(2);
}

const seed = process.env.TON_WALLET_SEED;
if (!seed) throw new Error("Set TON_WALLET_SEED");

const payload = {
  ...purchaseFields,
  seed,
  idempotency_key: process.env.IDEMPOTENCY_KEY ?? process.env.SHOP_ORDER_ID,
};

if (process.env.TON_WALLET_ADDRESS) {
  payload.wallet_address = process.env.TON_WALLET_ADDRESS;
}
if (process.env.TON_ACCOUNT_INDEX) {
  payload.account_index = Number(process.env.TON_ACCOUNT_INDEX);
}

if (!payload.idempotency_key) throw new Error("Set SHOP_ORDER_ID to a stable shop order ID");

const purchase = await request("/api/v1/purchases", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(payload),
});
console.log("Purchase:", purchase.purchase_id);

const terminal = new Set(["completed", "failed", "reconciliation_required"]);
let result = purchase;
const deadline = Date.now() + 300000;
while (!terminal.has(result.status)) {
  if (Date.now() >= deadline) {
    throw new Error(`Status check timed out. Resume purchase ${purchase.purchase_id}; do not create a new order.`);
  }
  await new Promise((resolve) => setTimeout(resolve, 2000));
  result = await request(`/api/v1/purchases/${purchase.purchase_id}`);
}

console.log(result.status, result.transaction_hash ?? result.error);
