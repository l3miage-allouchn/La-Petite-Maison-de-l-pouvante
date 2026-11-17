package fr.petitemaison.catalog.event;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.UUID;

/**
 * Payload of the {@code catalog.product-viewed} topic.
 * Contract: docs/events/product-viewed.schema.json (snake_case, user_id nullable).
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public record ProductViewedEvent(
        @JsonProperty("event_id") String eventId,
        @JsonProperty("event_type") String eventType,
        @JsonProperty("occurred_at") Instant occurredAt,
        @JsonProperty("user_id") String userId,
        @JsonProperty("session_id") String sessionId,
        @JsonProperty("product_id") String productId,
        @JsonProperty("category") String category,
        @JsonProperty("universe") String universe,
        @JsonProperty("source") String source) {

    public static final String TYPE = "product.viewed";
    public static final String SOURCE_PRODUCT_PAGE = "product_page";

    public static ProductViewedEvent of(ViewerContext viewer, String productId, String category,
                                        String universe, Instant now) {
        return new ProductViewedEvent(UUID.randomUUID().toString(), TYPE, now, viewer.userId(),
                viewer.sessionId(), productId, category, universe, SOURCE_PRODUCT_PAGE);
    }
}
