import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

# Fixed list of departments and subjects
DEPARTMENTS = {
    'CSE': {
        'name': 'Computer Science Engineering',
        'subjects': [
            'Computer Programming', 'Data Structures', 'Algorithms', 'Operating Systems',
            'Computer Networks', 'Database Management Systems', 'Software Engineering',
            'Artificial Intelligence', 'Machine Learning', 'OOPS', 
            'Computer Organization and Architecture', 'Cloud Computing'
        ]
    },
    'IT': {
        'name': 'Information Technology',
        'subjects': [
            'Computer Programming', 'Data Structures', 'Algorithms', 'Operating Systems',
            'Computer Networks', 'Database Management Systems', 'Software Engineering',
            'Artificial Intelligence', 'Machine Learning', 'OOPS', 
            'Computer Organization and Architecture', 'Cloud Computing'
        ]
    },
    'ECE': {
        'name': 'Electronics and Communication Engineering',
        'subjects': [
            'Digital Electronics', 'Analog Circuits', 'Microprocessors', 'Communication Systems',
            'Signal Processing', 'VLSI Design', 'Embedded Systems', 'Electromagnetic Theory'
        ]
    },
    'EEE': {
        'name': 'Electrical and Electronics Engineering',
        'subjects': [
            'Circuit Theory', 'Electrical Machines', 'Power Systems', 'Control Systems',
            'Power Electronics', 'Analog Electronics', 'Digital Electronics'
        ]
    },
    'Mechanical': {
        'name': 'Mechanical Engineering',
        'subjects': [
            'Thermodynamics', 'Fluid Mechanics', 'Strength of Materials', 
            'Manufacturing Processes', 'Theory of Machines (TOM)', 'Machine Design', 
            'Computer Aided Design (CAD)'
        ]
    },
    'Civil': {
        'name': 'Civil Engineering',
        'subjects': [
            'Building Materials and Construction', 'Building Information Modeling (BIM)', 
            'Highway and Traffic Engineering', 'Soil Mechanics', 
            'Water Supply and Wastewater Engineering', 'Construction Project Management'
        ]
    }
}

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Drop existing tables to recreate schema
    cursor.execute("DROP TABLE IF EXISTS marks")
    cursor.execute("DROP TABLE IF EXISTS students")
    
    # Create students table
    cursor.execute('''
        CREATE TABLE students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL
        )
    ''')
    
    # Create marks table (stores marks row-wise per subject)
    cursor.execute('''
        CREATE TABLE marks (
            mark_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            marks INTEGER NOT NULL CHECK(marks >= 0 AND marks <= 100),
            FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
            UNIQUE(student_id, subject_name)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_student(name, department):
    if department not in DEPARTMENTS:
        raise ValueError(f"Invalid department: {department}")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO students (name, department) VALUES (?, ?)",
        (name, department)
    )
    student_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return student_id

def save_marks(student_id, subject_marks):
    """
    subject_marks should be a dict: {subject_name: score}
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify student exists
    cursor.execute("SELECT department FROM students WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        raise ValueError(f"Student with ID {student_id} does not exist.")
        
    dept = student['department']
    valid_subjects = DEPARTMENTS[dept]['subjects']
    
    # Insert or update each subject
    for sub_name, score in subject_marks.items():
        if sub_name not in valid_subjects:
            continue # skip subjects not belonging to this department
        score_val = int(score)
        cursor.execute('''
            INSERT INTO marks (student_id, subject_name, marks)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id, subject_name) DO UPDATE SET marks = excluded.marks
        ''', (student_id, sub_name, score_val))
        
    conn.commit()
    conn.close()

def calculate_grade(average):
    if average is None:
        return "N/A"
    if average >= 80:
        return "A"
    elif average >= 60:
        return "B"
    elif average >= 40:
        return "C"
    else:
        return "F"

def get_student_performance(student_id):
    """
    Returns student details, marks dict, total, average, grade, and rank
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT student_id, name, department FROM students WHERE student_id = ?", (student_id,))
    student_row = cursor.fetchone()
    if not student_row:
        conn.close()
        return None
        
    student = dict(student_row)
    dept = student['department']
    subjects = DEPARTMENTS[dept]['subjects']
    
    # Fetch marks
    cursor.execute("SELECT subject_name, marks FROM marks WHERE student_id = ?", (student_id,))
    marks_rows = cursor.fetchall()
    conn.close()
    
    marks_dict = {row['subject_name']: row['marks'] for row in marks_rows}
    
    # Calculate performance if all or some marks are entered
    if marks_dict:
        total = sum(marks_dict.values())
        # Divide by total subjects in department to reflect overall completion
        avg = round(total / len(subjects), 2)
        grade = calculate_grade(avg)
    else:
        total = 0
        avg = 0.0
        grade = "N/A"
        
    student.update({
        'marks': marks_dict,
        'total': total,
        'average': avg,
        'grade': grade,
        'subject_count': len(subjects),
        'graded_count': len(marks_dict)
    })
    return student

def get_all_students_summary(department_filter=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if department_filter:
        cursor.execute("SELECT student_id, name, department FROM students WHERE department = ? ORDER BY student_id DESC", (department_filter,))
    else:
        cursor.execute("SELECT student_id, name, department FROM students ORDER BY student_id DESC")
        
    student_rows = cursor.fetchall()
    conn.close()
    
    students_list = []
    for row in student_rows:
        perf = get_student_performance(row['student_id'])
        students_list.append(perf)
        
    return students_list

def get_leaderboard(department_filter=None):
    """
    Returns list of students with scores, sorted by average descending, with ranks assigned.
    Only students who have marks are ranked.
    """
    students = get_all_students_summary(department_filter)
    
    # Filter only students who have entered marks
    scored_students = [s for s in students if s['graded_count'] > 0]
    
    # Sort by average descending, then name ascending
    scored_students.sort(key=lambda x: (-x['average'], x['name']))
    
    # Assign ranks
    for idx, s in enumerate(scored_students):
        s['rank'] = idx + 1
        
    return scored_students

def get_department_stats(dept):
    if dept not in DEPARTMENTS:
        return None
        
    students = get_all_students_summary(dept)
    total_students = len(students)
    
    scored_students = [s for s in students if s['graded_count'] > 0]
    
    if scored_students:
        dept_avg = round(sum(s['average'] for s in scored_students) / len(scored_students), 2)
        # Find top student by average
        top_student = max(scored_students, key=lambda x: x['average'])
        top_scorer_name = top_student['name']
        top_score = top_student['average']
    else:
        dept_avg = 0.0
        top_scorer_name = "N/A"
        top_score = 0.0
        
    return {
        'code': dept,
        'name': DEPARTMENTS[dept]['name'],
        'total_students': total_students,
        'average_performance': dept_avg,
        'top_scorer': top_scorer_name,
        'top_score': top_score,
        'subjects': DEPARTMENTS[dept]['subjects']
    }

def get_dashboard_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Overall count
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]
    
    # Get all scored students
    all_scored = get_leaderboard()
    if all_scored:
        overall_avg = round(sum(s['average'] for s in all_scored) / len(all_scored), 2)
        top_student = all_scored[0]
        top_scorer_name = top_student['name']
        top_score = top_student['average']
    else:
        overall_avg = 0.0
        top_scorer_name = "N/A"
        top_score = 0.0
        
    conn.close()
    
    # Get stats for each department
    dept_summaries = {}
    for d_code in DEPARTMENTS.keys():
        dept_summaries[d_code] = get_department_stats(d_code)
        
    return {
        'total_students': total_students,
        'class_average': overall_avg,
        'top_scorer': top_scorer_name,
        'top_score': top_score,
        'departments': dept_summaries
    }
