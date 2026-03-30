#!/usr/bin/env python3
"""Self-healing agent that monitors microservice health and auto-restarts failed containers.

Dependency-aware: checks Postgres health before restarting Spring Boot services.
If Postgres is down, restarts Postgres first and waits for it to become ready
before restarting any dependent service.
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

import urllib.request
import urllib.error

# Infrastructure dependencies — checked and healed first
POSTGRES = {
    "name": "postgres",
    "container": "postgres",
}

# Application services — only restarted when their dependencies are healthy
SERVICES = [
    {"name": "orders-service", "url": "http://localhost:8081/actuator/health", "depends_on": ["postgres"]},
    {"name": "inventory-service", "url": "http://localhost:8082/actuator/health", "depends_on": ["postgres"]},
    {"name": "payments-service", "url": "http://localhost:8083/actuator/health", "depends_on": ["postgres"]},
]

CHECK_INTERVAL_SECONDS = 30
FAILURE_THRESHOLD = 2
REQUEST_TIMEOUT_SECONDS = 5
POSTGRES_READY_TIMEOUT_SECONDS = 60
POSTGRES_READY_POLL_SECONDS = 5


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
    """Check a Spring Boot service's /actuator/health endpoint."""
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


def check_postgres_health():
    """Check if Postgres is accepting connections via pg_isready inside the container."""
    try:
        result = subprocess.run(
            ["docker", "exec", "postgres", "pg_isready", "-U", "postgres"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, "accepting connections"
        return False, result.stdout.strip() or result.stderr.strip() or "not ready"
    except subprocess.TimeoutExpired:
        return False, "pg_isready timed out"
    except Exception as e:
        return False, str(e)


def is_container_running(container_name):
    """Check if a Docker container is in 'running' state."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except Exception:
        return False


def wait_for_postgres(timeout=POSTGRES_READY_TIMEOUT_SECONDS):
    """Block until Postgres is accepting connections or timeout is reached.

    Returns True if Postgres became ready, False on timeout.
    """
    log("INFO", "postgres", "Waiting for Postgres to accept connections",
        timeout_seconds=timeout)
    elapsed = 0
    while elapsed < timeout:
        healthy, detail = check_postgres_health()
        if healthy:
            log("INFO", "postgres", "Postgres is ready", waited_seconds=elapsed)
            return True
        time.sleep(POSTGRES_READY_POLL_SECONDS)
        elapsed += POSTGRES_READY_POLL_SECONDS
    log("ERROR", "postgres", "Postgres did not become ready within timeout",
        timeout_seconds=timeout)
    return False


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


def start_container(container_name):
    """Start a stopped container (different from restart — won't fail if already stopped)."""
    log("WARN", container_name, "Starting container")
    try:
        result = subprocess.run(
            ["docker", "start", container_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            log("INFO", container_name, "Container started successfully")
            return True
        else:
            log("ERROR", container_name, "Failed to start container", stderr=result.stderr.strip())
            return False
    except subprocess.TimeoutExpired:
        log("ERROR", container_name, "Start command timed out")
        return False
    except FileNotFoundError:
        log("ERROR", container_name, "Docker CLI not found")
        return False


def main():
    consecutive_failures = {svc["name"]: 0 for svc in SERVICES}
    restart_counts = {svc["name"]: 0 for svc in SERVICES}
    restart_counts["postgres"] = 0
    postgres_was_down = False

    log("INFO", "all", "Self-healer started (dependency-aware)",
        interval=CHECK_INTERVAL_SECONDS, threshold=FAILURE_THRESHOLD)

    try:
        while True:
            # ── Phase 1: Check and heal Postgres first ──
            pg_running = is_container_running("postgres")
            pg_healthy, pg_detail = (False, "container not running") if not pg_running else check_postgres_health()

            if pg_healthy:
                if postgres_was_down:
                    log("INFO", "postgres", "Postgres recovered")
                    postgres_was_down = False
                log("INFO", "postgres", "Health check passed", status=pg_detail)
            else:
                postgres_was_down = True
                log("WARN", "postgres", "Health check failed", status=pg_detail, running=pg_running)

                if not pg_running:
                    log("ERROR", "postgres", "Postgres container is not running, starting it")
                    start_container("postgres")
                else:
                    log("ERROR", "postgres", "Postgres is running but not accepting connections, restarting")
                    restart_container("postgres")

                restart_counts["postgres"] += 1

                # Wait for Postgres to become ready before touching any service
                pg_ready = wait_for_postgres()
                if not pg_ready:
                    log("ERROR", "all",
                        "Postgres is not ready — skipping service restarts this cycle")
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

            # ── Phase 2: Check and heal application services ──
            # Re-check postgres health for the dependency gate
            pg_healthy_now, _ = check_postgres_health()

            for svc in SERVICES:
                name = svc["name"]
                healthy, detail = check_health(name, svc["url"])

                if healthy:
                    if consecutive_failures[name] > 0:
                        log("INFO", name, "Service recovered",
                            previous_failures=consecutive_failures[name])
                    consecutive_failures[name] = 0
                    log("INFO", name, "Health check passed", status=detail)
                else:
                    consecutive_failures[name] += 1
                    log("WARN", name, "Health check failed",
                        status=detail,
                        consecutive_failures=consecutive_failures[name])

                    if consecutive_failures[name] >= FAILURE_THRESHOLD:
                        # Dependency gate: don't restart if Postgres is still down
                        if "postgres" in svc.get("depends_on", []) and not pg_healthy_now:
                            log("WARN", name,
                                "Skipping restart — dependency 'postgres' is not healthy",
                                consecutive_failures=consecutive_failures[name])
                            continue

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
                failure_counters={k: v for k, v in consecutive_failures.items() if v > 0},
                postgres_healthy=pg_healthy_now)

            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        log("INFO", "all", "Self-healer stopped by user", restart_totals=restart_counts)
        sys.exit(0)


if __name__ == "__main__":
    main()
