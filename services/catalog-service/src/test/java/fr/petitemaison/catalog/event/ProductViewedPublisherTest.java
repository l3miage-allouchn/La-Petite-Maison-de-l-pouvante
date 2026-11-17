package fr.petitemaison.catalog.event;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.concurrent.CompletableFuture;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.TopicPartition;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@ExtendWith(MockitoExtension.class)
class ProductViewedPublisherTest {

    private static final String TOPIC = "catalog.product-viewed";

    @Mock
    private KafkaTemplate<String, String> kafkaTemplate;

    private final JsonMapper jsonMapper = JsonMapper.builder().build();
    private SimpleMeterRegistry registry;
    private ProductViewedPublisher publisher;

    @BeforeEach
    void setUp() {
        registry = new SimpleMeterRegistry();
        publisher = new ProductViewedPublisher(kafkaTemplate, jsonMapper, TOPIC, registry);
    }

    @Test
    @SuppressWarnings("unchecked")
    void sendsSnakeCaseJsonWithKeyAndHeaders() {
        ArgumentCaptor<ProducerRecord<String, String>> captor = ArgumentCaptor.forClass(ProducerRecord.class);
        when(kafkaTemplate.send(captor.capture())).thenAnswer(inv -> CompletableFuture.completedFuture(
                new SendResult<>(captor.getValue(), new RecordMetadata(new TopicPartition(TOPIC, 1), 0, 0, 0, 0, 0))));

        publisher.publish(event(null), "session-abcdef", "corr-12345678");

        ProducerRecord<String, String> record = captor.getValue();
        assertThat(record.topic()).isEqualTo(TOPIC);
        assertThat(record.key()).isEqualTo("session-abcdef");
        assertThat(new String(record.headers().lastHeader("correlation_id").value(), StandardCharsets.UTF_8))
                .isEqualTo("corr-12345678");
        assertThat(new String(record.headers().lastHeader("event_type").value(), StandardCharsets.UTF_8))
                .isEqualTo("product.viewed");

        JsonNode json = jsonMapper.readTree(record.value());
        assertThat(json.get("event_id").asString()).isEqualTo("11111111-2222-3333-4444-555555555555");
        assertThat(json.get("occurred_at").asString()).isEqualTo("2026-11-17T10:00:00Z");
        assertThat(json.has("user_id")).isTrue();
        assertThat(json.get("user_id").isNull()).isTrue();
        assertThat(json.get("session_id").asString()).isEqualTo("session-abcdef");
        assertThat(json.get("product_id").asString()).isEqualTo("fig-nosferatu");
        assertThat(json.get("source").asString()).isEqualTo("product_page");

        assertThat(registry.get("product.events.published").counter().count()).isEqualTo(1.0);
    }

    @Test
    void countsAsynchronousFailures() {
        when(kafkaTemplate.send(any(ProducerRecord.class)))
                .thenReturn(CompletableFuture.failedFuture(new IllegalStateException("broker down")));

        publisher.publish(event("user-1"), "user-1", "corr-12345678");

        assertThat(registry.get("product.events.publish.failures").counter().count()).isEqualTo(1.0);
    }

    @Test
    void neverPropagatesSynchronousProducerErrors() {
        when(kafkaTemplate.send(any(ProducerRecord.class))).thenThrow(new IllegalStateException("max.block.ms"));

        publisher.publish(event("user-1"), "user-1", null); // null correlation id falls back to event id

        assertThat(registry.get("product.events.publish.failures").counter().count()).isEqualTo(1.0);
        verify(kafkaTemplate).send(any(ProducerRecord.class));
    }

    @Test
    void warmUpToleratesUnreachableBroker() {
        when(kafkaTemplate.partitionsFor(TOPIC)).thenThrow(new IllegalStateException("timeout"));
        publisher.warmUp(); // must not throw
        verify(kafkaTemplate).partitionsFor(TOPIC);
    }

    @Test
    void warmUpFetchesMetadata() {
        when(kafkaTemplate.partitionsFor(TOPIC)).thenReturn(java.util.List.of());
        publisher.warmUp();
        verify(kafkaTemplate).partitionsFor(TOPIC);
    }

    private static ProductViewedEvent event(String userId) {
        return new ProductViewedEvent("11111111-2222-3333-4444-555555555555", ProductViewedEvent.TYPE,
                Instant.parse("2026-11-17T10:00:00Z"), userId, "session-abcdef", "fig-nosferatu",
                "FIGURINE", "gothique", ProductViewedEvent.SOURCE_PRODUCT_PAGE);
    }
}
