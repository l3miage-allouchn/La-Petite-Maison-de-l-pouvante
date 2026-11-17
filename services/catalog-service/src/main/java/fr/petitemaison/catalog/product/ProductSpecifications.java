package fr.petitemaison.catalog.product;

import jakarta.persistence.criteria.MapJoin;
import java.util.Locale;
import org.springframework.data.jpa.domain.Specification;

/** Composable JPA criteria for the catalog filters. All values are bound parameters (no SQL injection). */
final class ProductSpecifications {

    private static final char ESCAPE = '\\';

    private ProductSpecifications() {
    }

    static Specification<Product> matching(ProductSearchCriteria criteria) {
        Specification<Product> spec = Specification.unrestricted();
        if (criteria.category() != null) {
            spec = spec.and(hasCategory(criteria.category()));
        }
        if (criteria.store() != null) {
            spec = spec.and(inStockAt(criteria.store()));
        }
        if (criteria.query() != null && !criteria.query().isBlank()) {
            spec = spec.and(containsText(criteria.query()));
        }
        return spec;
    }

    static Specification<Product> hasCategory(Category category) {
        return (root, query, cb) -> cb.equal(root.get("category"), category);
    }

    static Specification<Product> inStockAt(Store store) {
        return (root, query, cb) -> {
            MapJoin<Product, Store, Integer> stock = root.joinMap("stockByStore");
            return cb.and(cb.equal(stock.key(), store), cb.greaterThan(stock.value(), 0));
        };
    }

    static Specification<Product> containsText(String text) {
        String pattern = "%" + escapeLike(text.trim().toLowerCase(Locale.ROOT)) + "%";
        return (root, query, cb) -> cb.or(
                cb.like(cb.lower(root.get("name")), pattern, ESCAPE),
                cb.like(cb.lower(root.get("universe")), pattern, ESCAPE),
                cb.like(cb.lower(root.get("description")), pattern, ESCAPE));
    }

    /** Escapes LIKE wildcards so that user input is matched literally. */
    static String escapeLike(String value) {
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }
}
