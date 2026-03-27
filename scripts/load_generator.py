#!/usr/bin/env python3
"""Load generator that sends POST /orders requests to the orders service."""

import json
import random
import sys
import time
from datetime import datetime, timezone

import urllib.request
import urllib.error

ORDERS_URL = "http://localhost:8081/orders"
REQUEST_INTERVAL_SECONDS = 2
SUMMARY_EVERY = 30

CUSTOMER_IDS = [f"CUST-{i:03d}" for i in range(1, 21)]
PRODUCT_IDS = [f"PROD-{i:03d}" for i in range(1, 6)]


def send_order():
    payload = {
        "customerId": random.choice(CUSTOMER_IDS),
        "productId": random.choice(PRODUCT_IDS),
        "quantity": random.randint(1, 5),
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        ORDERS_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed_ms = (time.time() - start) * 1000
            body = json.loads(resp.read().decode())
            return resp.status, elapsed_ms, body, payload
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.time() - start) * 1000
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {"error": str(e)}
        return e.code, elapsed_ms, body, payload
    except urllib.error.URLError as e:
        elapsed_ms = (time.time() - start) * 1000
        return 0, elapsed_ms, {"error": str(e.reason)}, payload
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return 0, elapsed_ms, {"error": str(e)}, payload


def print_summary(stats):
    total = stats["total"]
    if total == 0:
        return
    success_pct = (stats["success"] / total) * 100
    fail_pct = (stats["failure"] / total) * 100
    avg_ms = stats["total_ms"] / total
    print("\n" + "=" * 60)
    print(f"  SUMMARY (last {total} requests)")
    print(f"  Success: {stats['success']}/{total} ({success_pct:.1f}%)")
    print(f"  Failed:  {stats['failure']}/{total} ({fail_pct:.1f}%)")
    print(f"  Errors:  {stats['errors']}/{total}")
    print(f"  Avg latency: {avg_ms:.0f}ms")
    print(f"  Min latency: {stats['min_ms']:.0f}ms")
    print(f"  Max latency: {stats['max_ms']:.0f}ms")
    print("=" * 60 + "\n")


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Load generator started")
    print(f"  Target: {ORDERS_URL}")
    print(f"  Interval: {REQUEST_INTERVAL_SECONDS}s")
    print(f"  Summary every {SUMMARY_EVERY} requests\n")

    request_num = 0
    stats = {"total": 0, "success": 0, "failure": 0, "errors": 0,
             "total_ms": 0, "min_ms": float("inf"), "max_ms": 0}

    try:
        while True:
            request_num += 1
            status, elapsed_ms, body, payload = send_order()

            stats["total"] += 1
            stats["total_ms"] += elapsed_ms
            stats["min_ms"] = min(stats["min_ms"], elapsed_ms)
            stats["max_ms"] = max(stats["max_ms"], elapsed_ms)

            if status == 0:
                stats["errors"] += 1
                marker = "ERR"
            elif 200 <= status < 300:
                stats["success"] += 1
                marker = "OK "
            else:
                stats["failure"] += 1
                marker = "FAIL"

            order_id = body.get("id", body.get("orderId", "n/a"))
            order_status = body.get("status", body.get("error", "n/a"))

            print(f"[{marker}] #{request_num:04d} | {status} | {elapsed_ms:7.0f}ms | "
                  f"product={payload['productId']} qty={payload['quantity']} | "
                  f"order={order_id} status={order_status}")

            if stats["total"] % SUMMARY_EVERY == 0:
                print_summary(stats)
                stats = {"total": 0, "success": 0, "failure": 0, "errors": 0,
                         "total_ms": 0, "min_ms": float("inf"), "max_ms": 0}

            time.sleep(REQUEST_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print(f"\n[{datetime.now(timezone.utc).isoformat()}] Load generator stopped after {request_num} requests")
        if stats["total"] > 0:
            print_summary(stats)
        sys.exit(0)


if __name__ == "__main__":
    main()
