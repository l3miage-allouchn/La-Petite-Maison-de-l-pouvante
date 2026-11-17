package fr.petitemaison.catalog;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.kafka.KafkaContainer;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

/** Same images and versions as docker-compose.infra.yml (never :latest). */
@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

	public static final String KAFKA_IMAGE = "apache/kafka:4.4.0";
	public static final String POSTGRES_IMAGE = "postgres:18.7-alpine";

	@Bean
	@ServiceConnection
	KafkaContainer kafkaContainer() {
		return new KafkaContainer(DockerImageName.parse(KAFKA_IMAGE));
	}

	@Bean
	@ServiceConnection
	PostgreSQLContainer postgresContainer() {
		return new PostgreSQLContainer(DockerImageName.parse(POSTGRES_IMAGE));
	}

}
