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
-- Ensure you are connected to the face_recognization database before executing this script.

-- Drop existing tables if they exist to allow script re-execution
DROP TABLE IF EXISTS face_data CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS class_students CASCADE;
DROP TABLE IF EXISTS classes CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Create Users table to store user information
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'teacher', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Classes table to store class information
CREATE TABLE classes (
    class_id SERIAL PRIMARY KEY,
    class_name VARCHAR(100) NOT NULL,
    teacher_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    semester VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Class_Students table for many-to-many relationships between classes and students
CREATE TABLE class_students (
    class_id INTEGER NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (class_id, student_id)
);

-- Create Attendance table to store attendance records
CREATE TABLE attendance (
    attendance_id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    attendance_date DATE NOT NULL,
    check_in_time TIME,
    status VARCHAR(20) NOT NULL CHECK (status IN ('present', 'absent', 'late')),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Face_Data table to store face encoding data
CREATE TABLE face_data (
    face_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    face_encoding TEXT NOT NULL,
    image_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_classes_teacher_id ON classes(teacher_id);
CREATE INDEX IF NOT EXISTS idx_class_students_class ON class_students(class_id);
CREATE INDEX IF NOT EXISTS idx_class_students_student ON class_students(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_class_student ON attendance(class_id, student_id);
CREATE INDEX IF NOT EXISTS idx_face_data_user ON face_data(user_id);

-- End of SQL script
