-- Description: SQL script to create database schema
--This query creates the database schema for the attendance tracking system. It defines the following tables:
-- users: to store user information
-- classes: to store class information
-- class_students: to store the many-to-many relationship between classes and students
-- attendance: to store attendance records
-- face_data: to store face encoding data
-- The tables are connected using foreign key constraints to maintain data integrity. 
-- The schema also includes constraints to enforce data validation rules, such as role validation for users and 
-- status validation for attendance records.

-- Create Users table to store user information
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    role VARCHAR(20) CHECK (role IN ('student', 'teacher', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Classes table to store class information
CREATE TABLE classes (
    class_id SERIAL PRIMARY KEY,
    class_name VARCHAR(100) NOT NULL,
    teacher_id INTEGER REFERENCES users(user_id),
    semester VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Class_Students table for many-to-many relationship between classes and students
CREATE TABLE class_students (
    class_id INTEGER REFERENCES classes(class_id),
    student_id INTEGER REFERENCES users(user_id),
    PRIMARY KEY (class_id, student_id)
);

-- Create Attendance table to store attendance records
CREATE TABLE attendance (
    attendance_id SERIAL PRIMARY KEY,
    class_id INTEGER REFERENCES classes(class_id),
    student_id INTEGER REFERENCES users(user_id),
    attendance_date DATE NOT NULL,
    check_in_time TIME,
    status VARCHAR(20) CHECK (status IN ('present', 'absent', 'late')),
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Face_Data table to store face encoding data
CREATE TABLE face_data (
    face_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    face_encoding TEXT NOT NULL,
    image_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- int fib(int n){
--     if (n <= 1) return n;
--     return fib(n - 1) + fib(n - 2);
-- }
-- 13:
-- return fib(12) + fib(11)
-- return (fib(11) + fib(10)) + ((fib(10) + fib(9)))
-- return (fib(10) + fib(9)) + (f(9) + f(8)) + (f(9) + f(8)) + (f(8) + f(7))
-- return (f(9) + f(8)) + [f(8) + f(7)] + [f(8) + f(7)] + [f(7) + f(6)] + [f(8) + f(7)] + [f(7) + f(6)] + [f(7) + f(6)] + [f(6) + f(5)]
-- return [f(8) + f(7)] + [f(7) + f(6)] + [f(7) + f(6)] + [f(6) + f(5)] + [f(7) + f(6)] + [f(6) + f(5)] + [f(6) + f(5)] + [f(5) + f(4)] [f(7) + f(6)] [f(6) + f(5)] [f(6) + f(5)] 
--        [f(5) + f(4)] [f(6) + f(5)] [f(5) + f(4)] [f(5) + f(4)] [f(4) + f(3)] 

-- return [f(7) + f(6)] [f(6) + f(5)] [f(6) + f(5)] [f(5) + f(4)] [f(6) + f(5)] [f(5) + f(4)] [f(5) + f(4)][f(4) + f(3)][f(6) + f(5)] [f(5) + f(4)][f(5) + f(4)][f(4) + f(3)]
-- [f(5) + f(4)][f(4) + f(3)][f(4) + f(3)][f(3) + f(2)] [f(6) + f(5)] [f(6) + f(4)][f(6) + f(4)][f(4) + f(3)][f(5) + f(4)][f(4) + f(3)][f(4) + f(3)][f(3) + f(2)][f(5) + f(4)]
-- [f(4) + f(3)][f(4) + f(3)][f(3) + f(2)][f(4) + f(3)][f(3) + f(2)][f(3) + f(2)][f(2) + f(1)]

-- return 

-- [0 1 1 2 3 5 8 13] 