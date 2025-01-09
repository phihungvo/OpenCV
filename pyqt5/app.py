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

# Constants
CONFIDENCE_THRESHOLD = 50
REQUIRED_FACE_SAMPLES = 100 #30
DATASET_DIR = 'dataset'
TRAINER_DIR = 'trainer'
TRAINER_FILE = 'trainer.yml'

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
        
    def close(self):
        """Safely close database connection and cursor"""
        try:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()
            _logger.info("Database connection closed successfully")
        except Exception as e:
            _logger.error(f"Error closing database connection: {str(e)}")

    def add_user(self, full_name, email, role, class_id = None):
        try:
            _logger.info(f"Attempting to add user: {full_name}, {email}, {role}")
            if role not in ['Học sinh', 'Giáo viên', 'Quản trị viên']:
                raise ValueError("Invalid role. Must be 'student', 'Giáo viên', or 'Quản trị viên'")
            
            self.cur.execute(
                "INSERT INTO users (full_name, email, role) VALUES (%s, %s, %s) RETURNING user_id",
                (full_name, email, role)
            )
            user_id = self.cur.fetchone()[0]

            # If user is a student and class_id is provided, register them to the class
            if role == 'Học sinh' and class_id is not None:
                self.register_student_to_class(class_id, user_id)

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
        
    def is_student_registered(self, class_id, student_id):
        """Check if a student is registered for a specific class"""
        try:
            self.cur.execute("""
                SELECT 1 FROM class_students 
                WHERE class_id = %s AND student_id = %s
            """, (class_id, student_id))
            return bool(self.cur.fetchone())
        except Exception as e:
            _logger.error(f"Failed to check student registration: {str(e)}")
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
                # Đảm bảo confidence_score nằm trong khoảng hợp lệ
                confidence_score = max(0, min(100, confidence_score))  # Giới hạn giá trị từ 0 đến 100

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
            self.cur.execute("SELECT user_id, full_name FROM users WHERE role = 'Giáo viên'")
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
            raise ValueError("Học sinh đã được đăng ký trong lớp này!")
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
            _logger.error(f"Không thể lấy dữ liệu điểm danh: {str(e)}")
            raise e

    def get_students_by_class(self, class_id):
        try:
            self.cur.execute("""
                SELECT u.user_id, u.full_name, u.email,
                    COALESCE(
                        (SELECT status 
                        FROM attendance 
                        WHERE student_id = u.user_id 
                        AND class_id = %s 
                        AND attendance_date = CURRENT_DATE
                        ORDER BY check_in_time DESC 
                        LIMIT 1),
                        'Vắng'
                    ) as attendance_status
                FROM users u
                JOIN class_students cs ON u.user_id = cs.student_id
                WHERE cs.class_id = %s
                ORDER BY u.full_name
            """, (class_id, class_id))
            return self.cur.fetchall()
        except Exception as e:
            _logger.error(f"Failed to fetch students: {str(e)}")
            raise e
        
class FaceRecognitionThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    recognition_signal = pyqtSignal(str, float)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        if os.path.exists('trainer/trainer.yml'):
            self.recognizer.read('trainer/trainer.yml')

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.error_signal.emit("Lỗi khi mở camera!0")
            return
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                self.error_signal.emit("Không thể truy cập camera")
                break

            try:
                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    id_, confidence = self.recognizer.predict(gray[y:y+h, x:x+w])
                    
                    if confidence < 100:
                        self.recognition_signal.emit(str(id_), confidence)
                    
                self.change_pixmap_signal.emit(frame)
            except Exception  as e:
                self.error_signal.emit(f"Lỗi xử lý khung hình: {str(e)}")
                break
            
        cap.release()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hệ thống điểm danh nhận diện khuôn mặt")
        self.current_class_id = None

        # Ensure required directories exist
        for directory in [DATASET_DIR, TRAINER_DIR]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        self.db = DatabaseManager()
        self.setup_ui()

    def apply_styles(self):
        # Button style
        button_style = """
        QPushButton {
            min-width: 120px;
            min-height: 35px;
            font-size: 14px;
            font-weight: bold;
            border-radius: 8px;
            background-color: #4CAF50;
            color: white;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #388E3C;
        }
        """
        for widget in self.findChildren(QPushButton):
            widget.setStyleSheet(button_style)

        # Input fields
        input_style = """
        QLineEdit, QComboBox, QDateEdit {
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 5px;
            font-size: 14px;
        }
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
            border: 2px solid #4CAF50;
        }
        """
        for widget in self.findChildren((QLineEdit, QComboBox, QDateEdit)):
            widget.setStyleSheet(input_style)

        # GroupBox
        group_style = """
        QGroupBox {
            font-size: 14px;
            font-weight: bold;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
        }
        """
        for widget in self.findChildren(QGroupBox):
            widget.setStyleSheet(group_style)
     
    def setup_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Initialize all combo boxes first # Initialize here
        self.class_select = QComboBox()
        self.class_combo = QComboBox()
        self.camera_class_select = QComboBox()
        self.student_list_class_select = QComboBox()
        self.manual_class_select = QComboBox()
        
        # Add Camera Feed tab
        camera_tab = QWidget()
        camera_layout = QVBoxLayout(camera_tab)

        # Add class selection at the top of camera tab
        class_select_layout = QHBoxLayout()
        class_select_layout.addWidget(QLabel("Chọn Lớp để Điểm Danh:"))
        self.update_all_class_lists()  # This will now update camera_class_select too
        class_select_layout.addWidget(self.camera_class_select)
        camera_layout.addLayout(class_select_layout)

        # Add Class Management tab
        class_tab = QWidget()
        class_layout = QVBoxLayout(class_tab)
        
        # Add class form
        form_group = QGroupBox("Thêm lớp mới")
        form_layout = QFormLayout()
        
        self.class_name_input = QLineEdit()
        self.teacher_select = QComboBox()
        self.semester_input = QLineEdit()
        
        form_layout.addRow("Tên lớp:", self.class_name_input)
        form_layout.addRow("Giáo viên:", self.teacher_select)
        form_layout.addRow("Học kỳ:", self.semester_input)
        
        add_class_button = QPushButton("Thêm lớp")
        add_class_button.clicked.connect(self.add_class)
        form_layout.addRow(add_class_button)
        
        form_group.setLayout(form_layout)
        class_layout.addWidget(form_group)

        # Initialize class_select here before using it
        self.update_class_combo()  # This will populate the class_select combobox
        
        tabs.addTab(class_tab, "Quản lý lớp")

        # Add image label for camera feed
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(self.image_label)
        
        # Add status label
        self.status_label = QLabel("Đang chờ nhận diện khuôn mặt...")
        self.status_label.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(self.status_label)
        
        # Add buttons
        button_layout = QHBoxLayout()
        start_button = QPushButton("Bắt Đầu Điểm Danh")
        start_button.clicked.connect(self.start_recognition)
        button_layout.addWidget(start_button)
        
        stop_button = QPushButton("Dừng Điểm Danh")
        stop_button.clicked.connect(self.stop_recognition)
        button_layout.addWidget(stop_button)
        
        camera_layout.addLayout(button_layout)
        tabs.addTab(camera_tab, "Điểm danh bằng gương mặt")
        
        # Add Registration tab
        registration_tab = QWidget()
        reg_layout = QFormLayout(registration_tab)
        
        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems(['Học sinh', 'Giáo viên', 'Quản trị viên'])

        self.update_class_list()
        
        reg_layout.addRow("Tên đầy đủ :", self.name_input)
        reg_layout.addRow("Email:", self.email_input)
        reg_layout.addRow("Vai trò:", self.role_combo)
        reg_layout.addRow("Lớp:", self.class_combo)

        # Connect role change to toggle class selection visibility
        self.role_combo.currentTextChanged.connect(self.toggle_class_selection)
        
        register_button = QPushButton("Đăng ký và chụp ảnh gương mặt")
        register_button.clicked.connect(self.register_user)
        reg_layout.addWidget(register_button)

        # Initially hide class selection (shown only for students)
        self.toggle_class_selection(self.role_combo.currentText())

        tabs.addTab(registration_tab, "Đăng ký")

        # Add Student List tab
        student_list_tab = QWidget()
        student_list_layout = QVBoxLayout(student_list_tab)
        
        # Add class selection for student list
        student_list_header = QHBoxLayout()
        student_list_header.addWidget(QLabel("Chọn lớp:"))
        self.update_all_class_lists()  # This will now update student_list_class_select too
        student_list_header.addWidget(self.student_list_class_select)
        
        view_students_button = QPushButton("Xem danh sách học sinh")
        view_students_button.clicked.connect(self.view_students)
        student_list_header.addWidget(view_students_button)
        
        student_list_layout.addLayout(student_list_header)      
                
        # Add student table with improved styling
        self.student_table = QTableWidget()
        self.student_table.setColumnCount(4)
        self.student_table.setHorizontalHeaderLabels(['Mã sinh viên', 'Tên đầy đủ', 'Email', 'Trạng thái điểm danh'])

        # Set table styling
        self.student_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                background-color: white;
                gridline-color: #ddd;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ddd;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 5px;
                border: none;
                border-bottom: 2px solid #ddd;
                font-weight: bold;
            }
        """)

        # Set column widths
        self.student_table.setColumnWidth(0, 100)  
        self.student_table.setColumnWidth(1, 150)  
        self.student_table.setColumnWidth(2, 200)  
        self.student_table.setColumnWidth(3, 150) 

        # Enable sorting
        self.student_table.setSortingEnabled(True)

        # Adjust size and scrolling behavior
        self.student_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.student_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        student_list_layout.addWidget(self.student_table)
        
        tabs.addTab(student_list_tab, "Danh sách học sinh")

        # Add Manual Attendance tab
        manual_attendance_tab = QWidget()
        manual_layout = QVBoxLayout(manual_attendance_tab)
        
        # Add class selection and date selection
        top_layout = QHBoxLayout()
        
        # Class selection
        class_select_group = QGroupBox("Chọn lớp")
        class_select_layout = QVBoxLayout()
        self.update_all_class_lists()  # This will now update manual_class_select too
        class_select_layout.addWidget(self.manual_class_select)
        class_select_group.setLayout(class_select_layout)
        top_layout.addWidget(class_select_group)
        
        # Date selection
        date_select_group = QGroupBox("Chọn ngày")
        date_select_layout = QVBoxLayout()
        self.date_select = QDateEdit()
        self.date_select.setDate(QDate.currentDate())
        self.date_select.setDisplayFormat("dd/MM/yyyy")
        self.date_select.setCalendarPopup(True)
        date_select_layout.addWidget(self.date_select)
        date_select_group.setLayout(date_select_layout)
        top_layout.addWidget(date_select_group)
        
        manual_layout.addLayout(top_layout)
        
        # Add student table for manual attendance
        self.manual_attendance_table = QTableWidget()
        self.manual_attendance_table.setColumnCount(5)
        self.manual_attendance_table.setHorizontalHeaderLabels([
            'Mã SV', 'Họ và tên', 'Email', 'Trạng thái', 'Ghi chú'
        ])
        
        # Set table styling
        self.manual_attendance_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                background-color: white;
                gridline-color: #ddd;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ddd;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 5px;
                border: none;
                border-bottom: 2px solid #ddd;
                font-weight: bold;
            }
        """)
        
        # Set column widths
        self.manual_attendance_table.setColumnWidth(0, 100)
        self.manual_attendance_table.setColumnWidth(1, 200)
        self.manual_attendance_table.setColumnWidth(2, 200)
        self.manual_attendance_table.setColumnWidth(3, 120)
        self.manual_attendance_table.setColumnWidth(4, 150)
        
        manual_layout.addWidget(self.manual_attendance_table)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        load_students_btn = QPushButton("Tải danh sách")
        load_students_btn.clicked.connect(self.load_students_for_manual_attendance)
        button_layout.addWidget(load_students_btn)
        
        save_attendance_btn = QPushButton("Lưu điểm danh")
        save_attendance_btn.clicked.connect(self.save_manual_attendance)
        button_layout.addWidget(save_attendance_btn)
        
        manual_layout.addLayout(button_layout)
        
        tabs.addTab(manual_attendance_tab, "Điểm danh thủ công")

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

        # Attendance table
        self.attendance_table = QTableWidget()
        self.attendance_table.setColumnCount(4)
        self.attendance_table.setHorizontalHeaderLabels(['Tên học sinh', 'Check-in', 'Trạng thái', 'Độ chính xác'])
        self.attendance_table.setStyleSheet(
            "QTableWidget {"
            "    border: 1px solid #ccc;"
            "    background: #fff;"
            "    gridline-color: #ddd;"
            "}"
        )

        self.apply_styles()

    def add_class(self):
        class_name = self.class_name_input.text()
        teacher_id = self.teacher_select.currentData()
        semester = self.semester_input.text()
        
        if not all([class_name, teacher_id, semester]):
            QMessageBox.warning(self, "Error", "Hãy điền vào đầy đủ")
            return
            
        try:
            self.db.add_class(class_name, teacher_id, semester)
            self.update_all_class_lists()
            QMessageBox.information(self, "Success", "Lớp đã thêm thành công!")
            self.class_name_input.clear()
            self.semester_input.clear()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add class: {str(e)}")

    def update_class_list(self):
        self.class_select.clear()
        self.update_all_class_lists()
        classes = self.db.get_classes()
        for class_id, class_name in classes:
            self.class_select.addItem(class_name, class_id)

    def update_all_class_lists(self):
        """Update all class-related combo boxes"""
        try:
            classes = self.db.get_classes()

            # Update all class selection comboboxes
            for combo in [self.class_select, self.class_combo, self.camera_class_select, 
                        self.student_list_class_select, self.manual_class_select]:  # Added student_list_class_select
                combo.clear()
                combo.addItem("Chọn lớp", None)
                for class_id, class_name in classes:
                    combo.addItem(class_name, class_id)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to fetch classes: {str(e)}")

    def update_class_combo(self):
        self.class_select.clear()
        try: 
            self.update_all_class_lists()
            classes = self.db.get_classes()
            self.class_select.addItem("Chọn lớp", None)
            for class_id, class_name in classes:
                self.class_select.addItem(class_name, class_id)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to fetch classes: {str(e)}")

    def toggle_class_selection(self, role):
        # Show class selection only for students
        self.class_combo.setVisible(role == 'Học sinh')
        if role != 'Học sinh':
            self.class_combo.setCurrentIndex(0)

    # Fix the view_attendance method:
    def view_attendance(self):
        class_id = self.class_select.currentData()
        selected_date = self.date_select.date().toPyDate()

        if class_id is None:
            QMessageBox.warning(self, "Warning", "Please select a class to view attendance")
            return
        
        try:
            attendance_data = self.db.get_attendance_by_date(class_id, selected_date)

            # Clear and set up the table
            self.attendance_table.setRowCount(0)  # Clear existing rows
            self.attendance_table.setRowCount(len(attendance_data))
            
            for row, (name, time, status, confidence) in enumerate(attendance_data):
                self.attendance_table.setItem(row, 0, QTableWidgetItem(str(name)))
                self.attendance_table.setItem(row, 1, QTableWidgetItem(time.strftime("%H:%M:%S")))
                self.attendance_table.setItem(row, 2, QTableWidgetItem(status))
                self.attendance_table.setItem(row, 3, QTableWidgetItem(f"{confidence:.2f}%"))
                
            # Resize columns to content
            self.attendance_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load attendance data: {str(e)}")

    # Modify the view_students method to handle alignment:
    def view_students(self):
        class_id = self.student_list_class_select.currentData()
        if class_id is None:
            QMessageBox.warning(self, "Warning", "Vui lòng chọn một lớp để xem danh sách học sinh")
            return
        
        try:
            students = self.db.get_students_by_class(class_id)
            
            self.student_table.setRowCount(0)
            self.student_table.setRowCount(len(students))
            
            for row, (user_id, name, email, status) in enumerate(students):
                # Create items with alignment
                id_item = QTableWidgetItem(str(user_id))
                id_item.setTextAlignment(Qt.AlignCenter)
                
                name_item = QTableWidgetItem(name)
                name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                
                email_item = QTableWidgetItem(email)
                email_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                
                # Set items in table
                self.student_table.setItem(row, 0, id_item)
                self.student_table.setItem(row, 1, name_item)
                self.student_table.setItem(row, 2, email_item)
                self.student_table.setItem(row, 3, status_item)
                
                # Set row height
                self.student_table.setRowHeight(row, 30)
            
            # Make table rows fill the available height
            header_height = self.student_table.horizontalHeader().height()
            available_height = self.student_table.height() - header_height
            if len(students) > 0:
                # row_height = max(30, available_height / len(students))
                row_height = int(max(30, available_height / len(students)))
                for row in range(len(students)):
                    self.student_table.setRowHeight(row, row_height)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load student data: {str(e)}")

    def load_students_for_manual_attendance(self):
        """Load students for manual attendance marking with consistent status options"""
        class_id = self.manual_class_select.currentData()
        if not class_id:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một lớp")
            return
            
        try:
            # Fetch students
            selected_date = self.date_select.date().toPyDate()
            self.db.cur.execute("""
                SELECT u.user_id, u.full_name, u.email,
                    COALESCE(
                        (SELECT status 
                        FROM attendance 
                        WHERE student_id = u.user_id 
                        AND class_id = %s 
                        AND attendance_date = %s
                        ORDER BY check_in_time DESC 
                        LIMIT 1),
                        'Vắng'
                    ) as attendance_status,
                    COALESCE(
                        (SELECT note 
                        FROM attendance 
                        WHERE student_id = u.user_id 
                        AND class_id = %s 
                        AND attendance_date = %s
                        ORDER BY check_in_time DESC 
                        LIMIT 1),
                        ''
                    ) as note
                FROM users u
                JOIN class_students cs ON u.user_id = cs.student_id
                WHERE cs.class_id = %s
                ORDER BY u.full_name
            """, (class_id, selected_date, class_id, selected_date, class_id))
            
            students = self.db.cur.fetchall()
            
            # Clear and set up table
            self.manual_attendance_table.setRowCount(len(students))
            
            # Define consistent status options
            status_options = ['Có mặt', 'Vắng', 'Đi muộn', 'Có phép']
            
            for row, (user_id, name, email, status, note) in enumerate(students):
                # User ID
                id_item = QTableWidgetItem(str(user_id))
                id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
                self.manual_attendance_table.setItem(row, 0, id_item)
                
                # Name
                name_item = QTableWidgetItem(name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.manual_attendance_table.setItem(row, 1, name_item)
                
                # Email
                email_item = QTableWidgetItem(email)
                email_item.setFlags(email_item.flags() & ~Qt.ItemIsEditable)
                self.manual_attendance_table.setItem(row, 2, email_item)
                
                # Status ComboBox
                status_combo = QComboBox()
                status_combo.addItems(status_options)
                current_status = status if status in status_options else 'Vắng'
                status_combo.setCurrentText(current_status)
                self.manual_attendance_table.setCellWidget(row, 3, status_combo)
                
                # Note
                note_item = QTableWidgetItem(note)
                self.manual_attendance_table.setItem(row, 4, note_item)
                
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể tải danh sách học sinh: {str(e)}")

    def save_manual_attendance(self):
        """Save manual attendance records and update student list view"""
        class_id = self.manual_class_select.currentData()
        selected_date = self.date_select.date().toPyDate()
        
        if not class_id:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một lớp")
            return
            
        try:
            # Begin transaction
            self.db.cur.execute("BEGIN")
            
            # Delete existing attendance records for this class and date
            self.db.cur.execute("""
                DELETE FROM attendance 
                WHERE class_id = %s AND attendance_date = %s
            """, (class_id, selected_date))
            
            # Insert new attendance records
            current_time = datetime.datetime.now().time()
            for row in range(self.manual_attendance_table.rowCount()):
                student_id = int(self.manual_attendance_table.item(row, 0).text())
                status = self.manual_attendance_table.cellWidget(row, 3).currentText()
                note = self.manual_attendance_table.item(row, 4).text()
                
                self.db.cur.execute("""
                    INSERT INTO attendance (class_id, student_id, attendance_date, status, note, check_in_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (class_id, student_id, selected_date, status, note, current_time))
            
            # Commit transaction
            self.db.cur.execute("COMMIT")
            
            QMessageBox.information(self, "Thành công", "Đã lưu điểm danh thành công!")
            
            # Refresh both the manual attendance view and student list
            self.load_students_for_manual_attendance()
            
            # Update student list if we're viewing the same class
            if self.student_list_class_select.currentData() == class_id:
                self.view_students()
                
        except Exception as e:
            self.db.cur.execute("ROLLBACK")
            QMessageBox.warning(self, "Lỗi", f"Không thể lưu điểm danh: {str(e)}")

    def start_recognition(self):
        """
        Bắt đầu quá trình nhận diện khuôn mặt.
        Kiểm tra lớp học được chọn và khởi động luồng xử lý nhận diện.
        """
        try:
            # Kiểm tra nếu người dùng đã chọn lớp học
            self.current_class_id = self.camera_class_select.currentData()
            if self.current_class_id is None:
                QMessageBox.warning(self, "Warning", "Please select a class before starting recognition")
                return

            # Khởi động nhận diện
            self.thread.running = True
            self.thread.start()
            self.status_label.setText("Recognition started. Waiting for faces...")
            _logger.info(f"Recognition started for class ID: {self.current_class_id}")

        except Exception as e:
            _logger.error(f"Failed to start recognition: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred while starting recognition: {str(e)}")

    def stop_recognition(self):
        self.thread.running = False
        self.thread.wait()
        self.current_class_id = None
        self.status_label.setText("Recognition stopped")

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        qt_img = self.convert_cv_qt(cv_img)
        self.image_label.setPixmap(qt_img)

    # Update the handle_recognition method to show success message:
    @pyqtSlot(str, float)
    def handle_recognition(self, user_id, confidence):
        # Convert OpenCV confidence (lower is better) to percentage (higher is better)
        confidence_score = max(0, min(100, 100 - confidence))
        status = 'Có mặt' if confidence_score > CONFIDENCE_THRESHOLD else 'Vắng'
        
        if status == 'Có mặt' and self.current_class_id:
            try:
                # Kiểm tra học sinh có đăng ký lớp học không
                if not self.db.is_student_registered(self.current_class_id, int(user_id)):
                    self.status_label.setText(f"Student {user_id} not registered for this class")
                    return
                
                # Kiểm tra đã điểm danh chưa
                self.db.cur.execute("""
                    SELECT COUNT(*) 
                    FROM attendance 
                    WHERE class_id = %s AND student_id = %s AND attendance_date = CURRENT_DATE
                """, (self.current_class_id, int(user_id)))
                already_recorded = self.db.cur.fetchone()[0]

                # Lấy tên học sinh
                self.db.cur.execute("SELECT full_name FROM users WHERE user_id = %s", (int(user_id),))
                student_name = self.db.cur.fetchone()[0]

                if not already_recorded:
                    # Ghi nhận điểm danh
                    self.db.record_attendance(self.current_class_id, int(user_id), status, confidence_score)
                    
                    if student_name:
                        QMessageBox.information(self, "Điểm danh thành công", 
                                            f"Điểm danh đã được ghi nhận thành công cho {student_name}")
                        
                        # Cập nhật danh sách học sinh ngay lập tức
                        if self.student_list_class_select.currentData() == self.current_class_id:
                            self.view_students()  # Refresh student list
                    else:
                        QMessageBox.warning(self, "Error", "Không thể lấy tên học sinh.")
                else:
                    self.status_label.setText(f"Điểm danh đã được ghi nhận cho: {student_name}")

                # Cập nhật nhãn trạng thái
                self.status_label.setText(f"Điểm danh thành công: {student_name} (Độ chính xác: {confidence_score:.2f}%)")

            except Exception as e:
                _logger.error(f"Failed to handle recognition: {str(e)}")
                self.status_label.setText(f"Lỗi ghi nhận điểm danh: {str(e)}")

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
        class_id = self.class_combo.currentData() if role == 'Học sinh' else None
        
        if not all([name, email, role]):
            QMessageBox.warning(self, "Error", "Please fill required fields")
            return
            
        if role == 'Học sinh' and class_id is None:
            QMessageBox.warning(self, "Error", "Vui lòng chọn lớp cho học sinh")
            return
        
        try:
            _logger.info(f"Starting user registration for {name}")
            # Add user to database
            user_id = self.db.add_user(name, email, role, class_id)

            if user_id:
                reply = QMessageBox.question(self, "Success", 
                    "Người dùng đã đăng ký thành công. Bạn có muốn chụp dữ liệu khuôn mặt ngay bây giờ không?",
                    QMessageBox.Yes | QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    # Start face capture
                    self.capture_faces(user_id)

                # Cập nhật danh sách học sinh ngay lập tức nếu role là học sinh
                if role == 'Học sinh':
                    selected_class = self.student_list_class_select.currentData()
                    if selected_class == class_id:
                        self.view_students()  # Refresh student list if we're viewing the same class
               
                self.clear_registration_fields()
            
        except ValueError as ve:
            QMessageBox.warning(self, "Error", str(ve))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Registration failed: {str(e)}")

    def clear_registration_fields(self):
        self.name_input.clear()
        self.email_input.clear()
        self.class_combo.setCurrentIndex(0)

    def capture_faces(self, user_id):
        _logger.info(f"Starting face capture for user: {user_id}")
        face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        cam = None
        try:
            cam = cv2.VideoCapture(0)
            if not cam.isOpened():
                raise Exception("Failed to open camera")
            
            count = 0
            user_path = os.path.join(DATASET_DIR, f"User_{user_id}")
            os.makedirs(user_path, exist_ok=True)
            
            while count < REQUIRED_FACE_SAMPLES :
                ret, img = cam.read()
                if not ret:
                    raise Exception("Failed to read from camera")
                
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = face_detector.detectMultiScale(gray, 1.3, 5)
                
                for (x, y, w, h) in faces:
                    count += 1
                    # Save face image
                    # image_path = f"dataset/User.{user_id}.{count}.jpg"
                    image_path = os.path.join(user_path, f"{count}.jpg")
                    face_img = gray[y:y+h, x:x+w]
                    cv2.imwrite(image_path, face_img)
                    
                    # Save face data to database
                    face_encoding = face_img.tobytes().hex()
                    self.db.save_face_data(user_id, face_encoding, image_path)

                    # Show progress
                    self.status_label.setText(f"Capturing face {count}/{REQUIRED_FACE_SAMPLES}")
                    QApplication.processEvents()
                    
                if count >= REQUIRED_FACE_SAMPLES:
                    break
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to capture face data: {str(e)}")
            raise e
        finally:
            if cam is not None:
                cam.release()
                self.train_model() # Always train model after capturing faces

    def train_model(self):
        try:
            _logger.info("Training model....")
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

            faces = []
            ids = []

            # Duyệt qua các thư mục user trong DATASET_DIR
            for user_dir in os.listdir(DATASET_DIR):
                if not user_dir.startswith("User_"):
                    continue
                    
                try:
                    # Lấy user_id từ tên thư mục
                    user_id = int(user_dir.split("_")[1])
                    user_path = os.path.join(DATASET_DIR, user_dir)
                    
                    # Duyệt qua các ảnh trong thư mục user
                    for img_file in os.listdir(user_path):
                        img_path = os.path.join(user_path, img_file)
                        img = Image.open(img_path).convert('L')
                        img_numpy = np.array(img, 'uint8')
                        
                        faces.append(img_numpy)
                        ids.append(user_id)
                        
                except Exception as e:
                    _logger.warning(f"Error processing user directory {user_dir}: {str(e)}")
                    continue

            if not faces:
                raise ValueError("No valid face images found")

            recognizer.train(faces, np.array(ids))
            trainer_path = os.path.join(TRAINER_DIR, TRAINER_FILE)
            recognizer.write(trainer_path)
            QMessageBox.information(self, "Success", "Đăng ký hoàn tất !!!")
            
        except Exception as e:
            _logger.error(f"Error training model: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to train model: {str(e)}")

    def closeEvent(self, event):
        """Handle application shutdown"""
        try:
            self.stop_recognition()
            if hasattr(self, 'db'):
                self.db.close()
        except Exception as e:
            _logger.error(f"Error during shutdown: {str(e)}")
        finally:
            super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setGeometry(100, 100, 900, 600)
    window.show()
    sys.exit(app.exec_())