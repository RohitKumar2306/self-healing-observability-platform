package com.observability.payments.service;

import com.observability.payments.dto.ChargeRequest;
import com.observability.payments.dto.ChargeResponse;
import com.observability.payments.entity.Payment;
import com.observability.payments.entity.Payment.PaymentStatus;
import com.observability.payments.repository.PaymentRepository;
import com.observability.payments.simulator.FailureSimulator;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class PaymentsService {

    private static final Logger log = LoggerFactory.getLogger(PaymentsService.class);

    private final PaymentRepository paymentRepository;
    private final FailureSimulator failureSimulator;

    public ChargeResponse charge(ChargeRequest request) {
        log.info("Processing payment for orderId={}, amount={}", request.getOrderId(), request.getAmount());

        failureSimulator.simulateTimeout();
        failureSimulator.simulateFailure();

        Payment payment = Payment.builder()
                .orderId(request.getOrderId())
                .amount(request.getAmount())
                .status(PaymentStatus.SUCCESS)
                .build();

        payment = paymentRepository.save(payment);
        log.info("Payment successful paymentId={}, orderId={}", payment.getId(), payment.getOrderId());

        return ChargeResponse.builder()
                .paymentId(payment.getId())
                .orderId(payment.getOrderId())
                .amount(payment.getAmount())
                .status(payment.getStatus().name())
                .message("Payment processed successfully")
                .build();
    }

    public Payment getById(UUID id) {
        return paymentRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Payment not found: " + id));
    }

    public List<Payment> getByOrderId(String orderId) {
        return paymentRepository.findByOrderId(orderId);
    }
}
