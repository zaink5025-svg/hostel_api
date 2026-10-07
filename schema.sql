-- Hostel Management System - MySQL schema
-- Each table here replaces one of your old .txt files.
-- Run once:  mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS hostel_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE hostel_db;

-- students.txt  ->  students
CREATE TABLE IF NOT EXISTS students (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    first_name       VARCHAR(50)  NOT NULL,
    last_name        VARCHAR(50)  NOT NULL,
    father_name      VARCHAR(100),
    mother_name      VARCHAR(100),
    dob              DATE         NOT NULL,
    contact          VARCHAR(20)  NOT NULL,
    email            VARCHAR(100),
    address          VARCHAR(255),
    vehicle_number   VARCHAR(20),
    college_workplace VARCHAR(150),
    gender           ENUM('Male','Female','Other') NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- rooms.txt  ->  rooms
CREATE TABLE IF NOT EXISTS rooms (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    room_number  VARCHAR(20) NOT NULL UNIQUE,
    floor        INT         NOT NULL,
    capacity     INT         NOT NULL,
    gender       ENUM('Male','Female','Other') NOT NULL
);

-- beds.txt  ->  beds   (a bed belongs to a room)
CREATE TABLE IF NOT EXISTS beds (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    room_id   INT         NOT NULL,
    bed_name  VARCHAR(20) NOT NULL,
    status    ENUM('Available','Occupied') NOT NULL DEFAULT 'Available',
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

-- allocations.txt  ->  allocations
CREATE TABLE IF NOT EXISTS allocations (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT  NOT NULL,
    room_id         INT  NOT NULL,
    bed_id          INT  NOT NULL,
    allocated_date  DATE NOT NULL,
    checkout_date   DATE NULL,
    status          ENUM('Active','Checked-out') NOT NULL DEFAULT 'Active',
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (room_id)    REFERENCES rooms(id),
    FOREIGN KEY (bed_id)     REFERENCES beds(id)
);

-- services.txt  ->  services
CREATE TABLE IF NOT EXISTS services (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    description  VARCHAR(255)
);

-- visitors.txt  ->  visitors
CREATE TABLE IF NOT EXISTS visitors (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    student_id    INT          NOT NULL,
    visitor_name  VARCHAR(100) NOT NULL,
    contact       VARCHAR(20),
    reason        VARCHAR(255),
    address       VARCHAR(255),
    check_in      DATETIME     NOT NULL,
    check_out     DATETIME     NULL,
    status        ENUM('CheckedIn','CheckedOut') NOT NULL DEFAULT 'CheckedIn',
    FOREIGN KEY (student_id) REFERENCES students(id)
);

-- leaves.txt  ->  leaves
CREATE TABLE IF NOT EXISTS leaves (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    student_id        INT  NOT NULL,
    reason            VARCHAR(255) NOT NULL,
    application_date  DATE NOT NULL,
    return_date       DATE NOT NULL,
    status            ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (student_id) REFERENCES students(id)
);

-- attendance.txt  ->  attendance
-- in_time stays NULL while the student is outside.
CREATE TABLE IF NOT EXISTS attendance (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT          NOT NULL,
    purpose     VARCHAR(255) NOT NULL,
    out_time    DATETIME     NOT NULL,
    in_time     DATETIME     NULL,
    remarks     VARCHAR(255),
    FOREIGN KEY (student_id) REFERENCES students(id)
);