from flask import Flask, render_template, request, redirect, url_for, flash, Response
import db
import csv
import io

app = Flask(__name__)
app.secret_key = "smart_department_analytics_portal_secret_key"

# Initialize database (wipes old tables and sets up new schema)
db.init_db()

@app.route('/')
def dashboard():
    summary = db.get_dashboard_summary()
    students = db.get_all_students_summary()
    
    # We pass the department structures so the UI can list them
    return render_template('index.html', 
                           summary=summary, 
                           students=students, 
                           departments_info=db.DEPARTMENTS,
                           theme='default')

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        
        if not name or not department:
            flash("Student name and department are required!", "danger")
            return redirect(url_for('add_student'))
            
        if department not in db.DEPARTMENTS:
            flash("Invalid department selected!", "danger")
            return redirect(url_for('add_student'))
            
        try:
            student_id = db.add_student(name, department)
            flash(f"Student '{name}' registered successfully! Enter marks below.", "success")
            # Redirect directly to marks entry for high-quality UX
            return redirect(url_for('enter_marks', student_id=student_id))
        except Exception as e:
            flash(f"Error adding student: {str(e)}", "danger")
            return redirect(url_for('add_student'))
            
    return render_template('add_student.html', departments=db.DEPARTMENTS, theme='default')

@app.route('/enter_marks/<int:student_id>', methods=['GET', 'POST'])
def enter_marks(student_id):
    student = db.get_student_performance(student_id)
    if not student:
        flash("Student not found!", "danger")
        return redirect(url_for('dashboard'))
        
    dept_code = student['department']
    subjects = db.DEPARTMENTS[dept_code]['subjects']
    
    if request.method == 'POST':
        subject_marks = {}
        for sub in subjects:
            val = request.form.get(sub)
            if val is None or val.strip() == '':
                flash(f"Please enter marks for {sub}!", "danger")
                return redirect(url_for('enter_marks', student_id=student_id))
            try:
                score = int(val)
                if score < 0 or score > 100:
                    flash(f"Marks for {sub} must be between 0 and 100!", "danger")
                    return redirect(url_for('enter_marks', student_id=student_id))
                subject_marks[sub] = score
            except ValueError:
                flash(f"Marks for {sub} must be a valid integer!", "danger")
                return redirect(url_for('enter_marks', student_id=student_id))
                
        try:
            db.save_marks(student_id, subject_marks)
            flash("Marks updated successfully!", "success")
            return redirect(url_for('report', student_id=student_id))
        except Exception as e:
            flash(f"Error saving marks: {str(e)}", "danger")
            return redirect(url_for('enter_marks', student_id=student_id))
            
    return render_template('enter_marks.html', student=student, subjects=subjects, theme=dept_code.lower())

@app.route('/report/<int:student_id>')
def report(student_id):
    student = db.get_student_performance(student_id)
    if not student:
        flash("Student not found!", "danger")
        return redirect(url_for('dashboard'))
        
    dept_code = student['department']
    
    # Calculate ranks
    overall_leaderboard = db.get_leaderboard()
    dept_leaderboard = db.get_leaderboard(dept_code)
    
    overall_rank = "N/A"
    dept_rank = "N/A"
    
    if student['graded_count'] > 0:
        for s in overall_leaderboard:
            if s['student_id'] == student_id:
                overall_rank = s['rank']
                break
        for s in dept_leaderboard:
            if s['student_id'] == student_id:
                dept_rank = s['rank']
                break
                
    return render_template('report.html', 
                           student=student, 
                           overall_rank=overall_rank, 
                           dept_rank=dept_rank, 
                           theme=dept_code.lower())

@app.route('/department_view/<string:dept>')
def department_view(dept):
    if dept not in db.DEPARTMENTS:
        flash(f"Department '{dept}' not found!", "danger")
        return redirect(url_for('dashboard'))
        
    stats = db.get_department_stats(dept)
    students = db.get_all_students_summary(dept)
    
    return render_template('department_view.html', 
                           stats=stats, 
                           students=students, 
                           theme=dept.lower())

@app.route('/leaderboard')
def leaderboard():
    # Show overall rankings
    leaderboard_data = db.get_leaderboard()
    
    # Optional department filter
    selected_dept = request.args.get('department', '').strip()
    if selected_dept in db.DEPARTMENTS:
        leaderboard_data = db.get_leaderboard(selected_dept)
        theme_val = selected_dept.lower()
    else:
        selected_dept = 'ALL'
        theme_val = 'default'
        
    return render_template('leaderboard.html', 
                           leaderboard=leaderboard_data, 
                           selected_dept=selected_dept, 
                           departments=db.DEPARTMENTS,
                           theme=theme_val)

@app.route('/export_csv')
def export_csv():
    dept = request.args.get('department', '').strip()
    
    if dept in db.DEPARTMENTS:
        leaderboard_data = db.get_leaderboard(dept)
        filename = f"leaderboard_{dept.lower()}.csv"
    else:
        leaderboard_data = db.get_leaderboard()
        filename = "leaderboard_overall.csv"
        
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Rank', 'Name', 'Department', 'Total Score', 'Average Percentage', 'Grade', 'Graded Subjects'])
    
    for row in leaderboard_data:
        writer.writerow([
            row.get('rank', 'N/A'),
            row['name'],
            row['department'],
            row['total'],
            f"{row['average']}%",
            row['grade'],
            f"{row['graded_count']}/{row['subject_count']}"
        ])
        
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
