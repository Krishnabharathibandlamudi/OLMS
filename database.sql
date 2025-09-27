drop database if exists college;
create database college;
use college;

-- Corrected student_details table: Added 'mentor_id'
drop table student_details;
create table student_details(
id_num varchar(20) not null primary key,
name varchar(50),
email varchar(50),
phone varchar(10),
password varchar(10),
mentor_id varchar(20) -- ADDED: Required for registration to work
);

-- NEW TABLE FOR CERTIFICATES
drop table if exists certificate_application;
create table certificate_application(
	id int auto_increment primary key,
    student_email varchar(12),
    event_name varchar(100), -- Name of the Industrial Certification (e.g., AWS Developer)
    certificate_path varchar(255), -- Placeholder for the uploaded file path
    status varchar(1) default 'c', -- c: Pending, a: Approved, r: Denied
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

drop table if exists faculty;
create table faculty(
 id_num varchar(10) not null primary key,
 name varchar(20),
 email varchar(20),
 phone varchar(10),
 password varchar(8),
 is_hod varchar(1) default 'n' -- Renamed 'hod' to 'is_hod' for clarity, though both work
);

drop table if exists leave_application;
create table leave_application(
	id int auto_increment primary key, -- RENAMED: 'num' to 'id' for consistency with Flask code
    student_email varchar(7), -- RENAMED: 'id_num' to 'student_email' for consistency with Flask code
    start_date varchar(15), -- RENAMED: 'from_date' to 'start_date' for clarity/consistency
    end_date varchar(15), -- RENAMED: 'to_date' to 'end_date' for clarity/consistency
    reason varchar(200),
    status varchar(1) default 'c',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- ADDED: For ordering leaves correctly
);

create user if not exists 'monkey'@'localhost' identified by 'tail';
grant all privileges on college.* to 'monkey'@'localhost';

-- Sample data setup (f1, f2 are faculty, h1 is HoD, all use their ID as password)
insert into faculty (id_num, name, email, phone, password, is_hod) values
('F2001', 'Default Mentor', 'mentor@college.edu', '1234567890', 'F2001', 'n'),
('F2002', 'Faculty Two', 'f2@gmail.com', 'f2', 'f2', 'n'),
('H2001', 'HoD One', 'h1@gmail.com', 'h1', 'h1', 'y');

select * from student_details;
select * from faculty;
select * from leave_application;
