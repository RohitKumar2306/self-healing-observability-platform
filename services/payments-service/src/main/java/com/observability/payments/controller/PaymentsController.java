package com.observability.payments.controller;

import com.observability.payments.dto.ChargeRequest;
import com.observability.payments.dto.ChargeResponse;
import com.observability.payments.entity.Payment;
import com.observability.payments.service.PaymentsService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/payments")
@RequiredArgsConstructor
public class PaymentsController {

    private final PaymentsService paymentsService;

    @PostMapping("/charge")
    public ResponseEntity<ChargeResponse> charge(@RequestBody ChargeRequest request) {
        ChargeResponse response = paymentsService.charge(request);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Payment> getById(@PathVariable UUID id) {
        return ResponseEntity.ok(paymentsService.getById(id));
    }

    @GetMapping("/order/{orderId}")
    public ResponseEntity<List<Payment>> getByOrderId(@PathVariable String orderId) {
        return ResponseEntity.ok(paymentsService.getByOrderId(orderId));
    }
}
