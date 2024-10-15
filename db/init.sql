CREATE USER repl_user REPLICATION LOGIN PASSWORD '${DB_REPL_PASSWORD}';

CREATE DATABASE ${DB_DATABASE};

\c contacts_db;

CREATE TABLE IF NOT EXISTS PhoneNumbers (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS Emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

INSERT INTO Emails (email) VALUES ('valera@gmail.com'), ('valera@yandex.ru');
INSERT INTO PhoneNumbers (phone_number) VALUES ('+79171234212'), ('+79170653233');
