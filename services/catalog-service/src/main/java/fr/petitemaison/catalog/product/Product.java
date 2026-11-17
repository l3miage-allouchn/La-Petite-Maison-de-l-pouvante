package fr.petitemaison.catalog.product;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.MapKeyColumn;
import jakarta.persistence.MapKeyEnumerated;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.Map;
import org.hibernate.annotations.BatchSize;

/** Catalog product. The identifier is a human-readable slug (e.g. {@code fig-orc-evil-ed}). */
@Entity
@Table(name = "product")
public class Product {

    @Id
    @Column(length = 64)
    private String id;

    @Column(nullable = false, length = 200)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private Category category;

    @Column(nullable = false, length = 64)
    private String universe;

    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal price;

    @Column(columnDefinition = "text")
    private String description;

    @Column(name = "exclusive_evil_ed", nullable = false)
    private boolean exclusiveEvilEd;

    @Column(name = "image_url", length = 500)
    private String imageUrl;

    @ElementCollection
    @CollectionTable(name = "product_stock", joinColumns = @JoinColumn(name = "product_id"))
    @MapKeyEnumerated(EnumType.STRING)
    @MapKeyColumn(name = "store", length = 32)
    @Column(name = "quantity", nullable = false)
    @BatchSize(size = 50)
    private Map<Store, Integer> stockByStore = new HashMap<>();

    protected Product() {
        // for JPA
    }

    public Product(String id, String name, Category category, String universe, BigDecimal price,
                   String description, boolean exclusiveEvilEd, String imageUrl,
                   Map<Store, Integer> stockByStore) {
        this.id = id;
        this.name = name;
        this.category = category;
        this.universe = universe;
        this.price = price;
        this.description = description;
        this.exclusiveEvilEd = exclusiveEvilEd;
        this.imageUrl = imageUrl;
        this.stockByStore = new HashMap<>(stockByStore);
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public Category getCategory() {
        return category;
    }

    public String getUniverse() {
        return universe;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public String getDescription() {
        return description;
    }

    public boolean isExclusiveEvilEd() {
        return exclusiveEvilEd;
    }

    public String getImageUrl() {
        return imageUrl;
    }

    /** Returns a defensive copy, with every store present (0 when no stock row exists). */
    public Map<Store, Integer> getStockByStore() {
        Map<Store, Integer> copy = new EnumMap<>(Store.class);
        for (Store store : Store.values()) {
            copy.put(store, stockByStore.getOrDefault(store, 0));
        }
        return copy;
    }
}
