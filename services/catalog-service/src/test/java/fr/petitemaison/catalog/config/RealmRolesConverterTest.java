package fr.petitemaison.catalog.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;

class RealmRolesConverterTest {

    @Test
    void mapsKeycloakRealmRolesToSpringAuthorities() {
        Jwt jwt = jwt(Map.of("realm_access", Map.of("roles", List.of("client", "admin"))));

        assertThat(new SecurityConfig.RealmRolesConverter().convert(jwt))
                .extracting(GrantedAuthority::getAuthority)
                .containsExactlyInAnyOrder("ROLE_client", "ROLE_admin");
    }

    @Test
    void tokenWithoutRealmAccessHasNoAuthorities() {
        assertThat(new SecurityConfig.RealmRolesConverter().convert(jwt(Map.of("scope", "openid")))).isEmpty();
    }

    private static Jwt jwt(Map<String, Object> claims) {
        return Jwt.withTokenValue("token").header("alg", "RS256").subject("user-1")
                .claims(c -> c.putAll(claims)).issuedAt(Instant.now()).build();
    }
}
