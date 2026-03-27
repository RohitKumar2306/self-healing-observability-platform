package com.observability.inventory.init;

import com.observability.inventory.entity.InventoryItem;
import com.observability.inventory.repository.InventoryRepository;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private final InventoryRepository inventoryRepository;

    @Override
    public void run(String... args) {
        if (inventoryRepository.count() > 0) {
            log.info("Inventory already seeded, skipping initialization");
            return;
        }

        for (int i = 1; i <= 5; i++) {
            String productId = String.format("PROD-%03d", i);
            InventoryItem item = InventoryItem.builder()
                    .productId(productId)
                    .availableQuantity(100)
                    .reservedQuantity(0)
                    .build();
            inventoryRepository.save(item);
            log.info("Seeded product: {} with quantity 100", productId);
        }
    }
}
