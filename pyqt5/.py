class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Recognition Attendance System")
        self.current_class_id = None  # Track current selected class
        
        # Ensure required directories exist
        for directory in [DATASET_DIR, TRAINER_DIR]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        self.db = DatabaseManager()
        self.setup_ui()

    def setup_ui(self):
        # ... (previous code remains the same until camera tab setup)

        # Add class selection to camera tab
        camera_tab = QWidget()
        camera_layout = QVBoxLayout(camera_tab)
        
        # Add class selection at the top of camera tab
        class_select_layout = QHBoxLayout()
        class_select_layout.addWidget(QLabel("Select Class for Attendance:"))
        self.camera_class_select = QComboBox()
        self.update_all_class_lists()  # This will now update camera_class_select too
        class_select_layout.addWidget(self.camera_class_select)
        camera_layout.addLayout(class_select_layout)

        # Add image label for camera feed
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(self.image_label)
        
        # Add status label
        self.status_label = QLabel("Please select a class and start recognition")
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

    def update_all_class_lists(self):
        """Update all class-related combo boxes"""
        try:
            classes = self.db.get_classes()
            
            # Update all class selection comboboxes
            for combo in [self.class_select, self.class_combo, self.camera_class_select]:
                combo.clear()
                combo.addItem("Select Class", None)
                for class_id, class_name in classes:
                    combo.addItem(class_name, class_id)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to fetch classes: {str(e)}")

    def start_recognition(self):
        # Check if a class is selected
        self.current_class_id = self.camera_class_select.currentData()
        if self.current_class_id is None:
            QMessageBox.warning(self, "Warning", "Please select a class before starting recognition")
            return
        
        self.thread.running = True
        self.thread.start()
        self.status_label.setText("Recognition started. Waiting for faces...")

    def stop_recognition(self):
        self.thread.running = False
        self.thread.wait()
        self.current_class_id = None
        self.status_label.setText("Recognition stopped")

    @pyqtSlot(str, float)
    def handle_recognition(self, user_id, confidence):
        try:
            confidence_score = 100 - confidence
            status = 'present' if confidence_score > CONFIDENCE_THRESHOLD else 'unknown'
            
            if status == 'present' and self.current_class_id:
                # Record attendance in database
                self.db.record_attendance(self.current_class_id, int(user_id), status, confidence_score)
                
                # Update status label with recognition result
                self.status_label.setText(f"Attendance recorded for ID: {user_id} (Confidence: {confidence_score:.2f}%)")
                
                # Automatically refresh the attendance table if we're on the attendance tab
                # and the date is today
                if self.date_select.date() == QDate.currentDate():
                    self.view_attendance()
        except Exception as e:
            _logger.error(f"Failed to handle recognition: {str(e)}")
            self.status_label.setText(f"Error recording attendance: {str(e)}")

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
                # Add data to table
                self.attendance_table.setItem(row, 0, QTableWidgetItem(str(name)))
                self.attendance_table.setItem(row, 1, QTableWidgetItem(time.strftime("%H:%M:%S")))
                self.attendance_table.setItem(row, 2, QTableWidgetItem(status))
                self.attendance_table.setItem(row, 3, QTableWidgetItem(f"{confidence:.2f}%"))
                
            # Resize columns to content
            self.attendance_table.resizeColumnsToContents()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load attendance data: {str(e)}")