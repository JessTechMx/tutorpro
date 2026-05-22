"""
Script de configuración inicial.
Ejecutar UNA sola vez después de instalar dependencias.
"""
import os, sys

# Agregar el directorio al path
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, seed_data

print("🔧 Inicializando TutorPro...")
with app.app_context():
    db.create_all()
    print("✅ Base de datos creada.")
    seed_data()
    print("✅ Datos iniciales cargados.")
print("\n✨ Listo. Ejecuta: python app.py")
print("🌐 Abre: http://localhost:5000")
print("👤 Admin: admin@tutorpro.com / admin123")
