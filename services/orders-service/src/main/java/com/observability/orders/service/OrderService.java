package com.observability.orders.service;

import com.observability.orders.dto.CreateOrderRequest;
import com.observability.orders.entity.Order;
import com.observability.orders.entity.Order.OrderStatus;
import com.observability.orders.repository.OrderRepository;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository orderRepository;
    private final RestTemplate restTemplate;

    @Value("${orders.inventory-service-url:http://inventory-service:8082}")
    private String inventoryServiceUrl;

    @Value("${orders.payments-service-url:http://payments-service:8083}")
    private String paymentsServiceUrl;

    public Order createOrder(CreateOrderRequest request) {
        Order order = Order.builder()
                .customerId(request.getCustomerId())
                .productId(request.getProductId())
                .quantity(request.getQuantity())
                .totalAmount(request.getTotalAmount())
                .status(OrderStatus.PENDING)
                .build();

        order = orderRepository.save(order);
        log.info("Order created with id={}, status=PENDING", order.getId());

        try {
            // Step 1: Reserve inventory
            log.info("Reserving inventory for orderId={}, productId={}, quantity={}",
                    order.getId(), order.getProductId(), order.getQuantity());

            Map<String, Object> reserveRequest = Map.of(
                    "productId", order.getProductId(),
                    "quantity", order.getQuantity()
            );

            ResponseEntity<Map> inventoryResponse = restTemplate.postForEntity(
                    inventoryServiceUrl + "/inventory/reserve",
                    reserveRequest,
                    Map.class
            );

            if (!inventoryResponse.getStatusCode().is2xxSuccessful()) {
                throw new RuntimeException("Inventory reservation failed");
            }
            log.info("Inventory reserved successfully for orderId={}", order.getId());

            // Step 2: Process payment
            log.info("Processing payment for orderId={}, amount={}",
                    order.getId(), order.getTotalAmount());

            Map<String, Object> chargeRequest = Map.of(
                    "orderId", order.getId().toString(),
                    "amount", order.getTotalAmount()
            );

            ResponseEntity<Map> paymentResponse = restTemplate.postForEntity(
                    paymentsServiceUrl + "/payments/charge",
                    chargeRequest,
                    Map.class
            );

            if (!paymentResponse.getStatusCode().is2xxSuccessful()) {
                throw new RuntimeException("Payment processing failed");
            }
            log.info("Payment processed successfully for orderId={}", order.getId());

            // Both steps succeeded
            order.setStatus(OrderStatus.CONFIRMED);
            order = orderRepository.save(order);
            log.info("Order confirmed orderId={}", order.getId());

        } catch (Exception e) {
            log.error("Order failed orderId={}, reason={}", order.getId(), e.getMessage());
            order.setStatus(OrderStatus.FAILED);
            order = orderRepository.save(order);
        }

        return order;
    }

    public Order getOrderById(UUID id) {
        return orderRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Order not found: " + id));
    }

    public List<Order> getAllOrders() {
        return orderRepository.findAll();
    }
}
