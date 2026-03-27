package com.observability.inventory.service;

import com.observability.inventory.dto.ReserveRequest;
import com.observability.inventory.dto.ReserveResponse;
import com.observability.inventory.entity.InventoryItem;
import com.observability.inventory.repository.InventoryRepository;
import com.observability.inventory.simulator.FailureSimulator;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class InventoryService {

    private static final Logger log = LoggerFactory.getLogger(InventoryService.class);

    private final InventoryRepository inventoryRepository;
    private final FailureSimulator failureSimulator;
    private final MeterRegistry meterRegistry;

    public InventoryService(InventoryRepository inventoryRepository, FailureSimulator failureSimulator, MeterRegistry meterRegistry) {
        this.inventoryRepository = inventoryRepository;
        this.failureSimulator = failureSimulator;
        this.meterRegistry = meterRegistry;
    }

    @Transactional
    public ReserveResponse reserve(ReserveRequest request) {
        failureSimulator.simulateLatency();
        failureSimulator.simulateFailure();

        InventoryItem item = inventoryRepository.findByProductId(request.getProductId())
                .orElseThrow(() -> new RuntimeException("Product not found: " + request.getProductId()));

        if (item.getAvailableQuantity() < request.getQuantity()) {
            log.warn("Insufficient stock for productId={}, available={}, requested={}",
                    request.getProductId(), item.getAvailableQuantity(), request.getQuantity());
            Counter.builder("inventory.reserve.total").tag("status", "insufficient_stock").register(meterRegistry).increment();
            return ReserveResponse.builder()
                    .productId(request.getProductId())
                    .reserved(false)
                    .availableQuantity(item.getAvailableQuantity())
                    .reservedQuantity(item.getReservedQuantity())
                    .message("Insufficient stock")
                    .build();
        }

        item.setAvailableQuantity(item.getAvailableQuantity() - request.getQuantity());
        item.setReservedQuantity(item.getReservedQuantity() + request.getQuantity());
        inventoryRepository.save(item);

        log.info("Reserved {} units of productId={}", request.getQuantity(), request.getProductId());
        Counter.builder("inventory.reserve.total").tag("status", "success").register(meterRegistry).increment();

        return ReserveResponse.builder()
                .productId(request.getProductId())
                .reserved(true)
                .availableQuantity(item.getAvailableQuantity())
                .reservedQuantity(item.getReservedQuantity())
                .message("Stock reserved successfully")
                .build();
    }

    public InventoryItem getByProductId(String productId) {
        return inventoryRepository.findByProductId(productId)
                .orElseThrow(() -> new RuntimeException("Product not found: " + productId));
    }

    public List<InventoryItem> getAll() {
        return inventoryRepository.findAll();
    }
}
