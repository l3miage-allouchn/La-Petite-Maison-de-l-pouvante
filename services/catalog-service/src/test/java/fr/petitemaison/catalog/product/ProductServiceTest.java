package fr.petitemaison.catalog.product;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import fr.petitemaison.catalog.event.ProductViewedEvent;
import fr.petitemaison.catalog.event.ProductViewedPublisher;
import fr.petitemaison.catalog.event.ViewerContext;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

@ExtendWith(MockitoExtension.class)
class ProductServiceTest {

    private static final Instant NOW = Instant.parse("2026-11-17T10:00:00Z");

    @Mock
    private ProductRepository repository;
    @Mock
    private ProductViewedPublisher publisher;

    private SimpleMeterRegistry registry;
    private ProductService service;

    @BeforeEach
    void setUp() {
        registry = new SimpleMeterRegistry();
        service = new ProductService(repository, publisher, registry, Clock.fixed(NOW, ZoneOffset.UTC));
    }

    @Test
    void viewReturnsDetailAndPublishesEventKeyedByUser() {
        when(repository.findById("fig-nosferatu")).thenReturn(Optional.of(nosferatu()));

        var detail = service.view("fig-nosferatu", new ViewerContext("user-42", "session-abcdef", "corr-12345678"));

        assertThat(detail.name()).isEqualTo("Figurine Nosferatu");
        assertThat(detail.stockByStore()).containsEntry(Store.LYON, 0).containsEntry(Store.ONLINE, 3);

        ArgumentCaptor<ProductViewedEvent> event = ArgumentCaptor.forClass(ProductViewedEvent.class);
        verify(publisher).publish(event.capture(), eq("user-42"), eq("corr-12345678"));
        assertThat(event.getValue().userId()).isEqualTo("user-42");
        assertThat(event.getValue().sessionId()).isEqualTo("session-abcdef");
        assertThat(event.getValue().productId()).isEqualTo("fig-nosferatu");
        assertThat(event.getValue().category()).isEqualTo("FIGURINE");
        assertThat(event.getValue().universe()).isEqualTo("gothique");
        assertThat(event.getValue().eventType()).isEqualTo("product.viewed");
        assertThat(event.getValue().source()).isEqualTo("product_page");
        assertThat(event.getValue().occurredAt()).isEqualTo(NOW);
        assertThat(event.getValue().eventId()).isNotBlank();

        assertThat(registry.get("products.viewed").tag("category", "FIGURINE").counter().count()).isEqualTo(1.0);
    }

    @Test
    void anonymousViewIsKeyedBySession() {
        when(repository.findById("fig-nosferatu")).thenReturn(Optional.of(nosferatu()));

        service.view("fig-nosferatu", new ViewerContext(null, "session-abcdef", "corr-12345678"));

        verify(publisher).publish(any(ProductViewedEvent.class), eq("session-abcdef"), eq("corr-12345678"));
    }

    @Test
    void viewOfUnknownProductThrowsAndPublishesNothing() {
        when(repository.findById("nope")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.view("nope", new ViewerContext(null, "session-abcdef", "c")))
                .isInstanceOf(ProductNotFoundException.class)
                .hasMessageContaining("nope");
        verify(publisher, never()).publish(any(), any(), any());
    }

    @Test
    @SuppressWarnings("unchecked")
    void searchMapsPageToSummaries() {
        when(repository.findAll(any(Specification.class), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(nosferatu()), PageRequest.of(0, 12), 1));

        var page = service.search(new ProductSearchCriteria(Category.FIGURINE, null, null), 0, 12);

        assertThat(page.totalElements()).isEqualTo(1);
        assertThat(page.totalPages()).isEqualTo(1);
        assertThat(page.content()).singleElement()
                .satisfies(p -> assertThat(p.id()).isEqualTo("fig-nosferatu"));
    }

    static Product nosferatu() {
        return new Product("fig-nosferatu", "Figurine Nosferatu", Category.FIGURINE, "gothique",
                new BigDecimal("64.90"), "Le comte Orlok", false, "/img.webp", Map.of(Store.ONLINE, 3));
    }
}
