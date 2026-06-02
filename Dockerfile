FROM maven:3.8-openjdk-17
WORKDIR /app
COPY . .
WORKDIR /app/backend
RUN mvn clean package -DskipTests
CMD java -jar target/*.jar
