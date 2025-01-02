# config/settings.py
import os

# Database settings
DB_CONFIG = {
    "database": "face_recognization",
    "user": "odoo",
    "password": "odoo",
    "host": "localhost",
    "port": "5432"
}

# Constants
CONFIDENCE_THRESHOLD = 20
REQUIRED_FACE_SAMPLES = 30

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset')
TRAINER_DIR = os.path.join(BASE_DIR, 'trainer')
TRAINER_FILE = 'trainer.yml'
CASCADE_FILE = 'haarcascade_frontalface_default.xml'

# User roles
USER_ROLES = ['student', 'teacher', 'admin']
DEFAULT_ROLE = 'student'