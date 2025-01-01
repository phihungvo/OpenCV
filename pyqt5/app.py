import sys
import cv2
import numpy as np
import os
import datetime
import psycopg2
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PIL import Image
import logging
_logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                database="face_recognization",
                user="odoo",
                password="odoo",
                host="localhost",
                port="5432"
            )
            self.cur = self.conn.cursor()
            _logger.info("Database connected successfully")
        except Exception as e:
            _logger.error(f"Failed to connect to database {str(e)}")
            raise e

    def add_user(self, full_name, email, role):
        try:
            _logger.info(f"Attempting to add user: {full_name}, {email}, {role}")
            if role not in ['student', 'teacher', 'admin']:
                raise ValueError("Invalid role. Must be 'student', 'teacher', or 'admin'")
            
            self.cur.execute(
                "INSERT INTO users (full_name, email, role) VALUES (%s, %s, %s) RETURNING user_id",
                (full_name, email, role)
            )
            user_id = self.cur.fetchone()[0]
            self.conn.commit()
            _logger.info(f"User added successfully with ID: {user_id}")
            return user_id
        except psycopg2.errors.UniqueViolation:
            self.conn.rollback()
            _logger.error(f"Email {email} already exists")
            raise ValueError(f"Email {email} already exists")
        except Exception as e:
            self.conn.rollback()
            _logger.error(f"Failed to add user: {str(e)}")
            raise e

    def save_face_data(self, user_id, face_encoding, image_path):
        try:
            _logger.info(f"Saving face data: {user_id}, {image_path}")
            self.cur.execute(
                "INSERT INTO face_data (user_id, face_encoding, image_path) VALUES (%s, %s, %s)",
                (user_id, face_encoding, image_path)
            )
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            _logger.error(f"Failed to save face data: {str(e)}")
            raise e

    def record_attendance(self, class_id, student_id, status, confidence_score):
            try:
                _logger.info(f"Recording attendance: class_id: {class_id}, student_id: {student_id}, status: {status}, + {confidence_score}")
                current_date = datetime.date.today()
                current_time = datetime.datetime.now().time()
                
                # Check if student already has attendance for today in this class
                self.cur.execute("""
                    SELECT attendance_id FROM attendance 
                    WHERE class_id = %s AND student_id = %s AND attendance_date = %s
                """, (class_id, student_id, current_date))
                
                if self.cur.fetchone() is None:
                    # Only insert if no attendance record exists for today
                    self.cur.execute(
                        """INSERT INTO attendance 
                           (class_id, student_id, attendance_date, check_in_time, status, confidence_score) 
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (class_id, student_id, current_date, current_time, status, confidence_score)
                    )
                    self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                _logger.error(f"Failed to record attendence: {str(e)}")
                raise e

    def add_class(self, class_name, teacher_id, semester):
        try:
            _logger.info(f"Adding class: {class_name}, {teacher_id}")
            self.cur.execute(
                "INSERT INTO classes (class_name, teacher_id, semester) VALUES (%s, %s, %s) RETURNING class_id",
                (class_name, teacher_id, semester)
            )
            class_id = self.cur.fetchone()[0]
            self.conn.commit()
            return class_id
        except Exception as e:
            self.conn.rollback()
            _logger.error(f"Failed to add class: {str(e)}")
            raise e  
        
    def get_classes(self):
        try:
            _logger.info("Fetching classes")
            self.cur.execute("SELECT class_id, class_name FROM classes")
            return self.cur.fetchall()
        except Exception as e:
            _logger.error(f"Failed to fetch classes: {str(e)}")
            raise e
        
    def get_teachers(self):
        try:
            self.cur.execute("SELECT user_id, full_name FROM users WHERE role = 'teacher'")
            return self.cur.fetchall()
        except Exception as e:
            raise e
        
    def register_student_to_class(self, class_id, student_id):
        try:
            self.cur.execute(
                "INSERT INTO class_students (class_id, student_id) VALUES (%s, %s)",
                (class_id, student_id)
            )
            self.conn.commit()
        except psycopg2.errors.UniqueViolation:
            self.conn.rollback()
            raise ValueError("Student already registered in this class")
        except Exception as e:
            self.conn.rollback()
            raise e
        
    def get_attendance_by_date(self, class_id, date):
        try:
            _logger.info(f"Fetching attendance for class: {class_id}, date: {date}")
            self.cur.execute("""
                SELECT u.full_name, a.check_in_time, a.status, a.confidence_score
                FROM attendance a
                JOIN users u ON a.student_id = u.user_id
                WHERE a.class_id = %s AND a.attendance_date = %s
                ORDER BY a.check_in_time
            """, (class_id, date))
            return self.cur.fetchall()
        except Exception as e:
            _logger.error(f"Failed to fetch attendance: {str(e)}")
            raise e

class FaceRecognitionThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    recognition_signal = pyqtSignal(str, float)

    def __init__(self):
        super().__init__()
        self.running = True
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        if os.path.exists('trainer/trainer.yml'):
            self.recognizer.read('trainer/trainer.yml')

    def run(self):
        cap = cv2.VideoCapture(0)
        while self.running:
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    id_, confidence = self.recognizer.predict(gray[y:y+h, x:x+w])
                    
                    if confidence < 100:
                        self.recognition_signal.emit(str(id_), confidence)
                    
                self.change_pixmap_signal.emit(frame)
            
        cap.release()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Recognition Attendance System")
        self.db = DatabaseManager()
        self.current_class_id = None
        self.setup_ui()
        
    def setup_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Add Camera Feed tab
        camera_tab = QWidget()
        camera_layout = QVBoxLayout(camera_tab)

        #Add Class Management tab
        class_tab = QWidget()
        class_layout = QVBoxLayout(class_tab)
        
        # Add class form
        form_group = QGroupBox("Add New Class")
        form_layout = QFormLayout()
        
        self.class_name_input = QLineEdit()
        self.teacher_select = QComboBox()
        
        form_layout.addRow("Class Name:", self.class_name_input)
        form_layout.addRow("Teacher:", self.teacher_select)
        
        add_class_button = QPushButton("Add Class")
        add_class_button.clicked.connect(self.add_class)
        form_layout.addRow(add_class_button)
        
        form_group.setLayout(form_layout)
        class_layout.addWidget(form_group)

        # Add semester field in class form
        self.semester_input = QLineEdit()
        form_layout.addRow("Semester:", self.semester_input)

        # Add class selection for attendance
        self.class_select = QComboBox()
        self.update_class_list()
        class_layout.addWidget(QLabel("Select Class for Attendance:"))
        class_layout.addWidget(self.class_select)
        
        tabs.addTab(class_tab, "Class Management")
        
         # Add Attendance View tab
        attendance_tab = QWidget()
        attendance_layout = QVBoxLayout(attendance_tab)
        
        # Date selection
        date_layout = QHBoxLayout()
        self.date_select = QDateEdit()
        self.date_select.setDate(QDate.currentDate())
        date_layout.addWidget(QLabel("Select Date:"))
        date_layout.addWidget(self.date_select)
        
        view_button = QPushButton("View Attendance")
        view_button.clicked.connect(self.view_attendance)
        date_layout.addWidget(view_button)
        
        attendance_layout.addLayout(date_layout)
        
        # Attendance table
        self.attendance_table = QTableWidget()
        self.attendance_table.setColumnCount(4)
        self.attendance_table.setHorizontalHeaderLabels(['Student Name', 'Check-in Time', 'Status', 'Confidence'])
        attendance_layout.addWidget(self.attendance_table)
        
        tabs.addTab(attendance_tab, "View Attendance")

        # Add image label for camera feed
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(self.image_label)
        
        # Add status label
        self.status_label = QLabel("Waiting for face detection...")
        self.status_label.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(self.status_label)
        
        # Add buttons
        button_layout = QHBoxLayout()
        start_button = QPushButton("Start Recognition")
        start_button.clicked.connect(self.start_recognition)
        button_layout.addWidget(start_button)
        
        stop_button = QPushButton("Stop Recognition")
        stop_button.clicked.connect(self.stop_recognition)
        button_layout.addWidget(stop_button)
        
        camera_layout.addLayout(button_layout)
        tabs.addTab(camera_tab, "Camera Feed")
        
        # Add Registration tab
        registration_tab = QWidget()
        reg_layout = QFormLayout(registration_tab)
        
        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems(['student', 'teacher', 'admin'])
        
        reg_layout.addRow("Full Name:", self.name_input)
        reg_layout.addRow("Email:", self.email_input)
        reg_layout.addRow("Role:", self.role_combo)
        
        register_button = QPushButton("Register & Capture Face")
        register_button.clicked.connect(self.register_user)
        reg_layout.addWidget(register_button)
        
        tabs.addTab(registration_tab, "Registration")

        # Update teacher select combobox
        self.teacher_select.clear()
        try:
            teachers = self.db.get_teachers()
            for teacher_id, teacher_name in teachers:
                self.teacher_select.addItem(teacher_name, teacher_id)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to fetch teachers: {str(e)}")
        
        # Set up face recognition thread
        self.thread = FaceRecognitionThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.recognition_signal.connect(self.handle_recognition)


        #Style definition for the application
        button_style = """
        QPushButton {
            min-width: 150px;
            min-height: 35px;
            font-size: 14px;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 8px;
            background-color: #2196F3;
            color: white;
            border: none;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QPushButton:pressed {
            background-color: #1565C0;
        }

        """

        input_style = """
        QLineEdit, QComboBox {
            min-height: 30px;
            padding: 5px;
            border: 1px solid #BDBDBD;
            border-radius: 4px;
            font-size: 13px;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 2px solid #2196F3;
        }
        """

        # Apply styles
        for widget in self.findChildren(QPushButton):
            widget.setStyleSheet(button_style)

        for widget in self.findChildren((QLineEdit, QComboBox)):
            widget.setStyleSheet(input_style)

    def add_class(self):
        class_name = self.class_name_input.text()
        teacher_id = self.teacher_select.currentData()
        semester = self.semester_input.text()
        
        if not all([class_name, teacher_id, semester]):
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return
            
        try:
            self.db.add_class(class_name, teacher_id, semester)
            self.update_class_list()
            QMessageBox.information(self, "Success", "Class added successfully!")
            self.class_name_input.clear()
            self.semester_input.clear()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add class: {str(e)}")

    def update_class_list(self):
        self.class_select.clear()
        classes = self.db.get_classes()
        for class_id, class_name in classes:
            self.class_select.addItem(class_name, class_id)

    def view_attendance(self):
        class_id = self.class_select.currentData()
        selected_date = self.date_select.date().toPyDate()
        
        try:
            attendance_data = self.db.get_attendance_by_date(class_id, selected_date)
            self.attendance_table.setRowCount(len(attendance_data))
            
            for row, (name, time, status, confidence) in enumerate(attendance_data):
                self.attendance_table.setItem(row, 0, QTableWidgetItem(name))
                self.attendance_table.setItem(row, 1, QTableWidgetItem(time.strftime("%H:%M:%S")))
                self.attendance_table.setItem(row, 2, QTableWidgetItem(status))
                self.attendance_table.setItem(row, 3, QTableWidgetItem(f"{confidence:.2f}%"))
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load attendance data: {str(e)}")

    def start_recognition(self):
        self.thread.running = True
        self.thread.start()

    def stop_recognition(self):
        self.thread.running = False
        self.thread.wait()

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        qt_img = self.convert_cv_qt(cv_img)
        self.image_label.setPixmap(qt_img)

    @pyqtSlot(str, float)
    def handle_recognition(self, user_id, confidence):
        confidence_score = 100 - confidence
        status = 'present' if confidence_score > 20 else 'unknown'
        self.status_label.setText(f"Recognized: {user_id} (Confidence: {confidence_score:.2f}%)")
        
        if status == 'present' and self.current_class_id:
            # Record attendance in database
            try:
                self.db.record_attendance(self.current_class_id, int(user_id), status, confidence_score)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to record attendance: {str(e)}")

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(convert_to_Qt_format)

    def register_user(self):
        name = self.name_input.text()
        email = self.email_input.text()
        role = self.role_combo.currentText()
        
        if not all([name, email, role]):
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return
            
        try:
            _logger.info(f"Starting user registration for {name}")
            # Add user to database
            user_id = self.db.add_user(name, email, role)

            if user_id:
                reply = QMessageBox.question(self, "Success", 
                    "User registered successfully. Do you want to capture face data now?",
                    QMessageBox.Yes | QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    # Start face capture
                    self.capture_faces(user_id)
                else:
                    self.name_input.clear()
                    self.email_input.clear()
            
        except ValueError as ve:
            QMessageBox.warning(self, "Error", str(ve))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Registration failed: {str(e)}")

    def capture_faces(self, user_id):
        face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        cam = cv2.VideoCapture(0)
        count = 0
        
        while count < 30:
            ret, img = cam.read()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(gray, 1.3, 5)
            
            for (x, y, w, h) in faces:
                count += 1
                # Save face image
                image_path = f"dataset/User.{user_id}.{count}.jpg"
                cv2.imwrite(image_path, gray[y:y+h, x:x+w])
                
                # Save face data to database
                face_encoding = gray[y:y+h, x:x+w].tobytes().hex()
                self.db.save_face_data(user_id, face_encoding, image_path)
                
            if count >= 30:
                break
                
        cam.release()
        self.train_model()

    def train_model(self):
        path = 'dataset'
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

        faces = []
        ids = []
        
        for image_path in os.listdir(path):
            if image_path.startswith("User"):
                img = Image.open(os.path.join(path, image_path)).convert('L')
                img_numpy = np.array(img, 'uint8')
                id_ = int(image_path.split(".")[1])
                faces.append(img_numpy)
                ids.append(id_)

        recognizer.train(faces, np.array(ids))
        recognizer.write('trainer/trainer.yml')
        QMessageBox.information(self, "Success", "Registration complete and model trained!")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setGeometry(100, 100, 800, 600)
    window.show()
    sys.exit(app.exec_())