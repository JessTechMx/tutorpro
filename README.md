# TutorPro 🎓

Plataforma de clases particulares para Ing. Jesús Aguilar Núñez.

## Características

- **Página principal** con oferta de cursos publicados
- **Panel de alumno** con mis cursos, actividades y materiales
- **Revisión automática** de quizzes y código con IA (Claude)
- **Subida de materiales** (PDF, DOCX, PPTX, PY, imágenes, video)
- **Chat en tiempo real** entre maestro, alumnos y padres
- **Panel de maestro** con seguimiento individual de cada alumno
- **Sistema de progreso** por módulo y actividad

---

## Instalación

### 1. Requisitos previos
- Python 3.9 o superior
- pip

### 2. Clonar / descomprimir el proyecto

```bash
cd tutorpro
```

### 3. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS / Linux:
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar tu API Key de Anthropic (para revisión IA)

```bash
# Windows (PowerShell):
$env:ANTHROPIC_API_KEY = "sk-ant-tu-clave-aqui"

# macOS / Linux:
export ANTHROPIC_API_KEY="sk-ant-tu-clave-aqui"
```

> Obtén tu API key en: https://console.anthropic.com/

### 6. Inicializar la base de datos

```bash
python setup.py
```

### 7. Ejecutar la aplicación

```bash
python app.py
```

### 8. Abrir en el navegador

```
http://localhost:5000
```

---

## Credenciales iniciales

| Rol | Correo | Contraseña |
|-----|--------|------------|
| Maestro (Admin) | admin@tutorpro.com | admin123 |

---

## Estructura del proyecto

```
tutorpro/
├── app.py              # Backend principal (Flask)
├── setup.py            # Inicialización de BD
├── requirements.txt    # Dependencias Python
├── instance/
│   └── tutorpro.db    # Base de datos SQLite (se crea sola)
├── static/
│   ├── css/
│   │   └── style.css  # Estilos
│   └── uploads/       # Archivos subidos por el maestro
└── templates/
    ├── base.html       # Layout base con navbar
    ├── index.html      # Página principal / oferta de cursos
    ├── login.html      # Inicio de sesión
    ├── register.html   # Registro de alumnos/padres
    ├── dashboard.html  # Panel del alumno
    └── admin.html      # Panel del maestro
```

---

## Flujo de trabajo como maestro

### Crear un curso nuevo:
1. Entra a tu panel → **Cursos** → "Nuevo curso"
2. Llena título, descripción, nivel, duración y precio
3. Activa "Publicar en página principal" para que sea visible
4. Guarda el curso

### Agregar módulos y actividades (vía API):

```bash
# Crear módulo
curl -X POST http://localhost:5000/api/modules \
  -H "Content-Type: application/json" \
  -d '{"course_id": 1, "title": "Módulo 1: Variables", "order": 1}'

# Crear actividad de opción múltiple
curl -X POST http://localhost:5000/api/activities \
  -H "Content-Type: application/json" \
  -d '{
    "module_id": 1,
    "title": "Quiz: Variables",
    "type": "multiple_choice",
    "content": {
      "questions": [
        {
          "id": 1,
          "text": "¿Cómo se declara una variable en Python?",
          "options": ["var x = 5", "x = 5", "int x = 5", "declare x = 5"],
          "correct": "x = 5"
        }
      ]
    }
  }'

# Crear actividad de código (revisada por IA)
curl -X POST http://localhost:5000/api/activities \
  -H "Content-Type: application/json" \
  -d '{
    "module_id": 1,
    "title": "Ejercicio: Función suma",
    "type": "code",
    "content": {
      "instructions": "Crea una función llamada suma() que reciba dos números y retorne su suma.",
      "starter_code": "def suma(a, b):\n    # Tu código aquí\n    pass"
    }
  }'
```

### Subir materiales:
1. Panel → **Materiales**
2. Selecciona el módulo
3. Escribe el título del material
4. Arrastra el archivo o haz clic para seleccionar

### Ver progreso de alumnos:
1. Panel → **Alumnos**
2. Clic en "Ver progreso" junto a cualquier alumno

---

## Despliegue en producción

Para subir a un servidor real (PythonAnywhere, Render, VPS):

1. Cambia `SECRET_KEY` en `app.py` por una cadena aleatoria larga
2. Cambia `debug=True` a `debug=False`
3. Usa una variable de entorno para `ANTHROPIC_API_KEY`
4. Configura un servidor WSGI (gunicorn):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

---

## Tecnologías

- **Backend**: Python + Flask + SQLAlchemy + SQLite
- **Frontend**: HTML5 + CSS3 + JavaScript (Vanilla)
- **IA**: Anthropic Claude (revisión automática de código)
- **Iconos**: Tabler Icons
- **Tipografía**: Syne + DM Sans (Google Fonts)
