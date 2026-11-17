package fr.petitemaison.catalog.event;

import fr.petitemaison.catalog.web.CorrelationIdFilter;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.nio.charset.StandardCharsets;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

/**
 * Publishes product-viewed events. Runs on a separate (virtual) thread: the HTTP response never
 * waits for Kafka, and a broker outage only costs the event, never the page.
 */
@Component
public class ProductViewedPublisher {

    public static final String HEADER_CORRELATION_ID = "correlation_id";
    public static final String HEADER_EVENT_TYPE = "event_type";

    private static final Logger log = LoggerFactory.getLogger(ProductViewedPublisher.class);

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final JsonMapper jsonMapper;
    private final String topic;
    private final Counter published;
    private final Counter failed;

    public ProductViewedPublisher(KafkaTemplate<String, String> kafkaTemplate, JsonMapper jsonMapper,
                                  @Value("${app.kafka.topics.product-viewed}") String topic,
                                  MeterRegistry registry) {
        this.kafkaTemplate = kafkaTemplate;
        this.jsonMapper = jsonMapper;
        this.topic = topic;
        this.published = Counter.builder("product.events.published")
                .description("product-viewed events acknowledged by Kafka").register(registry);
        this.failed = Counter.builder("product.events.publish.failures")
                .description("product-viewed events that could not be published").register(registry);
    }

    /** Fetches topic metadata once at startup so that the first page view does not pay for it. */
    @Async
    @EventListener(ApplicationReadyEvent.class)
    public void warmUp() {
        try {
            log.info("Kafka producer ready: topic {} has {} partitions", topic, kafkaTemplate.partitionsFor(topic).size());
        } catch (RuntimeException ex) {
            log.warn("Kafka not reachable at startup ({}); events will be retried per request", rootCauseMessage(ex));
        }
    }

    @Async
    public void publish(ProductViewedEvent event, String key, String requestCorrelationId) {
        String correlationId = requestCorrelationId != null ? requestCorrelationId : event.eventId();
        MDC.put(CorrelationIdFilter.MDC_KEY, correlationId);
        try {
            ProducerRecord<String, String> record =
                    new ProducerRecord<>(topic, key, jsonMapper.writeValueAsString(event));
            record.headers()
                    .add(HEADER_EVENT_TYPE, event.eventType().getBytes(StandardCharsets.UTF_8))
                    .add(HEADER_CORRELATION_ID, correlationId.getBytes(StandardCharsets.UTF_8));
            kafkaTemplate.send(record).whenComplete((result, ex) -> {
                if (ex == null) {
                    published.increment();
                    log.debug("product-viewed published event_id={} partition={} offset={}", event.eventId(),
                            result.getRecordMetadata().partition(), result.getRecordMetadata().offset());
                } else {
                    failed.increment();
                    log.warn("product-viewed publish failed event_id={} correlation_id={}: {}",
                            event.eventId(), correlationId, rootCauseMessage(ex));
                }
            });
        } catch (RuntimeException ex) {
            // Serialization error or producer blocked beyond max.block.ms (broker unreachable).
            failed.increment();
            log.warn("product-viewed publish failed event_id={}: {}", event.eventId(), rootCauseMessage(ex));
        } finally {
            MDC.remove(CorrelationIdFilter.MDC_KEY);
        }
    }

    private static String rootCauseMessage(Throwable ex) {
        Throwable root = ex;
        while (root.getCause() != null && root.getCause() != root) {
            root = root.getCause();
        }
        return root == ex ? String.valueOf(ex.getMessage()) : ex.getMessage() + " (cause: " + root.getMessage() + ")";
    }
}
