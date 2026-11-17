package fr.petitemaison.catalog.product;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.springframework.data.domain.Page;

/** API representations (camelCase JSON). Entities never leave the service layer. */
public final class ProductDtos {

    private ProductDtos() {
    }

    public record ProductSummary(String id, String name, Category category, String universe,
                                 BigDecimal price, boolean exclusiveEvilEd, String imageUrl,
                                 Map<Store, Integer> stockByStore) {

        static ProductSummary from(Product p) {
            return new ProductSummary(p.getId(), p.getName(), p.getCategory(), p.getUniverse(),
                    p.getPrice(), p.isExclusiveEvilEd(), p.getImageUrl(), p.getStockByStore());
        }
    }

    public record ProductDetail(String id, String name, Category category, String universe,
                                BigDecimal price, String description, boolean exclusiveEvilEd,
                                String imageUrl, Map<Store, Integer> stockByStore) {

        static ProductDetail from(Product p) {
            return new ProductDetail(p.getId(), p.getName(), p.getCategory(), p.getUniverse(),
                    p.getPrice(), p.getDescription(), p.isExclusiveEvilEd(), p.getImageUrl(),
                    p.getStockByStore());
        }
    }

    public record PageResponse<T>(List<T> content, int page, int size, long totalElements, int totalPages) {

        static <T> PageResponse<T> from(Page<T> page) {
            return new PageResponse<>(page.getContent(), page.getNumber(), page.getSize(),
                    page.getTotalElements(), page.getTotalPages());
        }
    }
}
