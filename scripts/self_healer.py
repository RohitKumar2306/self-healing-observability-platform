#!/usr/bin/env python3
"""Self-healing agent that monitors microservice health and auto-restarts failed containers."""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

import urllib.request
import urllib.error

SERVICES = [
    {"name": "orders-service", "url": "http://localhost:8081/actuator/health"},
    {"name": "inventory-service", "url": "http://localhost:8082/actuator/health"},
    {"name": "payments-service", "url": "http://localhost:8083/actuator/health"},
]

CHECK_INTERVAL_SECONDS = 30
FAILURE_THRESHOLD = 2
REQUEST_TIMEOUT_SECONDS = 5


def log(level, service, message, **extra):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": "self-healer",
        "target": service,
        "message": message,
    }
    entry.update(extra)
    print(json.dumps(entry), flush=True)


def check_health(service_name, url):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode())
            status = body.get("status", "UNKNOWN")
            if resp.status == 200 and status == "UP":
                return True, status
            return False, status
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, str(e.reason)
    except Exception as e:
        return False, str(e)


def restart_container(service_name):
    log("WARN", service_name, "Restarting container")
    try:
        result = subprocess.run(
            ["docker", "restart", service_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            log("INFO", service_name, "Container restarted successfully")
            return True
        else:
            log("ERROR", service_name, "Failed to restart container", stderr=result.stderr.strip())
            return False
    except subprocess.TimeoutExpired:
        log("ERROR", service_name, "Restart command timed out")
        return False
    except FileNotFoundError:
        log("ERROR", service_name, "Docker CLI not found")
        return False


def main():
    consecutive_failures = {svc["name"]: 0 for svc in SERVICES}
    restart_counts = {svc["name"]: 0 for svc in SERVICES}

    log("INFO", "all", "Self-healer started", interval=CHECK_INTERVAL_SECONDS, threshold=FAILURE_THRESHOLD)

    try:
        while True:
            for svc in SERVICES:
                name = svc["name"]
                healthy, detail = check_health(name, svc["url"])

                if healthy:
                    if consecutive_failures[name] > 0:
                        log("INFO", name, "Service recovered", previous_failures=consecutive_failures[name])
                    consecutive_failures[name] = 0
                    log("INFO", name, "Health check passed", status=detail)
                else:
                    consecutive_failures[name] += 1
                    log("WARN", name, "Health check failed",
                        status=detail,
                        consecutive_failures=consecutive_failures[name])

                    if consecutive_failures[name] >= FAILURE_THRESHOLD:
                        log("ERROR", name, "Failure threshold reached, triggering restart",
                            consecutive_failures=consecutive_failures[name])
                        success = restart_container(name)
                        if success:
                            restart_counts[name] += 1
                            consecutive_failures[name] = 0
                            log("INFO", name, "Restart complete, counter reset",
                                total_restarts=restart_counts[name])

            log("INFO", "all", "Check cycle complete",
                restart_totals=restart_counts,
                failure_counters={k: v for k, v in consecutive_failures.items() if v > 0})

            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        log("INFO", "all", "Self-healer stopped by user", restart_totals=restart_counts)
        sys.exit(0)


if __name__ == "__main__":
    main()
