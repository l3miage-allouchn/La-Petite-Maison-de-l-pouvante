package fr.petitemaison.catalog.product;

import fr.petitemaison.catalog.event.ProductViewedEvent;
import fr.petitemaison.catalog.event.ProductViewedPublisher;
import fr.petitemaison.catalog.event.ViewerContext;
import fr.petitemaison.catalog.product.ProductDtos.PageResponse;
import fr.petitemaison.catalog.product.ProductDtos.ProductDetail;
import fr.petitemaison.catalog.product.ProductDtos.ProductSummary;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Clock;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class ProductService {

    private static final Logger log = LoggerFactory.getLogger(ProductService.class);

    private final ProductRepository repository;
    private final ProductViewedPublisher publisher;
    private final MeterRegistry registry;
    private final Clock clock;

    public ProductService(ProductRepository repository, ProductViewedPublisher publisher,
                          MeterRegistry registry, Clock clock) {
        this.repository = repository;
        this.publisher = publisher;
        this.registry = registry;
        this.clock = clock;
    }

    public PageResponse<ProductSummary> search(ProductSearchCriteria criteria, int page, int size) {
        PageRequest pageable = PageRequest.of(page, size, Sort.by("name").and(Sort.by("id")));
        return PageResponse.from(
                repository.findAll(ProductSpecifications.matching(criteria), pageable).map(ProductSummary::from));
    }

    /** Returns the product and emits a product-viewed event (fire-and-forget). */
    public ProductDetail view(String productId, ViewerContext viewer) {
        Product product = repository.findById(productId)
                .orElseThrow(() -> new ProductNotFoundException(productId));
        ProductDetail detail = ProductDetail.from(product);

        // Exposed in Prometheus as products_viewed_total{category="..."}
        Counter.builder("products.viewed")
                .description("Product detail pages served")
                .tag("category", product.getCategory().name())
                .register(registry)
                .increment();

        ProductViewedEvent event = ProductViewedEvent.of(viewer, product.getId(),
                product.getCategory().name(), product.getUniverse(), clock.instant());
        publisher.publish(event, viewer.partitionKey(), viewer.correlationId());
        // No personal data in logs: the correlation id (MDC) links this line to the Kafka event.
        log.info("product viewed product_id={} category={} authenticated={}",
                product.getId(), product.getCategory(), viewer.userId() != null);
        return detail;
    }
}
