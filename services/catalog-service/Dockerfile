# syntax=docker/dockerfile:1
# Multi-stage build: JDK to build, minimal JRE (Alpine) to run, non-root user, layered jar.

# ---------- build ----------
FROM eclipse-temurin:27-jdk-alpine-3.24 AS build
WORKDIR /workspace

# Dependencies first (cached layer as long as pom.xml does not change)
COPY .mvn/ .mvn/
COPY mvnw pom.xml ./
RUN --mount=type=cache,target=/root/.m2 ./mvnw -B -q dependency:go-offline

COPY src/ src/
# Tests run in CI (unit + Testcontainers), not during the image build.
RUN --mount=type=cache,target=/root/.m2 ./mvnw -B -q package -DskipTests \
 && java -Djarmode=tools -jar target/catalog-service.jar extract --layers --launcher --destination target/extracted

# ---------- runtime ----------
FROM eclipse-temurin:27-jre-alpine-3.24

LABEL org.opencontainers.image.title="catalog-service" \
      org.opencontainers.image.description="La Petite Maison de l'Épouvante - product catalog" \
      org.opencontainers.image.source="https://github.com/l3miage-allouchn/La-Petite-Maison-de-l-pouvante" \
      org.opencontainers.image.licenses="MIT"

RUN addgroup -S -g 10001 app && adduser -S -D -H -u 10001 -G app -s /sbin/nologin app
WORKDIR /app

# Least-changing layers first. Files stay owned by root: the app user cannot modify its own code.
COPY --from=build /workspace/target/extracted/dependencies/ ./
COPY --from=build /workspace/target/extracted/spring-boot-loader/ ./
COPY --from=build /workspace/target/extracted/snapshot-dependencies/ ./
COPY --from=build /workspace/target/extracted/application/ ./

USER 10001:10001
EXPOSE 8080

ENV SPRING_PROFILES_ACTIVE=docker \
    JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError -Djava.security.egd=file:/dev/urandom"

HEALTHCHECK --interval=15s --timeout=3s --start-period=40s --retries=5 \
  CMD wget -qO- http://127.0.0.1:8080/actuator/health/readiness | grep -q '"UP"' || exit 1

ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
