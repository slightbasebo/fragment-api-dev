"""Loopback-only synthetic Fragment API. No backend, wallets, or payments."""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MOCK_SEED = "mock-only-not-a-wallet"
SCENARIOS = {"completed", "failed", "429", "timeout", "reconciliation_required"}


class MockServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address=("127.0.0.1", 8081), *, timeout_delay=2.0):
        if address[0] not in {"127.0.0.1", "localhost"}:
            raise ValueError("Mock server must bind to loopback")
        self.orders = {}
        self.keys = {}
        self.attempts = {}
        self.lock = threading.Lock()
        self.timeout_delay = timeout_delay
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # Do not log request bodies, URLs, or wallet material.

    def send_json(self, status, value):
        raw = json.dumps(value).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            if status == 429:
                self.send_header("Retry-After", "2")
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            return self.send_json(200, {"status": "ok", "mock": True})
        if path == "/api/v1/prices":
            return self.send_json(
                200,
                {
                    "stars": {"amount": 50, "prices": {"gram": "1.00", "usdt": "2.00"}},
                    "premium": [
                        {"months": months, "prices": {"gram": "3.00", "usdt": "6.00"}}
                        for months in (3, 6, 12)
                    ],
                    "stale": False,
                },
            )
        if path == "/api/v1/prices/quote":
            query = parse_qs(urlsplit(self.path).query)
            try:
                amount = int(query.get("amount", ["50"])[0])
            except ValueError:
                return self.send_json(400, {"error": "Invalid amount"})
            return self.send_json(
                200,
                {
                    "product": query.get("product", ["stars"])[0],
                    "amount": amount,
                    "prices": {"gram": "1.00", "usdt": "2.00"},
                    "stale": False,
                },
            )
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "v1"] and parts[2] in {"purchases", "checkouts"}:
            with self.server.lock:
                order = self.server.orders.get(parts[3])
                if order and order["kind"] == parts[2]:
                    if order["status"] in {"queued", "submitted"}:
                        order["status"] = (
                            order["scenario"]
                            if order["scenario"] in {"failed", "reconciliation_required"}
                            else "completed"
                        )
                    return self.send_json(200, public(order))
        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError()
            value = json.loads(self.rfile.read(length))
            if not isinstance(value, dict):
                raise ValueError()
        except (ValueError, UnicodeError):
            return self.send_json(400, {"error": "Expected a small JSON object"})
        if "seed" in value and value["seed"] != MOCK_SEED:
            return self.send_json(400, {"error": "Mock accepts only the synthetic MOCK_SEED marker"})
        path = urlsplit(self.path).path
        if path == "/api/v1/availability/check":
            return self.send_json(
                200,
                {
                    "available": True,
                    "code": "AVAILABLE",
                    "message": "Synthetic recipient is available.",
                    "checked_at": "2026-01-01T00:00:00Z",
                },
            )
        if path == "/api/v1/wallets/resolve":
            return self.send_json(
                200,
                {
                    "wallet_address": "0:" + "0" * 64,
                    "wallet_version": "v5r1",
                    "account_index": 0,
                    "derivation_path": "synthetic",
                    "addresses": {"v4": "synthetic-v4", "v5r1": "synthetic-v5"},
                },
            )
        if path in {"/api/v1/purchases", "/api/v1/checkouts"}:
            return self.create(path.rsplit("/", 1)[1], value)
        parts = path.strip("/").split("/")
        if len(parts) == 5 and parts[:3] == ["api", "v1", "checkouts"] and parts[4] == "submitted":
            if set(value) != {"boc"} or value["boc"] != "c3ludGhldGlj":
                return self.send_json(400, {"error": "Mock requires synthetic BOC c3ludGhldGlj"})
            with self.server.lock:
                order = self.server.orders.get(parts[3])
                if not order or order["kind"] != "checkouts":
                    return self.send_json(404, {"error": "Not found"})
                if order["status"] == "awaiting_payment":
                    order["status"] = "submitted"
                return self.send_json(200, public(order))
        self.send_json(404, {"error": "Not found"})

    def create(self, kind, value):
        selection = {key: value.get(key) for key in ("product", "username", "amount", "payment_method")}
        key = value.get("idempotency_key")
        if (
            not isinstance(key, str)
            or not key
            or not isinstance(selection["username"], str)
            or selection["product"] not in ("stars", "premium")
            or type(selection["amount"]) is not int
            or selection["payment_method"] not in ("gram", "usdt")
            or (kind == "purchases" and value.get("seed") != MOCK_SEED)
            or (kind == "checkouts" and not value.get("payer_address"))
        ):
            return self.send_json(400, {"error": "Invalid synthetic purchase"})
        scenario = selection["username"].lstrip("@")
        scenario = scenario if scenario in SCENARIOS else "completed"
        # Store a digest, never request bodies or seed material.
        fingerprint = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        lookup = (kind, key)
        with self.server.lock:
            self.server.attempts[lookup] = self.server.attempts.get(lookup, 0) + 1
            attempt = self.server.attempts[lookup]
            previous = self.server.keys.get(lookup)
            if previous and previous[0] != fingerprint:
                return self.send_json(409, {"error": "Idempotency conflict", "code": "IDEMPOTENCY_CONFLICT"})
            if scenario == "429" and attempt == 1:
                return self.send_json(429, {"error": "Synthetic rate limit", "retry_after": 2})
            if previous:
                order = self.server.orders[previous[1]]
            else:
                identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, kind + ":" + key))
                order = {
                    **selection,
                    "id": identifier,
                    "kind": kind,
                    "scenario": scenario,
                    "status": "queued" if kind == "purchases" else "awaiting_payment",
                }
                self.server.orders[identifier] = order
                self.server.keys[lookup] = (fingerprint, identifier)
            response = public(order, prepared=kind == "checkouts")
        if scenario == "timeout" and attempt == 1:
            time.sleep(self.server.timeout_delay)  # Accepted first; caller loses the response.
        self.send_json(202 if kind == "purchases" else 200, response)


def public(order, *, prepared=False):
    value = {key: order[key] for key in ("product", "username", "amount", "payment_method", "status")}
    value["checkout_id" if order["kind"] == "checkouts" else "purchase_id"] = order["id"]
    value.update(
        transaction_hash="synthetic-transaction" if order["status"] == "completed" else None,
        error={"code": "SYNTHETIC_FAILURE", "message": "Mock scenario"}
        if order["status"] in {"failed", "reconciliation_required"}
        else None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    if prepared:
        value["tonconnect_transaction"] = {
            "validUntil": 1900000000,
            "messages": [{"address": "0:" + "0" * 64, "amount": "1", "payload": "c3ludGhldGlj"}],
        }
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    with MockServer(("127.0.0.1", args.port)) as server:
        print(f"Synthetic mock API: http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
