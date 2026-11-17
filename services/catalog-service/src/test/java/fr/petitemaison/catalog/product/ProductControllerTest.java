package fr.petitemaison.catalog.product;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import fr.petitemaison.catalog.config.SecurityConfig;
import fr.petitemaison.catalog.event.ViewerContext;
import fr.petitemaison.catalog.product.ProductDtos.PageResponse;
import fr.petitemaison.catalog.product.ProductDtos.ProductDetail;
import fr.petitemaison.catalog.web.CorrelationIdFilter;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(ProductController.class)
@Import(SecurityConfig.class)
@TestPropertySource(properties = "app.cors.allowed-origins=http://localhost:3000")
class ProductControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private ProductService service;
    @MockitoBean
    private JwtDecoder jwtDecoder;

    @Test
    void listIsPublicAndPassesFilters() throws Exception {
        when(service.search(any(), anyInt(), anyInt())).thenReturn(new PageResponse<>(List.of(), 1, 5, 0, 0));

        mvc.perform(get("/api/catalog/products")
                        .param("category", "FIGURINE").param("q", "orc").param("store", "LYON")
                        .param("page", "1").param("size", "5"))
                .andExpect(status().isOk())
                .andExpect(header().exists(CorrelationIdFilter.HEADER))
                .andExpect(jsonPath("$.page").value(1));

        verify(service).search(new ProductSearchCriteria(Category.FIGURINE, "orc", Store.LYON), 1, 5);
    }

    @Test
    void rejectsOversizedPageWithProblemDetail() throws Exception {
        mvc.perform(get("/api/catalog/products").param("size", "500"))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.status").value(400));
        verifyNoInteractions(service);
    }

    @Test
    void rejectsUnknownCategory() throws Exception {
        mvc.perform(get("/api/catalog/products").param("category", "TOASTER"))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON));
    }

    @Test
    void rejectsInvalidProductId() throws Exception {
        mvc.perform(get("/api/catalog/products/{id}", "DROP TABLE"))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }

    @Test
    void detailWithJwtUsesSubjectAsUserId() throws Exception {
        when(service.view(eq("fig-nosferatu"), any())).thenReturn(detail());

        mvc.perform(get("/api/catalog/products/{id}", "fig-nosferatu")
                        .header(ProductController.SESSION_HEADER, "session-abcdef")
                        .header(CorrelationIdFilter.HEADER, "corr-12345678")
                        .with(jwt().jwt(j -> j.subject("user-42"))))
                .andExpect(status().isOk())
                .andExpect(header().string(CorrelationIdFilter.HEADER, "corr-12345678"))
                .andExpect(jsonPath("$.id").value("fig-nosferatu"));

        ArgumentCaptor<ViewerContext> viewer = ArgumentCaptor.forClass(ViewerContext.class);
        verify(service).view(eq("fig-nosferatu"), viewer.capture());
        assertThat(viewer.getValue()).isEqualTo(new ViewerContext("user-42", "session-abcdef", "corr-12345678"));
    }

    @Test
    void anonymousDetailWithoutSessionGetsGeneratedSession() throws Exception {
        when(service.view(eq("fig-nosferatu"), any())).thenReturn(detail());

        mvc.perform(get("/api/catalog/products/{id}", "fig-nosferatu")
                        .header(CorrelationIdFilter.HEADER, "bad value\nwith newline"))
                .andExpect(status().isOk());

        ArgumentCaptor<ViewerContext> viewer = ArgumentCaptor.forClass(ViewerContext.class);
        verify(service).view(eq("fig-nosferatu"), viewer.capture());
        assertThat(viewer.getValue().userId()).isNull();
        assertThat(viewer.getValue().sessionId()).startsWith("anon-");
        assertThat(viewer.getValue().correlationId()).doesNotContain("\n").hasSize(36); // regenerated UUID
    }

    @Test
    void rejectsMalformedSessionHeader() throws Exception {
        mvc.perform(get("/api/catalog/products/{id}", "fig-nosferatu")
                        .header(ProductController.SESSION_HEADER, "<script>"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void unknownProductIs404ProblemDetail() throws Exception {
        when(service.view(eq("ghost"), any())).thenThrow(new ProductNotFoundException("ghost"));

        mvc.perform(get("/api/catalog/products/{id}", "ghost"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Product not found"))
                .andExpect(jsonPath("$.type").value("https://petite-maison.example/problems/product-not-found"));
    }

    @Test
    void unexpectedErrorsDoNotLeakDetails() throws Exception {
        when(service.view(eq("boom"), any())).thenThrow(new IllegalStateException("db password=secret"));

        mvc.perform(get("/api/catalog/products/{id}", "boom"))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.detail").value("An unexpected error occurred."));
    }

    @Test
    void writeMethodsRequireAuthentication() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post("/api/catalog/products"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void corsAllowsFrontendOriginOnly() throws Exception {
        mvc.perform(options("/api/catalog/products")
                        .header("Origin", "http://localhost:3000")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:3000"));

        mvc.perform(options("/api/catalog/products")
                        .header("Origin", "https://evil.example")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isForbidden());
    }

    private static ProductDetail detail() {
        return ProductDetail.from(ProductServiceTest.nosferatu());
    }
}
