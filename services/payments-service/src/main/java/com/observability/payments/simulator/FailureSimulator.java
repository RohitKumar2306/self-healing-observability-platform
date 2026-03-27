package com.observability.payments.simulator;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.concurrent.ThreadLocalRandom;

@Component
public class FailureSimulator {

    private static final Logger log = LoggerFactory.getLogger(FailureSimulator.class);

    private final MeterRegistry meterRegistry;

    @Value("${payments.simulate.timeout-enabled:true}")
    private boolean timeoutEnabled;

    @Value("${payments.simulate.timeout-ms:3000}")
    private int timeoutMs;

    @Value("${payments.simulate.timeout-rate:0.30}")
    private double timeoutRate;

    @Value("${payments.simulate.failure-rate:0.15}")
    private double failureRate;

    public FailureSimulator(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    public void simulateTimeout() {
        if (!timeoutEnabled) {
            return;
        }
        double roll = ThreadLocalRandom.current().nextDouble();
        if (roll < timeoutRate) {
            log.warn("Simulating timeout: sleeping {}ms (random={} < threshold={})", timeoutMs, roll, timeoutRate);
            Counter.builder("payments.timeout.simulated.total").register(meterRegistry).increment();
            try {
                Thread.sleep(timeoutMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }

    public void simulateFailure() {
        double roll = ThreadLocalRandom.current().nextDouble();
        if (roll < failureRate) {
            log.warn("Simulating failure: random={} < threshold={}", roll, failureRate);
            throw new RuntimeException("Simulated payment gateway failure");
        }
    }
}
