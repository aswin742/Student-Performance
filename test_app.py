import unittest
import os
import sqlite3
import db
import app

class StudentPortalTests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Use temporary database for testing
        cls.test_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_database.db')
        db.DATABASE_PATH = cls.test_db_path
        
    def setUp(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        db.init_db()
        
        app.app.config['TESTING'] = True
        app.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.app.test_client()
        
    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
            
    def test_database_initialization(self):
        """Verify that tables are correctly initialized."""
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students';")
        self.assertIsNotNone(cursor.fetchone(), "students table should exist")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='marks';")
        self.assertIsNotNone(cursor.fetchone(), "marks table should exist")
        
        conn.close()
        
    def test_add_student(self):
        """Test adding student details to database."""
        # Valid department
        student_id = db.add_student("Alice Smith", "CSE")
        self.assertEqual(student_id, 1)
        
        # Invalid department should throw error
        with self.assertRaises(ValueError):
            db.add_student("Bob", "INVALID_DEPT")
            
        student = db.get_student_performance(1)
        self.assertIsNotNone(student)
        self.assertEqual(student['name'], "Alice Smith")
        self.assertEqual(student['department'], "CSE")
        self.assertEqual(student['subject_count'], 12) # CSE has 12 subjects
        self.assertEqual(student['graded_count'], 0) # No grades entered yet
        
    def test_add_or_update_marks(self):
        """Test adding and updating subject scores row-wise."""
        student_id = db.add_student("Bob Jones", "Civil") # Civil has 6 subjects
        
        # Enter partial marks
        partial_marks = {
            'Building Materials and Construction': 90,
            'Building Information Modeling (BIM)': 80
        }
        db.save_marks(student_id, partial_marks)
        
        student = db.get_student_performance(student_id)
        self.assertEqual(student['graded_count'], 2)
        self.assertEqual(student['marks']['Building Materials and Construction'], 90)
        # Average should be sum/6 (170/6 = 28.33)
        self.assertAlmostEqual(student['average'], 28.33, places=2)
        
        # Enter all marks
        all_marks = {
            'Building Materials and Construction': 90,
            'Building Information Modeling (BIM)': 80,
            'Highway and Traffic Engineering': 85,
            'Soil Mechanics': 90,
            'Water Supply and Wastewater Engineering': 95,
            'Construction Project Management': 100
        }
        db.save_marks(student_id, all_marks)
        
        student = db.get_student_performance(student_id)
        self.assertEqual(student['graded_count'], 6)
        # Sum = 90+80+85+90+95+100 = 540
        # Avg = 540/6 = 90.0
        self.assertEqual(student['total'], 540)
        self.assertEqual(student['average'], 90.0)
        self.assertEqual(student['grade'], "A")
        
    def test_grade_calculation(self):
        """Verify grade categorization boundaries."""
        self.assertEqual(db.calculate_grade(85), "A")
        self.assertEqual(db.calculate_grade(80), "A")
        self.assertEqual(db.calculate_grade(79.9), "B")
        self.assertEqual(db.calculate_grade(60), "B")
        self.assertEqual(db.calculate_grade(59), "C")
        self.assertEqual(db.calculate_grade(40), "C")
        self.assertEqual(db.calculate_grade(39.9), "F")
        self.assertEqual(db.calculate_grade(None), "N/A")
        
    def test_leaderboard_and_ranking_by_average(self):
        """Verify ranks are assigned based on average percentage descending (fair across depts)."""
        # Alice in Civil (6 subjects, sum = 480, avg = 80.0)
        id1 = db.add_student("Alice", "Civil")
        civil_marks = {s: 80 for s in db.DEPARTMENTS['Civil']['subjects']}
        db.save_marks(id1, civil_marks)
        
        # Bob in EEE (7 subjects, sum = 630, avg = 90.0)
        id2 = db.add_student("Bob", "EEE")
        eee_marks = {s: 90 for s in db.DEPARTMENTS['EEE']['subjects']}
        db.save_marks(id2, eee_marks)
        
        # Charlie in CSE (12 subjects, sum = 840, avg = 70.0)
        id3 = db.add_student("Charlie", "CSE")
        cse_marks = {s: 70 for s in db.DEPARTMENTS['CSE']['subjects']}
        db.save_marks(id3, cse_marks)
        
        # Rankings should sort by average: Bob (90) -> Alice (80) -> Charlie (70)
        # Even though Charlie has a much higher total score (840) than Bob (630)!
        leaderboard = db.get_leaderboard()
        self.assertEqual(len(leaderboard), 3)
        self.assertEqual(leaderboard[0]['student_id'], id2) # Bob (1st)
        self.assertEqual(leaderboard[1]['student_id'], id1) # Alice (2nd)
        self.assertEqual(leaderboard[2]['student_id'], id3) # Charlie (3rd)
        
    def test_flask_routing(self):
        """Check status code for routes and dynamic theming variables."""
        # Dashboard
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Institutional Overview", response.data)
        
        # Add Student POST
        response = self.client.post('/add_student', data={
            'name': 'Diana Prince',
            'department': 'ECE'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Should redirect directly to marks entry
        self.assertIn(b"Recording scores for <strong>Diana Prince</strong>", response.data)
        
        # Enter Marks POST
        # ECE has subjects: Digital Electronics, Analog Circuits, Microprocessors, etc.
        ece_subjects = db.DEPARTMENTS['ECE']['subjects']
        post_data = {sub: '85' for sub in ece_subjects}
        response = self.client.post('/enter_marks/1', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Should redirect to report card
        self.assertIn(b"Report Card - Diana Prince", response.data)
        
        # Department View
        response = self.client.get('/department_view/ECE')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ECE Department", response.data)
        
        # Leaderboard Overall
        response = self.client.get('/leaderboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Overall Standings Leaderboard", response.data)
        
        # Leaderboard with department filter
        response = self.client.get('/leaderboard?department=ECE')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ECE Standings Leaderboard", response.data)
        
        # Export CSV
        response = self.client.get('/export_csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')

if __name__ == '__main__':
    unittest.main()
