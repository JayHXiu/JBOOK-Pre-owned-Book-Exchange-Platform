FROM maven:3.8.8-openjdk-17 AS builder
COPY ./backend /app
WORKDIR /app
RUN mvn clean package -DskipTests

FROM openjdk:17-jdk-slim
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
CMD ["java","-jar","app.jar"]
