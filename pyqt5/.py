from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QComboBox, QDateEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QGroupBox, QFormLayout, QTabWidget, QMessageBox
)
from PyQt5.QtGui import QFont, QPalette, QColor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Recognition Attendance System")
        self.resize(900, 600)
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Tabs container
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Camera Feed Tab
        camera_tab = QWidget()
        camera_layout = QVBoxLayout(camera_tab)

        # Add class selection
        class_select_layout = QHBoxLayout()
        class_select_layout.addWidget(QLabel("Select Class for Attendance:"))
        self.camera_class_select = QComboBox()
        class_select_layout.addWidget(self.camera_class_select)
        camera_layout.addLayout(class_select_layout)

        # Image and status label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: #f9f9f9;")
        camera_layout.addWidget(self.image_label)

        self.status_label = QLabel("Waiting for face detection...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; font-style: italic; color: #555;")
        camera_layout.addWidget(self.status_label)

        # Start/Stop buttons
        button_layout = QHBoxLayout()
        start_button = QPushButton("Start Recognition")
        stop_button = QPushButton("Stop Recognition")
        button_layout.addWidget(start_button)
        button_layout.addWidget(stop_button)
        camera_layout.addLayout(button_layout)

        tabs.addTab(camera_tab, "Camera Feed")

        # Class Management Tab
        class_tab = QWidget()
        class_layout = QVBoxLayout(class_tab)

        form_group = QGroupBox("Add New Class")
        form_layout = QFormLayout()

        self.class_name_input = QLineEdit()
        self.teacher_select = QComboBox()
        self.semester_input = QLineEdit()

        form_layout.addRow("Class Name:", self.class_name_input)
        form_layout.addRow("Teacher:", self.teacher_select)
        form_layout.addRow("Semester:", self.semester_input)

        add_class_button = QPushButton("Add Class")
        form_layout.addWidget(add_class_button)

        form_group.setLayout(form_layout)
        class_layout.addWidget(form_group)

        tabs.addTab(class_tab, "Class Management")

        # Attendance Tab
        attendance_tab = QWidget()
        attendance_layout = QVBoxLayout(attendance_tab)

        # Date and class selection
        date_layout = QHBoxLayout()
        self.date_select = QDateEdit()
        self.date_select.setDate(QDate.currentDate())
        date_layout.addWidget(QLabel("Select Date:"))
        date_layout.addWidget(self.date_select)

        self.class_select = QComboBox()
        date_layout.addWidget(QLabel("Select Class:"))
        date_layout.addWidget(self.class_select)

        view_button = QPushButton("View Attendance")
        date_layout.addWidget(view_button)

        attendance_layout.addLayout(date_layout)

        # Add Registration tab
        registration_tab = QWidget()
        reg_layout = QFormLayout(registration_tab)
        
        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems(['student', 'teacher', 'admin'])

        self.update_class_list()
        
        reg_layout.addRow("Tên đầy đủ :", self.name_input)
        reg_layout.addRow("Email:", self.email_input)
        reg_layout.addRow("Vai trờ:", self.role_combo)
        reg_layout.addRow("Lớp:", self.class_combo)

        # Connect role change to toggle class selection visibility
        self.role_combo.currentTextChanged.connect(self.toggle_class_selection)
        
        register_button = QPushButton("Đăng ký và chụp ảnh gương mặt")
        register_button.clicked.connect(self.register_user)
        reg_layout.addWidget(register_button)

        # Initially hide class selection (shown only for students)
        self.toggle_class_selection(self.role_combo.currentText())

        tabs.addTab(registration_tab, "Đăng ký")

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
        self.attendance_table.setHorizontalHeaderLabels(['Student Name', 'Check-in Time', 'Status', 'Confidence'])
        self.attendance_table.setStyleSheet(
            "QTableWidget {"
            "    border: 1px solid #ccc;"
            "    background: #fff;"
            "    gridline-color: #ddd;"
            "}"
        )
        attendance_layout.addWidget(self.attendance_table)

        tabs.addTab(attendance_tab, "View Attendance")

        # Style definitions
        self.apply_styles()

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


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
