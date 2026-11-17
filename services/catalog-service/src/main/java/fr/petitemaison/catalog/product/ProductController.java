package fr.petitemaison.catalog.product;

import fr.petitemaison.catalog.event.ViewerContext;
import fr.petitemaison.catalog.product.ProductDtos.PageResponse;
import fr.petitemaison.catalog.product.ProductDtos.ProductDetail;
import fr.petitemaison.catalog.product.ProductDtos.ProductSummary;
import fr.petitemaison.catalog.web.CorrelationIdFilter;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Public, read-only catalog API. Constraint violations are returned as RFC 9457 problem details. */
@RestController
@RequestMapping("/api/catalog/products")
public class ProductController {

    public static final String SESSION_HEADER = "X-Session-Id";
    static final String ID_PATTERN = "^[a-z0-9][a-z0-9-]{0,63}$";
    static final String SESSION_PATTERN = "^[A-Za-z0-9-]{8,64}$";

    private final ProductService service;

    public ProductController(ProductService service) {
        this.service = service;
    }

    @GetMapping
    public PageResponse<ProductSummary> list(
            @RequestParam(required = false) Category category,
            @RequestParam(required = false) @Size(max = 100) String q,
            @RequestParam(required = false) Store store,
            @RequestParam(defaultValue = "0") @Min(0) @Max(1000) int page,
            @RequestParam(defaultValue = "12") @Min(1) @Max(50) int size) {
        return service.search(new ProductSearchCriteria(category, q, store), page, size);
    }

    @GetMapping("/{id}")
    public ProductDetail get(
            @PathVariable @Pattern(regexp = ID_PATTERN) String id,
            @RequestHeader(name = SESSION_HEADER, required = false) @Pattern(regexp = SESSION_PATTERN) String sessionId,
            @AuthenticationPrincipal Jwt jwt) {
        String userId = jwt != null ? jwt.getSubject() : null;
        String session = sessionId != null ? sessionId : "anon-" + UUID.randomUUID();
        String correlationId = MDC.get(CorrelationIdFilter.MDC_KEY);
        return service.view(id, new ViewerContext(userId, session, correlationId));
    }
}
