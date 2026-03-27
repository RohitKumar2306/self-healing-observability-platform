package com.observability.inventory.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReserveResponse {

    private String productId;
    private boolean reserved;
    private Integer availableQuantity;
    private Integer reservedQuantity;
    private String message;
}
