package fr.petitemaison.catalog.config;

import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;

/** {@code @Async} runs on Boot's task executor, backed by virtual threads (spring.threads.virtual.enabled). */
@Configuration(proxyBeanMethods = false)
@EnableAsync
public class AppConfig {

    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
