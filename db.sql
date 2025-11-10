-- =====================================================
-- capstoneprojectdb - Consolidated SQL Setup
-- Single-file schema, data, functions, procedures,
-- triggers, RBAC roles, and example users.
-- Use MySQL 8.0+.
-- NOTE: No User table; authentication is simulated via MySQL users/roles.
-- =====================================================

DROP SCHEMA IF EXISTS capstoneprojectdb;
CREATE SCHEMA IF NOT EXISTS capstoneprojectdb;
USE capstoneprojectdb;

-- =====================================================
-- TABLES
-- =====================================================

CREATE TABLE IF NOT EXISTS Faculty (
  Faculty_ID INT NOT NULL PRIMARY KEY,
  Name VARCHAR(100) NOT NULL,
  Email VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS Student (
  SRN VARCHAR(20) NOT NULL PRIMARY KEY,
  Name VARCHAR(100) NOT NULL,
  Email VARCHAR(100) UNIQUE NOT NULL,
  Sem INT NOT NULL CHECK (Sem BETWEEN 1 AND 8)
);

CREATE TABLE IF NOT EXISTS Team (
  Team_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  Faculty_ID INT NULL,
  FOREIGN KEY (Faculty_ID) REFERENCES Faculty (Faculty_ID)
    ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Project (
  Project_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  Title VARCHAR(255) NOT NULL,
  Description TEXT NULL,
  Status ENUM('Ongoing', 'Completed', 'Cancelled') 
      NOT NULL DEFAULT 'Ongoing'
);

CREATE TABLE IF NOT EXISTS Rubric (
  Rubric_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  Rubric_Name VARCHAR(100) NOT NULL,
  Max_Marks DECIMAL(7,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS Team_Student (
  Team_ID INT NOT NULL,
  SRN VARCHAR(20) NOT NULL,
  PRIMARY KEY (Team_ID, SRN),
  FOREIGN KEY (Team_ID) REFERENCES Team (Team_ID)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (SRN) REFERENCES Student (SRN)
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Team_Project (
  Team_ID INT NOT NULL,
  Project_ID INT NOT NULL,
  PRIMARY KEY (Team_ID, Project_ID),
  FOREIGN KEY (Team_ID) REFERENCES Team (Team_ID)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (Project_ID) REFERENCES Project (Project_ID)
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Meeting (
  Meeting_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  Faculty_ID INT NOT NULL,
  Team_ID INT NOT NULL,
  DateTime DATETIME NOT NULL,
  Feedback TEXT NULL,
  FOREIGN KEY (Faculty_ID) REFERENCES Faculty (Faculty_ID)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (Team_ID) REFERENCES Team (Team_ID)
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Review_Type (
  ReviewType_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  Review_Name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS Review (
  Review_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  ReviewType_ID INT NOT NULL,
  Team_ID INT NOT NULL,
  Date DATE NOT NULL,
  Venue VARCHAR(100) NULL,
  FOREIGN KEY (ReviewType_ID) REFERENCES Review_Type (ReviewType_ID)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (Team_ID) REFERENCES Team (Team_ID)
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Review_Panel (
  Review_ID INT NOT NULL,
  Faculty_ID INT NOT NULL,
  PRIMARY KEY (Review_ID, Faculty_ID),
  FOREIGN KEY (Review_ID) REFERENCES Review (Review_ID)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (Faculty_ID) REFERENCES Faculty (Faculty_ID)
    ON DELETE CASCADE ON UPDATE CASCADE
);

-- Evaluation table: one row per (faculty grader, student, rubric, project, review)
CREATE TABLE IF NOT EXISTS Evaluation (
  Evaluation_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  Faculty_ID INT NOT NULL,
  SRN VARCHAR(20) NOT NULL,
  Rubric_ID INT NOT NULL,
  Project_ID INT NOT NULL,
  Review_ID INT NOT NULL,
  Marks DECIMAL(7,2) NOT NULL CHECK (Marks >= 0),
  Comments TEXT NULL,
  Created_At TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  Updated_At TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY ux_eval_unique (Faculty_ID, SRN, Rubric_ID, Project_ID, Review_ID),
  FOREIGN KEY (Faculty_ID) REFERENCES Faculty (Faculty_ID)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  FOREIGN KEY (SRN) REFERENCES Student (SRN)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  FOREIGN KEY (Rubric_ID) REFERENCES Rubric (Rubric_ID)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  FOREIGN KEY (Project_ID) REFERENCES Project (Project_ID)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (Review_ID) REFERENCES Review (Review_ID)
    ON DELETE CASCADE ON UPDATE CASCADE
);

-- =====================================================
-- INITIAL SAMPLE DATA (faculty, students, teams, projects, reviews, rubrics, evaluations)
-- Note: No users table / no user mapping stored in DB (authentication simulated via DB users/roles)
-- =====================================================

INSERT INTO Faculty (Faculty_ID, Name, Email) VALUES
(101, 'Dr. Ramesh Kumar', 'ramesh.kumar@univ.edu'),
(102, 'Dr. Meera Iyer', 'meera.iyer@univ.edu'),
(103, 'Dr. Anil Nair', 'anil.nair@univ.edu');

INSERT INTO Student (SRN, Name, Email, Sem) VALUES
('PES1UG21CS001', 'Aditi Sharma', 'aditi.sharma@univ.edu', 7),
('PES1UG21CS002', 'Rahul Menon', 'rahul.menon@univ.edu', 7),
('PES1UG21CS003', 'Sneha Rao', 'sneha.rao@univ.edu', 7),
('PES1UG21CS004', 'Vikram Patil', 'vikram.patil@univ.edu', 7),
('PES1UG21CS005', 'Karan Desai', 'karan.desai@univ.edu', 7),
('PES1UG21CS006', 'Neha Bhat', 'neha.bhat@univ.edu', 7);

-- Create teams (some with mentors, some unmentored)
INSERT INTO Team (Team_ID, Faculty_ID) VALUES
(1, 101),
(2, 102),
(3, 103),
(4, NULL); -- an example team with no mentor yet

INSERT INTO Team_Student (Team_ID, SRN) VALUES
(1, 'PES1UG21CS001'),
(1, 'PES1UG21CS002'),
(2, 'PES1UG21CS003'),
(2, 'PES1UG21CS004'),
(3, 'PES1UG21CS005'),
(3, 'PES1UG21CS006');

INSERT INTO Project (Project_ID, Title, Status, Description) VALUES
(1, 'AI-based Traffic Flow Optimization', 'Ongoing', NULL),
(2, 'IoT Smart Home Energy Saver', 'Ongoing', NULL),
(3, 'Autonomous Drone Delivery System', 'Ongoing', NULL);

INSERT INTO Team_Project (Team_ID, Project_ID) VALUES
(1, 1),
(2, 2),
(3, 3);

INSERT INTO Meeting (Faculty_ID, Team_ID, DateTime, Feedback) VALUES
(101, 1, '2025-02-10 10:30:00', 'Good progress on model accuracy.'),
(102, 2, '2025-02-11 15:00:00', 'Hardware integration needs improvement.'),
(103, 3, '2025-02-12 11:00:00', 'Excellent demo and documentation.');

INSERT INTO Review_Type (Review_Name) VALUES
('ISA 1'),
('ISA 2'),
('ESA');

INSERT INTO Review (Review_ID, ReviewType_ID, Team_ID, Date, Venue) VALUES
(1, 1, 1, '2025-03-01', 'Room A-101'),
(2, 1, 2, '2025-03-01', 'Room A-102'),
(3, 1, 3, '2025-03-02', 'Room A-103'),
(4, 3, 1, '2025-05-20', 'Auditorium'),
(5, 3, 2, '2025-05-21', 'Auditorium');

INSERT INTO Review_Panel (Review_ID, Faculty_ID) VALUES
(1, 101), (1, 102),
(2, 102), (2, 103),
(3, 103), (3, 101),
(4, 101), (4, 103),
(5, 102), (5, 103);

INSERT INTO Rubric (Rubric_ID, Rubric_Name, Max_Marks) VALUES
(1, 'Innovation', 10.0),
(2, 'Technical Depth', 10.0),
(3, 'Presentation', 5.0);

INSERT INTO Evaluation (Faculty_ID, SRN, Rubric_ID, Project_ID, Review_ID, Marks, Comments) VALUES
(101, 'PES1UG21CS001', 1, 1, 1, 9.0, 'Highly innovative'),
(101, 'PES1UG21CS002', 2, 1, 1, 8.5, 'Technically sound'),
(102, 'PES1UG21CS003', 1, 2, 2, 7.5, 'Needs better design'),
(102, 'PES1UG21CS004', 3, 2, 2, 4.5, 'Good presentation'),
(103, 'PES1UG21CS005', 1, 3, 3, 9.5, 'Excellent concept'),
(103, 'PES1UG21CS006', 2, 3, 3, 8.8, 'Well executed');

-- =====================================================
-- FUNCTIONS: semester total and grade mapping
-- =====================================================

DELIMITER $$

CREATE FUNCTION GetSemesterTotal(srn_in VARCHAR(20), semester_in INT)
RETURNS DECIMAL(5,2)
DETERMINISTIC
BEGIN
    DECLARE total_marks DECIMAL(12,4) DEFAULT 0;
    DECLARE max_marks DECIMAL(12,4) DEFAULT 0;
    DECLARE percentage DECIMAL(7,4);

    SELECT 
        SUM(e.Marks) AS total_marks_sum,
        SUM(r.Max_Marks) AS max_marks_sum
    INTO total_marks, max_marks
    FROM Evaluation e
    JOIN Rubric r ON e.Rubric_ID = r.Rubric_ID
    JOIN Student s ON e.SRN = s.SRN
    WHERE s.SRN = srn_in
      AND s.Sem = semester_in;

    IF max_marks IS NULL OR max_marks = 0 THEN
        RETURN NULL;
    END IF;

    SET percentage = (total_marks / max_marks) * 100;
    RETURN ROUND(percentage, 2);
END$$

DELIMITER ;

-- =====================================================
-- PROCEDURES
-- Important: procedures accept explicit SRN or Faculty_ID parameters
-- so you don't need user table mapping in DB.
-- =====================================================

DELIMITER $$

CREATE PROCEDURE AddReviewForTeam(
    IN rev_type_id INT,
    IN team_id INT,
    IN rev_date DATE,
    IN venue VARCHAR(100),
    IN panel_faculty_ids TEXT -- comma separated Faculty_IDs
)
BEGIN
    DECLARE last_review_id INT;
    DECLARE mentor_id INT;
    DECLARE formatted_list TEXT;
    DECLARE tmp TEXT;

    SELECT Faculty_ID INTO mentor_id
    FROM Team
    WHERE Team_ID = team_id;

    IF mentor_id IS NOT NULL AND FIND_IN_SET(mentor_id, panel_faculty_ids) = 0 THEN
        SET panel_faculty_ids = CONCAT(panel_faculty_ids, ',', mentor_id);
    END IF;

    INSERT INTO Review (ReviewType_ID, Team_ID, Date, Venue)
    VALUES (rev_type_id, team_id, rev_date, venue);

    SET last_review_id = LAST_INSERT_ID();

    SET tmp = panel_faculty_ids;
    SET tmp = REPLACE(tmp, ' ', '');
    SET formatted_list = '';
    WHILE CHAR_LENGTH(tmp) > 0 DO
        SET formatted_list = CONCAT(formatted_list, '(', last_review_id, ',', 
            SUBSTRING_INDEX(tmp, ',', 1), '),');
        IF INSTR(tmp, ',') = 0 THEN
            SET tmp = '';
        ELSE
            SET tmp = SUBSTRING(tmp, INSTR(tmp, ',') + 1);
        END IF;
    END WHILE;

    IF CHAR_LENGTH(formatted_list) > 0 THEN
        SET formatted_list = LEFT(formatted_list, CHAR_LENGTH(formatted_list) - 1);
        SET @sql = CONCAT('INSERT INTO Review_Panel (Review_ID, Faculty_ID) VALUES ', formatted_list);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$

CREATE PROCEDURE AutoGenerateEvaluations(
    IN review_id INT,
    IN rubric_id INT
)
BEGIN
    INSERT IGNORE INTO Evaluation (Faculty_ID, SRN, Rubric_ID, Project_ID, Review_ID, Marks)
    SELECT rp.Faculty_ID, ts.SRN, rubric_id, tp.Project_ID, review_id, 0
    FROM Review_Panel rp
    JOIN Review r ON rp.Review_ID = r.Review_ID
    JOIN Team_Student ts ON r.Team_ID = ts.Team_ID
    JOIN Team_Project tp ON r.Team_ID = tp.Team_ID
    WHERE r.Review_ID = review_id;
END$$

-- STUDENT: create a new team with a list of students (caller provides SRN and optional comma-separated teammate SRNs)
DELIMITER $$

CREATE PROCEDURE StudentCreateTeam(
    IN srn_in VARCHAR(20),
    IN teammate_srns TEXT -- comma-separated SRNs (may be NULL or empty)
)
BEGIN
    DECLARE existing INT DEFAULT 0;
    DECLARE caller_sem INT;
    DECLARE ttmp TEXT;
    DECLARE cur_srn VARCHAR(20);
    DECLARE cur_sem INT;
    DECLARE tmp_msg TEXT;

    -- Handle any SQL exception safely (rollback)
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Team creation failed (rolled back) due to validation error';
    END;

    START TRANSACTION;

    -- Validate caller exists
    IF NOT EXISTS (SELECT 1 FROM Student WHERE SRN = srn_in) THEN
        SET tmp_msg = CONCAT('Invalid student SRN: ', srn_in);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = tmp_msg;
    END IF;

    -- Check caller not already in a team
    SELECT COUNT(*) INTO existing FROM Team_Student WHERE SRN = srn_in;
    IF existing > 0 THEN
        SET tmp_msg = CONCAT('Student already in a team: ', srn_in);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = tmp_msg;
    END IF;

    -- Get caller's semester
    SELECT Sem INTO caller_sem FROM Student WHERE SRN = srn_in;

    -- Create team without name (Faculty_ID NULL)
    INSERT INTO Team (Faculty_ID) VALUES (NULL);
    SET @new_team_id = LAST_INSERT_ID();

    -- Insert the calling student
    INSERT INTO Team_Student (Team_ID, SRN) VALUES (@new_team_id, srn_in);

    -- Handle teammate SRNs if provided
    IF teammate_srns IS NOT NULL AND CHAR_LENGTH(TRIM(teammate_srns)) > 0 THEN
        SET ttmp = REPLACE(teammate_srns, ' ', '');
        WHILE CHAR_LENGTH(ttmp) > 0 DO
            SET cur_srn = SUBSTRING_INDEX(ttmp, ',', 1);

            -- Validate student exists
            IF NOT EXISTS (SELECT 1 FROM Student WHERE SRN = cur_srn) THEN
                SET tmp_msg = CONCAT('Teammate SRN not found: ', cur_srn);
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = tmp_msg;
            END IF;

            -- Validate not already in a team
            IF EXISTS (SELECT 1 FROM Team_Student WHERE SRN = cur_srn) THEN
                SET tmp_msg = CONCAT('Teammate already in team: ', cur_srn);
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = tmp_msg;
            END IF;

            -- Validate semester match
            SELECT Sem INTO cur_sem FROM Student WHERE SRN = cur_srn;
            IF cur_sem <> caller_sem THEN
                SET tmp_msg = CONCAT('Semester mismatch for ', cur_srn, ' (expected sem ', caller_sem, ')');
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = tmp_msg;
            END IF;

            -- Insert valid teammate
            INSERT INTO Team_Student (Team_ID, SRN) VALUES (@new_team_id, cur_srn);

            -- Move to next SRN
            IF INSTR(ttmp, ',') = 0 THEN
                SET ttmp = '';
            ELSE
                SET ttmp = SUBSTRING(ttmp, INSTR(ttmp, ',') + 1);
            END IF;
        END WHILE;
    END IF;

    COMMIT;
END$$



-- STUDENT: add project for the team of the given SRN
CREATE PROCEDURE StudentAddProject(
    IN srn_in VARCHAR(20),
    IN project_title VARCHAR(255),
    IN description TEXT
)
BEGIN
    DECLARE team_id_var INT;

    SELECT ts.Team_ID INTO team_id_var
    FROM Team_Student ts
    WHERE ts.SRN = srn_in
    LIMIT 1;

    IF team_id_var IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Student not in a team';
    END IF;

    INSERT INTO Project (Title, Description, Status)
    VALUES (project_title, description, 'Ongoing');

    INSERT INTO Team_Project (Team_ID, Project_ID)
    VALUES (team_id_var, LAST_INSERT_ID());
END$$

-- FACULTY: claim a team (faculty_id provided directly)
CREATE PROCEDURE FacultyClaimTeam(
    IN faculty_id INT,
    IN team_id INT
)
BEGIN
    DECLARE faculty_exists INT;
    SELECT COUNT(*) INTO faculty_exists FROM Faculty WHERE Faculty_ID = faculty_id;
    IF faculty_exists = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid faculty id';
    END IF;

    UPDATE Team
    SET Faculty_ID = faculty_id
    WHERE Team_ID = team_id AND (Faculty_ID IS NULL OR Faculty_ID = faculty_id);

    IF ROW_COUNT() = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Team already has a different mentor or does not exist';
    END IF;
END$$

-- FACULTY: schedule meeting (faculty_id provided directly)
CREATE PROCEDURE FacultyScheduleMeeting(
    IN faculty_id INT,
    IN team_id INT,
    IN meet_time DATETIME,
    IN feedback_text TEXT
)
BEGIN
    DECLARE faculty_id_var INT;
    SELECT COUNT(*) INTO faculty_id_var FROM Faculty WHERE Faculty_ID = faculty_id;
    IF faculty_id_var = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid faculty id';
    END IF;

    IF (SELECT Faculty_ID FROM Team WHERE Team_ID = team_id) <> faculty_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Not mentor of this team';
    END IF;

    INSERT INTO Meeting (Faculty_ID, Team_ID, DateTime, Feedback)
    VALUES (faculty_id, team_id, meet_time, feedback_text);
END$$

-- FACULTY: add marks for an evaluation (faculty_id provided directly)
CREATE PROCEDURE FacultyAddMarks(
    IN faculty_id INT,
    IN eval_id INT,
    IN marks_in DECIMAL(7,2),
    IN comments_in TEXT
)
BEGIN
    DECLARE exists_panel INT;

    IF NOT EXISTS (SELECT 1 FROM Faculty WHERE Faculty_ID = faculty_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid faculty id';
    END IF;

    SELECT COUNT(*) INTO exists_panel
    FROM Evaluation e
    JOIN Review_Panel rp ON e.Review_ID = rp.Review_ID
    WHERE e.Evaluation_ID = eval_id AND rp.Faculty_ID = faculty_id;

    IF exists_panel = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Not authorized to mark this evaluation';
    END IF;

    IF marks_in < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Marks cannot be negative';
    END IF;

    UPDATE Evaluation
    SET Marks = marks_in, Comments = comments_in
    WHERE Evaluation_ID = eval_id;
END$$

DELIMITER ;

-- =====================================================
-- TRIGGERS
-- =====================================================

DELIMITER $$

CREATE TRIGGER trg_check_meeting_mentor
BEFORE INSERT ON Meeting
FOR EACH ROW
BEGIN
    DECLARE mentor_id INT;
    SELECT Faculty_ID INTO mentor_id
    FROM Team
    WHERE Team_ID = NEW.Team_ID;

    IF mentor_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Team has no mentor assigned';
    END IF;

    IF NEW.Faculty_ID <> mentor_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Faculty is not the mentor of this team';
    END IF;
END$$

CREATE TRIGGER trg_team_size_limit
BEFORE INSERT ON Team_Student
FOR EACH ROW
BEGIN
    DECLARE member_count INT;
    SELECT COUNT(*) INTO member_count
    FROM Team_Student
    WHERE Team_ID = NEW.Team_ID;

    IF member_count >= 4 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A team cannot have more than 4 members';
    END IF;
END$$

CREATE TRIGGER trg_check_marks
BEFORE INSERT ON Evaluation
FOR EACH ROW
BEGIN
    DECLARE max_allowed DECIMAL(7,2);
    SELECT Max_Marks INTO max_allowed
    FROM Rubric
    WHERE Rubric_ID = NEW.Rubric_ID;

    IF NEW.Marks > max_allowed THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Marks exceed maximum allowed for this rubric';
    END IF;
END$$

CREATE TRIGGER trg_mentor_in_panel
BEFORE INSERT ON Review_Panel
FOR EACH ROW
BEGIN
    DECLARE mentor_id INT;
    SELECT t.Faculty_ID INTO mentor_id
    FROM Team t
    JOIN Review r ON r.Team_ID = t.Team_ID
    WHERE r.Review_ID = NEW.Review_ID;

    -- If inserting a mentor row itself, allow; otherwise ensure mentor already exists or will exist
    IF mentor_id IS NOT NULL AND NEW.Faculty_ID <> mentor_id THEN
        IF NOT EXISTS (
            SELECT 1 FROM Review_Panel rp
            WHERE rp.Review_ID = NEW.Review_ID AND rp.Faculty_ID = mentor_id
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'The mentor must be included in the review panel';
        END IF;
    END IF;
END$$

DELIMITER $$

CREATE TRIGGER trg_project_status_update
AFTER INSERT ON Evaluation
FOR EACH ROW
BEGIN
    DECLARE total_reviews INT DEFAULT 0;
    DECLARE eval_count INT DEFAULT 0;
    DECLARE team_project_id INT DEFAULT NULL;
    DECLARE team_id INT DEFAULT NULL;

    -- Find team for this student
    SELECT Team_ID INTO team_id
    FROM Team_Student
    WHERE SRN = NEW.SRN
    LIMIT 1;

    -- Proceed only if a team exists
    IF team_id IS NOT NULL THEN

        SELECT Project_ID INTO team_project_id
        FROM Team_Project
        WHERE Team_ID = team_id
        LIMIT 1;

        SELECT COUNT(*) INTO total_reviews
        FROM Review
        WHERE Team_ID = team_id;

        SELECT COUNT(DISTINCT e.Review_ID) INTO eval_count
        FROM Evaluation e
        JOIN Team_Student ts ON e.SRN = ts.SRN
        WHERE ts.Team_ID = team_id;

        IF total_reviews > 0 AND total_reviews = eval_count THEN
            UPDATE Project
            SET Status = 'Completed'
            WHERE Project_ID = team_project_id;
        END IF;

    END IF;
END$$

DELIMITER ;


-- =====================================================
-- ROLE-BASED ACCESS CONTROL (RBAC) - MySQL roles & users
-- We simulate three types of users: admin, faculty, student as DB users.
-- Admins have admin privileges (and faculty-like execution rights).
-- Faculty can view teams they mentor, schedule meetings for their teams, and add marks
-- only for evaluations where they are in the review panel.
-- Students can create teams, add projects for their teams, and view meetings/marks.
-- =====================================================

-- Create roles
CREATE ROLE IF NOT EXISTS 'role_admin';
CREATE ROLE IF NOT EXISTS 'role_faculty';
CREATE ROLE IF NOT EXISTS 'role_student';

-- Grant privileges to roles (on capstoneprojectdb)
GRANT ALL PRIVILEGES ON capstoneprojectdb.* TO 'role_admin';

-- Faculty role privileges (restricted)
GRANT SELECT ON capstoneprojectdb.Team TO 'role_faculty';
GRANT SELECT ON capstoneprojectdb.Student TO 'role_faculty';
GRANT SELECT ON capstoneprojectdb.Review TO 'role_faculty';
GRANT SELECT ON capstoneprojectdb.Review_Panel TO 'role_faculty';
GRANT SELECT ON capstoneprojectdb.Evaluation TO 'role_faculty';
GRANT SELECT ON capstoneprojectdb.Meeting TO 'role_faculty';
GRANT SELECT ON capstoneprojectdb.Team_Project TO 'role_faculty';
GRANT SELECT ON capstoneprojectdb.Team_Student TO 'role_faculty';
GRANT SELECT ON capstoneprojectdb.Project TO 'role_faculty';
GRANT SELECT ON capstoneprojectdb.Rubric TO 'role_faculty';

GRANT INSERT ON capstoneprojectdb.Meeting TO 'role_faculty';
GRANT INSERT ON capstoneprojectdb.Evaluation TO 'role_faculty';
GRANT UPDATE (Marks, Comments) ON capstoneprojectdb.Evaluation TO 'role_faculty';
GRANT UPDATE (Faculty_ID) ON capstoneprojectdb.Team TO 'role_faculty';

GRANT EXECUTE ON PROCEDURE capstoneprojectdb.AddReviewForTeam TO 'role_faculty';
GRANT EXECUTE ON PROCEDURE capstoneprojectdb.AutoGenerateEvaluations TO 'role_faculty';
GRANT EXECUTE ON PROCEDURE capstoneprojectdb.FacultyClaimTeam TO 'role_faculty';
GRANT EXECUTE ON PROCEDURE capstoneprojectdb.FacultyScheduleMeeting TO 'role_faculty';
GRANT EXECUTE ON PROCEDURE capstoneprojectdb.FacultyAddMarks TO 'role_faculty';

-- Student role privileges
GRANT SELECT ON capstoneprojectdb.Team TO 'role_student';
GRANT SELECT ON capstoneprojectdb.Team_Student TO 'role_student';
GRANT SELECT ON capstoneprojectdb.Project TO 'role_student';
GRANT SELECT ON capstoneprojectdb.Meeting TO 'role_student';
GRANT SELECT ON capstoneprojectdb.Evaluation TO 'role_student';
GRANT SELECT ON capstoneprojectdb.Rubric TO 'role_student';
GRANT SELECT ON capstoneprojectdb.Review TO 'role_student';

GRANT INSERT ON capstoneprojectdb.Team TO 'role_student';
GRANT INSERT ON capstoneprojectdb.Team_Student TO 'role_student';
GRANT INSERT ON capstoneprojectdb.Project TO 'role_student';
GRANT INSERT ON capstoneprojectdb.Team_Project TO 'role_student';

GRANT EXECUTE ON PROCEDURE capstoneprojectdb.StudentCreateTeam TO 'role_student';
GRANT EXECUTE ON PROCEDURE capstoneprojectdb.StudentAddProject TO 'role_student';

-- Create example MySQL users and attach roles (these are DB-level accounts to simulate 3 users)
CREATE USER IF NOT EXISTS 'admin_user'@'%' IDENTIFIED BY 'AdminPass@123';
GRANT 'role_admin' TO 'admin_user';
SET DEFAULT ROLE 'role_admin' TO 'admin_user';

CREATE USER IF NOT EXISTS 'faculty_user'@'%' IDENTIFIED BY 'FacultyPass@123';
GRANT 'role_faculty' TO 'faculty_user';
SET DEFAULT ROLE 'role_faculty' TO 'faculty_user';

CREATE USER IF NOT EXISTS 'student_user'@'%' IDENTIFIED BY 'StudentPass@123';
GRANT 'role_student' TO 'student_user';
SET DEFAULT ROLE 'role_student' TO 'student_user';


-- Revoke high-risk schema modification from non-admin roles
REVOKE DROP, ALTER, CREATE, DELETE ON capstoneprojectdb.* FROM 'role_faculty', 'role_student';

-- =====================================================
-- HELPFUL VERIFICATION QUERIES (run separately if desired)
-- =====================================================

-- Which teams a faculty mentors (example: faculty_id = 101)
-- SELECT * FROM Team WHERE Faculty_ID = 101;

-- Student view: meetings for student's team (use SRN)
-- SELECT m.* FROM Meeting m JOIN Team_Student ts ON m.Team_ID = ts.Team_ID WHERE ts.SRN = 'PES1UG21CS001';

-- Student: marks from reviews
-- SELECT * FROM Evaluation WHERE SRN = 'PES1UG21CS001';

-- Admin/faculty: claim team
-- CALL FacultyClaimTeam(101, 4); -- faculty 101 claims team 4

-- Student: create team with teammates
-- CALL StudentCreateTeam('PES1UG21CS002', 'PES1UG21CS004');

-- Student: add project for their team
-- CALL StudentAddProject('PES1UG21CS002', 'Smart Plant Monitor', 'Description here');

-- Faculty: schedule meeting
-- CALL FacultyScheduleMeeting(101, 1, '2025-11-10 14:00:00', 'Review of next milestone');

-- Faculty: add marks
-- CALL FacultyAddMarks(101, 1, 9.5, 'Updated marks after demo');

-- Useful function checks:
-- SELECT GetSemesterTotal('PES1UG21CS001', 7);

-- =====================================================
-- END OF SCRIPT
-- =====================================================
