-- Disposable test database; pytest refuses database names without the _test suffix.
CREATE DATABASE IF NOT EXISTS marcus_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON marcus_test.* TO 'marcus'@'%';
