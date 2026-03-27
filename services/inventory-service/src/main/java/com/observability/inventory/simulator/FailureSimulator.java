package com.observability.inventory.simulator;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.concurrent.ThreadLocalRandom;

@Component
public class FailureSimulator {

    private static final Logger log = LoggerFactory.getLogger(FailureSimulator.class);

    @Value("${inventory.simulate.latency-enabled:true}")
    private boolean latencyEnabled;

    @Value("${inventory.simulate.max-latency-ms:2000}")
    private int maxLatencyMs;

    @Value("${inventory.simulate.failure-rate:0.20}")
    private double failureRate;

    public void simulateLatency() {
        if (!latencyEnabled) {
            return;
        }
        int sleepMs = ThreadLocalRandom.current().nextInt(0, maxLatencyMs + 1);
        log.warn("Simulating latency: sleeping {}ms", sleepMs);
        try {
            Thread.sleep(sleepMs);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    public void simulateFailure() {
        double roll = ThreadLocalRandom.current().nextDouble();
        if (roll < failureRate) {
            log.warn("Simulating failure: random={} < threshold={}", roll, failureRate);
            throw new RuntimeException("Simulated inventory service failure");
        }
    }
}
