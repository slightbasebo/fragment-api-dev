import { randomUUID } from "node:crypto";

const baseUrl = process.env.FRAGMENT_API_URL ?? "https://api-stars.duckdns.org";
const seed = process.env.TON_WALLET_SEED;
if (!seed) throw new Error("Set TON_WALLET_SEED");

async function request(path, options) {
  const response = await fetch(`${baseUrl}${path}`, options);
  const body = await response.json();
  if (!response.ok) {
    throw new Error([body.code, body.error, body.action].filter(Boolean).join(": "));
  }
  return body;
}

const payload = {
  product: process.env.PRODUCT ?? "stars",
  username: process.env.TELEGRAM_USERNAME ?? "@telegram_user",
  amount: Number(process.env.AMOUNT ?? "50"),
  payment_method: process.env.PAYMENT_METHOD ?? "gram",
  seed,
  idempotency_key: process.env.IDEMPOTENCY_KEY ?? randomUUID(),
};

if (process.env.TON_WALLET_ADDRESS) {
  payload.wallet_address = process.env.TON_WALLET_ADDRESS;
}
if (process.env.TON_ACCOUNT_INDEX) {
  payload.account_index = Number(process.env.TON_ACCOUNT_INDEX);
}

const purchase = await request("/api/v1/purchases", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(payload),
});
console.log("Purchase:", purchase.purchase_id);

const terminal = new Set(["completed", "failed", "reconciliation_required"]);
let result = purchase;
while (!terminal.has(result.status)) {
  await new Promise((resolve) => setTimeout(resolve, 2000));
  result = await request(`/api/v1/purchases/${purchase.purchase_id}`);
}

console.log(result.status, result.transaction_hash ?? result.error);
