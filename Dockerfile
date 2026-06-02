FROM maven:3.8-openjdk-17 AS build
# 复制整个项目到容器
COPY . /source
# 进入backend目录（pom在这里）
WORKDIR /source/backend
RUN mvn clean package -DskipTests

FROM eclipse-temurin:17-jre-alpine
COPY --from=build /source/backend/target/*.jar app.jar
EXPOSE 8080
CMD ["java","-jar","app.jar"]
