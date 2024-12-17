from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    # Database models
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password = db.Column(db.String(200), nullable=False)
        role = db.Column(db.String(50), nullable=False)
        name = db.Column(db.String(100), nullable=False)
        subject = db.Column(db.String(100), nullable=True)  # For teachers
        class_name = db.Column(db.String(100), nullable=True)  # For students

    class ClassTeacher(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        class_name = db.Column(db.String(100), nullable=False)
        teacher_name = db.Column(db.String(100), nullable=False)
        subject = db.Column(db.String(100), nullable=False)

    class Class(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), unique=True, nullable=False)
        teacher = db.Column(db.String(100), nullable=False)

    class Lesson(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
        lesson_name = db.Column(db.String(100), nullable=False)
        video_url = db.Column(db.String(200), nullable=False)

    # Create the database tables
    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        if 'email' in session:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            name = request.form['name']
            role = request.form['role']
        
            # Explicitly get the subject, ensuring it's not None;
            # Not getting it this way can cause errors on the student dashboard
            subject = request.form.get('subject', '')
            class_name = request.form.get('class_name', '')

            # Debugging print
            print(f"Registering: Name: {name}, Role: {role}, Subject: {subject}, Class: {class_name}")

            # Check if the email is already registered
            if User.query.filter_by(email=email).first():
                return "Email already registered.", 400

            # Create a new user with the provided information
            new_user = User(
                email=email, 
                password=password, 
                role=role, 
                name=name, 
                subject=subject, 
                class_name=class_name
            )
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('index'))

        return render_template('register.html')
    
    @app.route('/login', methods=['POST'])
    def login():
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['email'] = email
            session['role'] = user.role
            session['name'] = user.name
        
            # Store the class name in the session for students
            if user.role == 'student':
                session['class_name'] = user.class_name  # Store the class name in the session

            return redirect(url_for('dashboard'))

        return "Invalid email or password.", 400
    
    @app.route('/dashboard')
    def dashboard():
        if 'email' not in session:
            return redirect(url_for('index'))

        if session['role'] == 'teacher':
            # Get unique classes for this teacher
            classes = []
            class_teachers = ClassTeacher.query.filter_by(teacher_name=session['name']).all()
        
            for class_teacher in class_teachers:
                # Find lessons for this class
                class_lessons = Lesson.query.filter_by(class_id=class_teacher.id).all()
            
                # Create a class object with name and lessons
                class_obj = {
                    'name': class_teacher.class_name,
                    'lessons': class_lessons
                }
                classes.append(class_obj)
        
            return render_template('dashboard_teacher.html', classes=classes)
    
        elif session['role'] == 'student':
            # Get unique subjects for the student's class
            student_subjects = ClassTeacher.query.filter_by(class_name=session['class_name']).all()
            return render_template('dashboard_student.html', student_subjects=student_subjects)
    
    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

    @app.route('/add-class', methods=['POST'])
    def add_class():
        class_name = request.form['class_name']
    
        # Find the current user to get their subject
        user = User.query.filter_by(email=session['email']).first()
        subject = user.subject if user and user.subject else 'Unknown'

        # Check if the class-teacher combination already exists
        existing_class_teacher = ClassTeacher.query.filter_by(
            class_name=class_name, 
            teacher_name=session['name']
        ).first()

        if not existing_class_teacher:
            # Create a new class-teacher relationship
            new_class_teacher = ClassTeacher(
                class_name=class_name, 
                teacher_name=session['name'],
                subject=subject
            )
            db.session.add(new_class_teacher)
            db.session.commit()

        return redirect(url_for('dashboard'))

    @app.route('/add-lesson', methods=['POST'])
    def add_lesson():
        class_name = request.form['class_name']
        lesson_name = request.form['lesson_name']
        video_url = request.form['video_url']

        # Find the ClassTeacher entry for this class and teacher
        class_teacher = ClassTeacher.query.filter_by(
            class_name=class_name, 
            teacher_name=session['name']
        ).first()

        if class_teacher:
            # Create a new lesson associated with this class
            new_lesson = Lesson(
                class_id=class_teacher.id, 
                lesson_name=lesson_name, 
                video_url=video_url
            )
            db.session.add(new_lesson)
            db.session.commit()

        return redirect(url_for('dashboard'))
    
    @app.route('/view-class-lessons/<class_name>')
    def view_class_lessons(class_name):
        if 'email' not in session or session['role'] != 'teacher':
            return redirect(url_for('index'))

        # Find the ClassTeacher entry for this class and teacher
        class_teacher = ClassTeacher.query.filter_by(
        class_name=class_name, 
        teacher_name=session['name']
        ).first()

        # Get lessons for this specific class
        lessons = []
        if class_teacher:
            lessons = Lesson.query.filter_by(class_id=class_teacher.id).all()

        return render_template('class_lessons.html', class_name=class_name, lessons=lessons)
    
    @app.route('/subject/<subject>/teacher/<teacher>')
    def view_subject_lessons(subject, teacher):
        # Find all ClassTeacher entries for this subject and teacher
        class_teachers = ClassTeacher.query.filter_by(
            subject=subject, 
            teacher_name=teacher
        ).all()
    
        lessons = []
        for class_teacher in class_teachers:
            # Get lessons for each class
            class_lessons = Lesson.query.filter_by(class_id=class_teacher.id).all()
            lessons.extend(class_lessons)
    
        return render_template('subject_lessons.html', 
                            subject=subject, 
                            teacher=teacher, 
                            lessons=lessons)

    @app.route('/class/<class_name>')
    def view_class(class_name):
        # Get all teachers for this class
        class_teachers = ClassTeacher.query.filter_by(class_name=class_name).all()
    
        lessons = []
        for class_teacher in class_teachers:
            class_lessons = Lesson.query.filter_by(class_id=class_teacher.id).all()
            lessons.extend(class_lessons)
    
        return render_template('class_view.html', class_name=class_name, class_data={'lessons': lessons})

    return app