"""Real Kafka (official apache/kafka image, KRaft) and Valkey containers, same versions as Compose."""

import socket
from collections.abc import Iterator

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

KAFKA_IMAGE = "apache/kafka:4.4.0"
VALKEY_IMAGE = "valkey/valkey:9.1.3-alpine"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def kafka_bootstrap() -> Iterator[str]:
    # The advertised listener must contain the host port, so it is chosen before start.
    port = _free_port()
    container = (
        DockerContainer(KAFKA_IMAGE)
        .with_bind_ports(9092, port)
        .with_env("KAFKA_NODE_ID", "1")
        .with_env("KAFKA_PROCESS_ROLES", "broker,controller")
        # PLAINTEXT is for the tests (host port); BROKER is for tools running inside the container.
        .with_env("KAFKA_LISTENERS", "PLAINTEXT://:9092,BROKER://:29092,CONTROLLER://:9093")
        .with_env("KAFKA_ADVERTISED_LISTENERS", f"PLAINTEXT://localhost:{port},BROKER://localhost:29092")
        .with_env("KAFKA_LISTENER_SECURITY_PROTOCOL_MAP", "PLAINTEXT:PLAINTEXT,BROKER:PLAINTEXT,CONTROLLER:PLAINTEXT")
        .with_env("KAFKA_INTER_BROKER_LISTENER_NAME", "BROKER")
        .with_env("KAFKA_CONTROLLER_LISTENER_NAMES", "CONTROLLER")
        .with_env("KAFKA_CONTROLLER_QUORUM_VOTERS", "1@localhost:9093")
        .with_env("KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR", "1")
        .with_env("KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR", "1")
        .with_env("KAFKA_TRANSACTION_STATE_LOG_MIN_ISR", "1")
        .with_env("KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS", "0")
        .with_env("KAFKA_AUTO_CREATE_TOPICS_ENABLE", "false")
        .with_env("KAFKA_HEAP_OPTS", "-Xmx512m")
        .waiting_for(LogMessageWaitStrategy("Kafka Server started").with_startup_timeout(90))
    )
    with container:
        for topic, partitions in (("catalog.product-viewed", 3), ("catalog.product-viewed.dlq", 1)):
            exit_code, output = container.exec(
                [
                    "/opt/kafka/bin/kafka-topics.sh",
                    "--bootstrap-server",
                    "localhost:29092",
                    "--create",
                    "--if-not-exists",
                    "--topic",
                    topic,
                    "--partitions",
                    str(partitions),
                    "--replication-factor",
                    "1",
                ]
            )
            assert exit_code == 0, output
        yield f"localhost:{port}"


@pytest.fixture(scope="session")
def valkey_address() -> Iterator[tuple[str, int]]:
    container = (
        DockerContainer(VALKEY_IMAGE)
        .with_exposed_ports(6379)
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections").with_startup_timeout(30))
    )
    with container:
        yield container.get_container_host_ip(), int(container.get_exposed_port(6379))
