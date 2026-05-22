from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cambia-esta-clave-secreta-en-produccion'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tutorpro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'png', 'jpg', 'jpeg', 'docx', 'pptx', 'mp4', 'py'}

db = SQLAlchemy(app)

# ─────────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='student')  # admin, student, parent
    avatar_initials = db.Column(db.String(3))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    submissions = db.relationship('Submission', backref='student', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    level = db.Column(db.String(50))
    duration = db.Column(db.String(50))
    price = db.Column(db.Float, default=0)
    is_published = db.Column(db.Boolean, default=False)
    icon = db.Column(db.String(50), default='ti-code')
    color = db.Column(db.String(30), default='blue')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modules = db.relationship('Module', backref='course', lazy=True, cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, default=0)
    activities = db.relationship('Activity', backref='module', lazy=True, cascade='all, delete-orphan')
    materials = db.relationship('Material', backref='module', lazy=True, cascade='all, delete-orphan')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    activity_type = db.Column(db.String(30), default='quiz')  # quiz, code, text, multiple_choice
    content = db.Column(db.Text)  # JSON with questions/tasks
    max_score = db.Column(db.Integer, default=100)
    order = db.Column(db.Integer, default=0)
    submissions = db.relationship('Submission', backref='activity', lazy=True)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(300))
    file_type = db.Column(db.String(20))
    file_size = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Integer, default=0)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    answers = db.Column(db.Text)  # JSON
    score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    auto_graded = db.Column(db.Boolean, default=False)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    sender = db.relationship('User', foreign_keys=[sender_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'error': 'Acceso denegado'}), 403
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
# RUTAS PÚBLICAS
# ─────────────────────────────────────────────

