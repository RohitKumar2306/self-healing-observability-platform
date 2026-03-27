package com.observability.payments.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChargeResponse {

    private UUID paymentId;
    private String orderId;
    private BigDecimal amount;
    private String status;
    private String message;
}
