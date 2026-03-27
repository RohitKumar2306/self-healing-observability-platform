#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

stop_container() {
    local name="$1"
    log_warn "Stopping ${name}..."
    if docker stop "${name}" >/dev/null 2>&1; then
        log_info "${name} stopped"
    else
        log_error "Failed to stop ${name} (may already be stopped)"
    fi
}

restart_all() {
    log_info "Restarting all services..."
    for svc in inventory-service payments-service orders-service postgres; do
        docker restart "${svc}" >/dev/null 2>&1 && log_info "${svc} restarted" || log_error "Failed to restart ${svc}"
    done
}

set_inventory_failure_rate() {
    local rate="$1"
    log_info "Setting inventory-service failure rate to ${rate}%..."
    docker exec inventory-service sh -c "
        curl -s -X POST 'http://localhost:8082/actuator/env' \
            -H 'Content-Type: application/json' \
            -d '{\"name\":\"inventory.simulate.failure-rate\",\"value\":\"0.${rate}\"}' || true
    " >/dev/null 2>&1

    # Fallback: restart with updated env var
    log_info "Restarting inventory-service with FAILURE_RATE=${rate}%..."
    docker update --env-add "INVENTORY_SIMULATE_FAILURE_RATE=0.${rate}" inventory-service >/dev/null 2>&1 || true
    docker stop inventory-service >/dev/null 2>&1 || true
    docker compose up -d inventory-service 2>/dev/null || docker-compose up -d inventory-service 2>/dev/null
    log_info "inventory-service restarted with failure rate ${rate}%"
}

show_status() {
    echo ""
    echo "=============================="
    echo "  Current Container Status"
    echo "=============================="
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" \
        --filter "name=orders-service" \
        --filter "name=inventory-service" \
        --filter "name=payments-service" \
        --filter "name=postgres"
    echo ""
}

show_menu() {
    echo ""
    echo "==========================================="
    echo "  Failure Simulation Menu"
    echo "==========================================="
    echo "  1) Stop inventory-service"
    echo "  2) Stop payments-service"
    echo "  3) Stop postgres"
    echo "  4) Restart all services"
    echo "  5) Set inventory failure rate to 80%"
    echo "  6) Reset inventory failure rate to 20%"
    echo "  7) Show container status"
    echo "  0) Exit"
    echo "==========================================="
    echo -n "  Choose an option: "
}

main() {
    echo -e "${GREEN}"
    echo "  Self-Healing Observability Platform"
    echo "  Failure Simulator"
    echo -e "${NC}"

    while true; do
        show_menu
        read -r choice
        echo ""

        case "${choice}" in
            1) stop_container "inventory-service" ;;
            2) stop_container "payments-service" ;;
            3) stop_container "postgres" ;;
            4) restart_all ;;
            5) set_inventory_failure_rate 80 ;;
            6) set_inventory_failure_rate 20 ;;
            7) show_status ;;
            0)
                log_info "Exiting"
                exit 0
                ;;
            *)
                log_error "Invalid option: ${choice}"
                ;;
        esac
    done
}

main
