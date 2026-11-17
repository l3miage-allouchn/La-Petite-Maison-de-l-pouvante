package fr.petitemaison.catalog;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.everyItem;
import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.is;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import fr.petitemaison.catalog.web.CorrelationIdFilter;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.micrometer.metrics.test.autoconfigure.AutoConfigureMetrics;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.kafka.core.KafkaAdmin;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.kafka.KafkaContainer;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * End-to-end inside the service: real PostgreSQL (Flyway demo data) and real Kafka (Testcontainers).
 * The JWT is injected by spring-security-test (no Keycloak needed).
 */
@SpringBootTest(properties = "spring.profiles.active=test")
@AutoConfigureMockMvc
@AutoConfigureMetrics
@Import(TestcontainersConfiguration.class)
class CatalogApiIT {

    private static final String TOPIC = "catalog.product-viewed";

    @Autowired
    private MockMvc mvc;
    @Autowired
    private KafkaContainer kafka;
    @Autowired
    private KafkaAdmin kafkaAdmin;
    @Autowired
    private JsonMapper jsonMapper;

    @Test
    void listsFlywayDemoDataWithPagination() throws Exception {
        mvc.perform(get("/api/catalog/products").param("size", "50"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(30))
                .andExpect(jsonPath("$.content[0].stockByStore.ONLINE").exists());
    }

    @Test
    void filtersByCategory() throws Exception {
        mvc.perform(get("/api/catalog/products").param("category", "FIGURINE").param("size", "50"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(7))
                .andExpect(jsonPath("$.content[*].category", everyItem(is("FIGURINE"))));
    }

    @Test
    void filtersByStoreStock() throws Exception {
        mvc.perform(get("/api/catalog/products").param("store", "LONDRES").param("size", "50"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[*].stockByStore.LONDRES", everyItem(greaterThan(0))));
    }

    @Test
    void searchesNameUniverseAndDescriptionCaseInsensitively() throws Exception {
        mvc.perform(get("/api/catalog/products").param("q", "NOSFERATU").param("size", "50"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(2));

        // LIKE wildcards are matched literally
        mvc.perform(get("/api/catalog/products").param("q", "%"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(0));
    }

    @Test
    void combinesFilters() throws Exception {
        mvc.perform(get("/api/catalog/products")
                        .param("category", "BLURAY").param("q", "giallo").param("store", "AIX"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[*].id", everyItem(containsString("bluray"))));
    }

    @Test
    void viewingAProductPublishesAnEventKeyedByUser() throws Exception {
        String correlationId = "it-" + UUID.randomUUID();
        createTopicIfMissing();

        mvc.perform(get("/api/catalog/products/{id}", "fig-orc-evil-ed")
                        .header(CorrelationIdFilter.HEADER, correlationId)
                        .header("X-Session-Id", "session-it-12345")
                        .with(jwt().jwt(j -> j.subject("it-user-1"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.exclusiveEvilEd").value(true));

        ConsumerRecord<String, String> record = awaitRecord(correlationId);
        assertThat(record.key()).isEqualTo("it-user-1");
        JsonNode event = jsonMapper.readTree(record.value());
        assertThat(event.get("event_type").asString()).isEqualTo("product.viewed");
        assertThat(event.get("user_id").asString()).isEqualTo("it-user-1");
        assertThat(event.get("session_id").asString()).isEqualTo("session-it-12345");
        assertThat(event.get("product_id").asString()).isEqualTo("fig-orc-evil-ed");
        assertThat(event.get("category").asString()).isEqualTo("FIGURINE");
        assertThat(event.get("universe").asString()).isEqualTo("heroic-fantasy");

        mvc.perform(get("/actuator/prometheus"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("products_viewed_total{")));
    }

    @Test
    void unknownProductReturns404() throws Exception {
        mvc.perform(get("/api/catalog/products/{id}", "does-not-exist"))
                .andExpect(status().isNotFound());
    }

    @Test
    void healthIsUp() throws Exception {
        mvc.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    private void createTopicIfMissing() {
        kafkaAdmin.createOrModifyTopics(new org.apache.kafka.clients.admin.NewTopic(TOPIC, 3, (short) 1));
    }

    private ConsumerRecord<String, String> awaitRecord(String correlationId) {
        Map<String, Object> props = Map.of(
                ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, kafka.getBootstrapServers(),
                ConsumerConfig.GROUP_ID_CONFIG, "it-" + UUID.randomUUID(),
                ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        try (KafkaConsumer<String, String> consumer =
                     new KafkaConsumer<>(props, new StringDeserializer(), new StringDeserializer())) {
            consumer.subscribe(List.of(TOPIC));
            long deadline = System.nanoTime() + Duration.ofSeconds(20).toNanos();
            List<String> seen = new ArrayList<>();
            while (System.nanoTime() < deadline) {
                for (ConsumerRecord<String, String> record : consumer.poll(Duration.ofMillis(500))) {
                    var header = record.headers().lastHeader("correlation_id");
                    String value = header == null ? "" : new String(header.value(), StandardCharsets.UTF_8);
                    seen.add(value);
                    if (correlationId.equals(value)) {
                        return record;
                    }
                }
            }
            throw new AssertionError("No event with correlation_id=" + correlationId + " (seen " + seen + ")");
        }
    }
}
