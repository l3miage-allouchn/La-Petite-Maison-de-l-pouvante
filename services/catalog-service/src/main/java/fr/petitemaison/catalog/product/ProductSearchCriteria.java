package fr.petitemaison.catalog.product;

/** Optional catalog filters; {@code null} means "no filter". */
public record ProductSearchCriteria(Category category, String query, Store store) {
}
