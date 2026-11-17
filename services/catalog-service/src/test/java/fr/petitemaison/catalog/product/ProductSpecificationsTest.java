package fr.petitemaison.catalog.product;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class ProductSpecificationsTest {

    @Test
    void escapesLikeWildcards() {
        assertThat(ProductSpecifications.escapeLike("100%_off\\")).isEqualTo("100\\%\\_off\\\\");
    }

    @Test
    void plainTextIsUnchanged() {
        assertThat(ProductSpecifications.escapeLike("nosferatu")).isEqualTo("nosferatu");
    }

    @Test
    void buildsSpecificationForAnyCombinationOfFilters() {
        assertThat(ProductSpecifications.matching(new ProductSearchCriteria(null, null, null))).isNotNull();
        assertThat(ProductSpecifications.matching(new ProductSearchCriteria(Category.BD, "  ", Store.AIX))).isNotNull();
    }
}
