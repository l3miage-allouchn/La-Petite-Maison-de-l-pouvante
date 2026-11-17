package fr.petitemaison.catalog.event;

/**
 * Who is looking at a product.
 *
 * @param userId        Keycloak subject when the request carries a valid JWT, otherwise {@code null}
 * @param sessionId     browser session identifier (always present)
 * @param correlationId request correlation identifier, propagated as a Kafka header
 */
public record ViewerContext(String userId, String sessionId, String correlationId) {

    /** Kafka partition key: per user when authenticated, per session otherwise (ordering per viewer). */
    public String partitionKey() {
        return userId != null ? userId : sessionId;
    }
}