@app.route('/')
def index():
    courses = Course.query.filter_by(is_published=True).all()
    return render_template('index.html', courses=courses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        user = User.query.filter_by(email=data.get('email')).first()
        if user and check_password_hash(user.password_hash, data.get('password')):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            return jsonify({'success': True, 'role': user.role, 'name': user.name})
        return jsonify({'success': False, 'error': 'Credenciales incorrectas'}), 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        if User.query.filter_by(email=data.get('email')).first():
            return jsonify({'success': False, 'error': 'El correo ya está registrado'}), 400
        initials = ''.join([n[0].upper() for n in data.get('name', 'U').split()[:2]])
        user = User(
            name=data.get('name'),
            email=data.get('email'),
            password_hash=generate_password_hash(data.get('password')),
            role=data.get('role', 'student'),
            avatar_initials=initials
        )
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['user_name'] = user.name
        return jsonify({'success': True, 'role': user.role})
    return render_template('register.html')

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template('dashboard.html', user=user)

@app.route('/admin')
@admin_required
def admin_dashboard():
    students = User.query.filter_by(role='student').all()
    courses = Course.query.all()
    total_submissions = Submission.query.count()
    return render_template('admin.html',
        students=students,
        courses=courses,
        total_submissions=total_submissions
    )

# ─────────────────────────────────────────────
# API - CURSOS
# ─────────────────────────────────────────────

@app.route('/api/courses', methods=['GET'])
def api_courses():
    courses = Course.query.filter_by(is_published=True).all()
    return jsonify([{
        'id': c.id, 'title': c.title, 'description': c.description,
        'level': c.level, 'duration': c.duration, 'price': c.price,
        'icon': c.icon, 'color': c.color,
        'students': len(c.enrollments)
    } for c in courses])

@app.route('/api/courses', methods=['POST'])
@admin_required
def create_course():
    data = request.get_json()
    course = Course(
        title=data['title'],
        description=data.get('description', ''),
        level=data.get('level', 'Básico'),
        duration=data.get('duration', ''),
        price=data.get('price', 0),
        icon=data.get('icon', 'ti-code'),
        color=data.get('color', 'blue'),
        is_published=data.get('is_published', False)
    )
    db.session.add(course)
    db.session.commit()
    return jsonify({'success': True, 'id': course.id})

@app.route('/api/courses/<int:cid>', methods=['PUT'])
@admin_required
def update_course(cid):
    course = Course.query.get_or_404(cid)
    data = request.get_json()
    for field in ['title', 'description', 'level', 'duration', 'price', 'icon', 'color', 'is_published']:
        if field in data:
            setattr(course, field, data[field])
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/courses/<int:cid>', methods=['DELETE'])
@admin_required
def delete_course(cid):
    course = Course.query.get_or_404(cid)
    db.session.delete(course)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/courses/<int:cid>/enroll', methods=['POST'])
@login_required
def enroll(cid):
    existing = Enrollment.query.filter_by(student_id=session['user_id'], course_id=cid).first()
    if existing:
        return jsonify({'success': False, 'error': 'Ya estás inscrito'})
    enrollment = Enrollment(student_id=session['user_id'], course_id=cid)
    db.session.add(enrollment)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/my-courses')
@login_required
def my_courses():
    enrollments = Enrollment.query.filter_by(student_id=session['user_id']).all()
    result = []
    for e in enrollments:
        c = e.course
        result.append({
            'id': c.id, 'title': c.title, 'level': c.level,
            'progress': e.progress, 'icon': c.icon, 'color': c.color,
            'modules': len(c.modules)
        })
    return jsonify(result)

# ─────────────────────────────────────────────
# API - MÓDULOS Y ACTIVIDADES
# ─────────────────────────────────────────────

@app.route('/api/courses/<int:cid>/modules')
@login_required
def get_modules(cid):
    course = Course.query.get_or_404(cid)
    modules = sorted(course.modules, key=lambda m: m.order)
    result = []
    for m in modules:
        activities = []
        for a in sorted(m.activities, key=lambda x: x.order):
            sub = Submission.query.filter_by(
                student_id=session['user_id'], activity_id=a.id
            ).first()
            activities.append({
                'id': a.id, 'title': a.title, 'type': a.activity_type,
                'max_score': a.max_score,
                'submitted': sub is not None,
                'score': sub.score if sub else None
            })
        materials = [{'id': mat.id, 'title': mat.title, 'type': mat.file_type, 'path': mat.file_path}
                     for mat in m.materials]
        result.append({
            'id': m.id, 'title': m.title, 'order': m.order,
            'activities': activities, 'materials': materials
        })
    return jsonify(result)

@app.route('/api/modules', methods=['POST'])
@admin_required
def create_module():
    data = request.get_json()
    module = Module(
        course_id=data['course_id'],
        title=data['title'],
        order=data.get('order', 0)
    )
    db.session.add(module)
    db.session.commit()
    return jsonify({'success': True, 'id': module.id})

@app.route('/api/activities', methods=['POST'])
@admin_required
def create_activity():
    data = request.get_json()
    activity = Activity(
        module_id=data['module_id'],
        title=data['title'],
        description=data.get('description', ''),
        activity_type=data.get('type', 'multiple_choice'),
        content=json.dumps(data.get('content', {})),
        max_score=data.get('max_score', 100),
        order=data.get('order', 0)
    )
    db.session.add(activity)
    db.session.commit()
    return jsonify({'success': True, 'id': activity.id})

@app.route('/api/activities/<int:aid>')
@login_required
def get_activity(aid):
    a = Activity.query.get_or_404(aid)
    content = json.loads(a.content) if a.content else {}
    return jsonify({
        'id': a.id, 'title': a.title, 'description': a.description,
        'type': a.activity_type, 'content': content, 'max_score': a.max_score
    })

# ─────────────────────────────────────────────
# API - ENVÍO Y CALIFICACIÓN AUTOMÁTICA
# ─────────────────────────────────────────────

@app.route('/api/activities/<int:aid>/submit', methods=['POST'])
@login_required
def submit_activity(aid):
    activity = Activity.query.get_or_404(aid)
    data = request.get_json()
    answers = data.get('answers', {})

    score = None
    feedback = ''
    auto_graded = False

    if activity.activity_type == 'multiple_choice':
        content = json.loads(activity.content) if activity.content else {}
        questions = content.get('questions', [])
        if questions:
            correct = sum(1 for q in questions if str(answers.get(str(q['id']))) == str(q['correct']))
            score = round((correct / len(questions)) * activity.max_score, 1)
            feedback = f'Respondiste correctamente {correct} de {len(questions)} preguntas.'
            auto_graded = True

    elif activity.activity_type == 'code':
        # Calificación con IA - se llama desde el frontend directamente
        score = None
        feedback = 'Pendiente de revisión por IA'
        auto_graded = False

    sub = Submission.query.filter_by(
        student_id=session['user_id'], activity_id=aid
    ).first()
    if sub:
        sub.answers = json.dumps(answers)
        sub.score = score
        sub.feedback = feedback
        sub.auto_graded = auto_graded
        sub.submitted_at = datetime.utcnow()
    else:
        sub = Submission(
            student_id=session['user_id'],
            activity_id=aid,
            answers=json.dumps(answers),
            score=score,
            feedback=feedback,
            auto_graded=auto_graded
        )
        db.session.add(sub)

    db.session.commit()
    return jsonify({'success': True, 'score': score, 'feedback': feedback, 'auto_graded': auto_graded})

# ─────────────────────────────────────────────
# API - MATERIALES
# ─────────────────────────────────────────────

@app.route('/api/materials/upload', methods=['POST'])
@admin_required
def upload_material():
    if 'file' not in request.files:
        return jsonify({'error': 'No se recibió archivo'}), 400
    file = request.files['file']
    module_id = request.form.get('module_id')
    title = request.form.get('title', file.filename)
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        ext = filename.rsplit('.', 1)[1].lower()
        size = os.path.getsize(filepath)
        material = Material(
            module_id=module_id,
            title=title,
            file_path=f'/static/uploads/{filename}',
            file_type=ext,
            file_size=size
        )
        db.session.add(material)
        db.session.commit()
        return jsonify({'success': True, 'id': material.id, 'path': material.file_path})
    return jsonify({'error': 'Tipo de archivo no permitido'}), 400

@app.route('/api/materials/<int:mid>', methods=['DELETE'])
@admin_required
def delete_material(mid):
    mat = Material.query.get_or_404(mid)
    full_path = os.path.join(os.path.dirname(__file__), mat.file_path.lstrip('/'))
    if os.path.exists(full_path):
        os.remove(full_path)
    db.session.delete(mat)
    db.session.commit()
    return jsonify({'success': True})

# ─────────────────────────────────────────────
# API - ALUMNOS (ADMIN)
# ─────────────────────────────────────────────

@app.route('/api/students')
@admin_required
def api_students():
    students = User.query.filter_by(role='student').all()
    result = []
    for s in students:
        enrollments = len(s.enrollments)
        submissions = len(s.submissions)
        avg_score = None
        scored = [sub.score for sub in s.submissions if sub.score is not None]
        if scored:
            avg_score = round(sum(scored) / len(scored), 1)
        result.append({
            'id': s.id, 'name': s.name, 'email': s.email,
            'initials': s.avatar_initials or s.name[:2].upper(),
            'enrolled': enrollments,
            'submissions': submissions,
            'avg_score': avg_score,
            'joined': s.created_at.strftime('%d/%m/%Y')
        })
    return jsonify(result)

@app.route('/api/students/<int:sid>/progress')
@admin_required
def student_progress(sid):
    student = User.query.get_or_404(sid)
    enrollments = Enrollment.query.filter_by(student_id=sid).all()
    data = []
    for e in enrollments:
        course = e.course
        activities_total = sum(len(m.activities) for m in course.modules)
        submitted = Submission.query.filter_by(student_id=sid).filter(
            Submission.activity_id.in_(
                [a.id for m in course.modules for a in m.activities]
            )
        ).count()
        progress = round((submitted / activities_total * 100) if activities_total else 0)
        data.append({
            'course': course.title,
            'progress': progress,
            'submitted': submitted,
            'total': activities_total
        })
    return jsonify({'name': student.name, 'courses': data})

# ─────────────────────────────────────────────
# API - CHAT
# ─────────────────────────────────────────────

@app.route('/api/chat/contacts')
@login_required
def chat_contacts():
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        contacts = User.query.filter(User.id != user.id).all()
    else:
        contacts = User.query.filter_by(role='admin').all()
    return jsonify([{
        'id': c.id, 'name': c.name,
        'initials': c.avatar_initials or c.name[:2].upper(),
        'role': c.role
    } for c in contacts])

@app.route('/api/chat/messages/<int:other_id>')
@login_required
def get_messages(other_id):
    uid = session['user_id']
    messages = ChatMessage.query.filter(
        ((ChatMessage.sender_id == uid) & (ChatMessage.recipient_id == other_id)) |
        ((ChatMessage.sender_id == other_id) & (ChatMessage.recipient_id == uid))
    ).order_by(ChatMessage.sent_at).all()
    ChatMessage.query.filter_by(recipient_id=uid, sender_id=other_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify([{
        'id': m.id,
        'sender_id': m.sender_id,
        'sender_name': m.sender.name,
        'message': m.message,
        'sent_at': m.sent_at.strftime('%H:%M'),
        'is_mine': m.sender_id == uid
    } for m in messages])

@app.route('/api/chat/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    msg = ChatMessage(
        sender_id=session['user_id'],
        recipient_id=data['recipient_id'],
        message=data['message']
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({'success': True, 'id': msg.id, 'sent_at': msg.sent_at.strftime('%H:%M')})

@app.route('/api/chat/unread')
@login_required
def unread_count():
    count = ChatMessage.query.filter_by(recipient_id=session['user_id'], is_read=False).count()
    return jsonify({'count': count})

# ─────────────────────────────────────────────
# API - SESIÓN ACTUAL
# ─────────────────────────────────────────────

@app.route('/api/me')
def api_me():
    if 'user_id' not in session:
        return jsonify({'logged_in': False})
    user = User.query.get(session['user_id'])
    return jsonify({
        'logged_in': True,
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'initials': user.avatar_initials or user.name[:2].upper()
    })

# ─────────────────────────────────────────────
# API - REVISIÓN AUTOMÁTICA CON IA
# ─────────────────────────────────────────────

@app.route('/api/ai-review', methods=['POST'])
@login_required
def ai_review():
    """Revisión de código con Anthropic Claude"""
    import anthropic as anthropic_client
    data = request.get_json()
    code = data.get('code', '')
    activity_id = data.get('activity_id')

    activity = Activity.query.get(activity_id) if activity_id else None
    context = ''
    if activity:
        content = json.loads(activity.content) if activity.content else {}
        context = content.get('instructions', activity.title)

    # Actualizar la entrega con el código enviado
    sub = Submission.query.filter_by(
        student_id=session['user_id'], activity_id=activity_id
    ).first()
    if sub:
        sub.answers = json.dumps({'code': code})
        db.session.commit()

    try:
        client = anthropic_client.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))
        prompt = f"""Eres un maestro de Python amigable y constructivo para estudiantes de secundaria/preparatoria.

Tarea asignada: {context}

Código del alumno:
```python
{code}
```

Por favor revisa este código y proporciona:
1. Una calificación del 0 al 100
2. Retroalimentación clara sobre qué está bien
3. Sugerencias de mejora específicas (si aplica)
4. Un ejemplo de mejora si hay errores importantes

Responde en español, con un tono alentador. Sé breve y concreto (máximo 200 palabras).
Al final incluye exactamente esta línea: SCORE: [número del 0 al 100]"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = message.content[0].text

        # Extraer puntuación
        score = None
        for line in full_response.split('\n'):
            if line.strip().startswith('SCORE:'):
                try:
                    score = int(line.split(':')[1].strip())
                except:
                    pass

        feedback_text = full_response.replace(f'SCORE: {score}', '').strip() if score else full_response

        # Guardar resultado
        if sub and score is not None:
            sub.score = score
            sub.feedback = feedback_text
            sub.auto_graded = True
            db.session.commit()

        return jsonify({'success': True, 'feedback': feedback_text, 'score': score})

    except Exception as e:
        return jsonify({'success': False, 'feedback': f'Error al conectar con IA: {str(e)}', 'score': None}), 500

# ─────────────────────────────────────────────
# PÁGINAS SPA
# ─────────────────────────────────────────────

@app.route('/curso/<int:cid>')
@login_required
def course_view(cid):
    course = Course.query.get_or_404(cid)
    return render_template('course.html', course=course)

@app.route('/actividad/<int:aid>')
@login_required
def activity_view(aid):
    activity = Activity.query.get_or_404(aid)
    return render_template('activity.html', activity=activity)

# ─────────────────────────────────────────────
# INICIALIZACIÓN
# ─────────────────────────────────────────────

def seed_data():
    """Crea datos iniciales si la BD está vacía"""
    if User.query.count() > 0:
        return
    admin = User(
        name='Ing. Jesús Aguilar',
        email='admin@tutorpro.com',
        password_hash=generate_password_hash('admin123'),
        role='admin',
        avatar_initials='JA'
    )
    db.session.add(admin)

    course = Course(
        title='Python Avanzado',
        description='Curso completo de Python con POO, manejo de archivos, Pygame y proyecto final.',
        level='Avanzado',
        duration='10 semanas',
        price=1500,
        icon='ti-brand-python',
        color='blue',
        is_published=True
    )
    db.session.add(course)
    db.session.flush()

    module = Module(course_id=course.id, title='Programación Orientada a Objetos', order=1)
    db.session.add(module)
    db.session.flush()

    questions = [
        {"id": 1, "text": "¿Qué palabra clave se usa para definir una clase en Python?", "options": ["def", "class", "object", "type"], "correct": "class"},
        {"id": 2, "text": "¿Cómo se llama el método constructor en Python?", "options": ["constructor()", "__init__()", "start()", "__new__()"], "correct": "__init__()"},
        {"id": 3, "text": "¿Qué significa 'self' en un método de clase?", "options": ["El módulo actual", "La clase padre", "La instancia actual", "Una variable global"], "correct": "La instancia actual"},
    ]
    activity = Activity(
        module_id=module.id,
        title='Quiz: Conceptos básicos de POO',
        description='Evalúa tu comprensión de los fundamentos de la programación orientada a objetos.',
        activity_type='multiple_choice',
        content=json.dumps({'questions': questions}),
        max_score=100,
        order=1
    )
    db.session.add(activity)
    db.session.commit()
    print("✅ Datos iniciales creados. Admin: admin@tutorpro.com / admin123")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True, port=5000)
