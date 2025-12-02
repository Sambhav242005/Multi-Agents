"""
Product Conversation Manager
A PyQt5-based GUI application for processing product information through conversation workflows.
"""

import sys
import json
import os
import webbrowser
from datetime import datetime
from typing import Dict, Any, Optional
from queue import Queue

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
                             QProgressBar, QMessageBox, QTabWidget, QGroupBox, QScrollArea,
                             QInputDialog, QCheckBox, QSplitter, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QImage, QPalette, QColor
import pygame

# Import your existing classes
from src.ui.controller import ProductConversationManager


class WorkerThread(QThread):
    """
    Worker thread to run the workflow without freezing the UI.
    Handles background processing and communicates with the UI via signals.
    """
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    user_input_required = pyqtSignal(str)
    clarifier_question = pyqtSignal(str)

    def __init__(self, manager: ProductConversationManager, generate_audio: bool = True):
        super().__init__()
        self.manager = manager
        self.generate_audio = generate_audio
        self.answer_queue = Queue()
        self.clarifier_response_queue = Queue()

    def run(self):
        """Execute the workflow in the background thread."""
        try:
            self.progress.emit("Starting workflow...")

            # Define callbacks for user interactions
            def user_input_callback(question):
                self.user_input_required.emit(question)
                return self.answer_queue.get()

            def clarifier_callback(question):
                self.clarifier_question.emit(question)
                return self.clarifier_response_queue.get()

            def progress_callback(message):
                self.progress.emit(message)

            # Run the workflow with callbacks
            result = self.manager.run_full_workflow(
                user_input_callback=user_input_callback,
                clarifier_callback=clarifier_callback,
                generate_audio=self.generate_audio,
                progress_callback=progress_callback
            )

            self.finished.emit(result)

        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
            self.finished.emit({"error": str(e)})


class StyledWidget(QWidget):
    """Base widget with consistent styling."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                color: #333333;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #e1e1e1;
                border: 1px solid #cccccc;
                padding: 6px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom-color: white;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4a86e8;
            }
        """)


class ProductConversationGUI(QMainWindow):
    """
    Main application window for the Product Conversation Manager.
    Provides a user interface for inputting product information and viewing results.
    """

    def __init__(self):
        super().__init__()
        self.manager = ProductConversationManager()
        self.worker = None
        self.tab_switch_timer = QTimer(self)
        self.tab_switch_timer.timeout.connect(self.switch_to_summary_tab)
        self.initUI()

    def initUI(self):
        """Initialize the user interface with a modern, clean design."""
        self.setWindowTitle("Product Conversation Manager")
        self.setGeometry(100, 100, 1200, 900)
        self.setMinimumSize(800, 600)

        # Set application icon if available
        # self.setWindowIcon(QIcon("app_icon.png"))

        # Create main widget and layout
        main_widget = StyledWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header with title
        header_layout = QHBoxLayout()
        title_label = QLabel("Product Conversation Manager")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        header_layout.addWidget(title_label)
        main_layout.addLayout(header_layout)

        # Create a splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)

        # Input section
        input_widget = StyledWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(10, 10, 10, 10)

        input_group = QGroupBox("Input Options")
        input_group_layout = QGridLayout()
        input_group_layout.setSpacing(10)

        # Text input
        input_group_layout.addWidget(QLabel("Text Input:"), 0, 0)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter product description or requirements...")
        self.text_input.setMinimumHeight(80)
        input_group_layout.addWidget(self.text_input, 0, 1)

        # Image input
        input_group_layout.addWidget(QLabel("Image Path:"), 1, 0)
        image_path_layout = QHBoxLayout()
        self.image_path = QLineEdit()
        self.image_path.setPlaceholderText("Path to image file...")
        image_path_layout.addWidget(self.image_path)
        self.image_browse_btn = QPushButton("Browse")
        self.image_browse_btn.clicked.connect(self.browse_image)
        self.image_browse_btn.setMaximumWidth(80)
        image_path_layout.addWidget(self.image_browse_btn)
        input_group_layout.addLayout(image_path_layout, 1, 1)

        # Audio input
        input_group_layout.addWidget(QLabel("Audio Input:"), 2, 0)
        audio_path_layout = QHBoxLayout()
        self.audio_path = QLineEdit()
        self.audio_path.setPlaceholderText("Path to audio file or 'RECORD' to record new audio")
        audio_path_layout.addWidget(self.audio_path)
        self.audio_browse_btn = QPushButton("Browse")
        self.audio_browse_btn.clicked.connect(self.browse_audio)
        self.audio_browse_btn.setMaximumWidth(80)
        audio_path_layout.addWidget(self.audio_browse_btn)
        input_group_layout.addLayout(audio_path_layout, 2, 1)

        # Audio generation option
        self.generate_audio_checkbox = QCheckBox("Generate Audio Summary")
        self.generate_audio_checkbox.setChecked(True)
        self.generate_audio_checkbox.setToolTip("Generate and play an audio summary of the product")
        input_group_layout.addWidget(self.generate_audio_checkbox, 3, 1)

        input_group.setLayout(input_group_layout)
        input_layout.addWidget(input_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.run_btn = QPushButton("Run Workflow")
        self.run_btn.clicked.connect(self.run_workflow)
        self.run_btn.setStyleSheet("QPushButton { background-color: #27ae60; }")
        self.run_btn.setMinimumHeight(36)
        button_layout.addWidget(self.run_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_inputs)
        self.reset_btn.setStyleSheet("QPushButton { background-color: #e74c3c; }")
        self.reset_btn.setMinimumHeight(36)
        button_layout.addWidget(self.reset_btn)

        input_layout.addLayout(button_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(20)
        input_layout.addWidget(self.progress_bar)

        splitter.addWidget(input_widget)

        # Results section
        results_widget = StyledWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(10, 10, 10, 10)

        # Results tabs
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)

        # Setup all tabs
        self.setup_clarifier_tab()
        self.setup_summary_tab()
        self.setup_log_tab()
        self.setup_diagram_tab()
        self.setup_tts_tab()
        self.setup_json_tab()

        results_layout.addWidget(self.results_tabs)
        splitter.addWidget(results_widget)

        # Set initial splitter sizes
        splitter.setSizes([300, 600])
        main_layout.addWidget(splitter)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def setup_clarifier_tab(self):
        """Setup the clarifier conversation tab."""
        self.clarifier_tab = StyledWidget()
        clarifier_layout = QVBoxLayout(self.clarifier_tab)
        clarifier_layout.setSpacing(10)

        clarifier_header = QLabel("Clarifier Conversation")
        clarifier_header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        clarifier_layout.addWidget(clarifier_header)

        self.clarifier_display = QTextEdit()
        self.clarifier_display.setReadOnly(True)
        self.clarifier_display.setMinimumHeight(200)
        clarifier_layout.addWidget(self.clarifier_display)

        response_layout = QHBoxLayout()
        self.clarifier_response = QLineEdit()
        self.clarifier_response.setPlaceholderText("Type your response to clarifier questions here...")
        response_layout.addWidget(self.clarifier_response)

        self.send_response_btn = QPushButton("Send Response")
        self.send_response_btn.clicked.connect(self.send_clarifier_response)
        self.send_response_btn.setEnabled(False)
        self.send_response_btn.setMaximumWidth(120)
        response_layout.addWidget(self.send_response_btn)

        clarifier_layout.addLayout(response_layout)
        self.results_tabs.addTab(self.clarifier_tab, "Clarifier")

    def setup_summary_tab(self):
        """Setup the summary results tab."""
        self.summary_tab = StyledWidget()
        summary_layout = QVBoxLayout(self.summary_tab)
        summary_layout.setSpacing(10)

        summary_header = QLabel("Product Summary")
        summary_header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        summary_layout.addWidget(summary_header)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)

        self.results_tabs.addTab(self.summary_tab, "Summary")

    def setup_log_tab(self):
        """Setup the agent logs tab."""
        self.log_tab = StyledWidget()
        log_layout = QVBoxLayout(self.log_tab)
        log_layout.setSpacing(10)

        log_header = QLabel("Agent Logs")
        log_header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        log_layout.addWidget(log_header)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        log_layout.addWidget(self.log_display)

        self.results_tabs.addTab(self.log_tab, "Logs")

    def setup_diagram_tab(self):
        """Setup the diagram results tab."""
        self.diagram_tab = StyledWidget()
        diagram_layout = QVBoxLayout(self.diagram_tab)
        diagram_layout.setSpacing(10)

        diagram_header = QLabel("Product Diagram")
        diagram_header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        diagram_layout.addWidget(diagram_header)

        diagram_info_layout = QVBoxLayout()
        diagram_info_layout.addWidget(QLabel("Diagram URL:"))

        self.diagram_url = QLineEdit()
        self.diagram_url.setReadOnly(True)
        diagram_info_layout.addWidget(self.diagram_url)

        self.open_diagram_btn = QPushButton("Open Diagram in Browser")
        self.open_diagram_btn.clicked.connect(self.open_diagram_in_browser)
        self.open_diagram_btn.setEnabled(False)
        self.open_diagram_btn.setMaximumHeight(36)
        diagram_info_layout.addWidget(self.open_diagram_btn)

        diagram_layout.addLayout(diagram_info_layout)
        diagram_layout.addStretch()

        self.results_tabs.addTab(self.diagram_tab, "Diagram")

    def setup_tts_tab(self):
        """Setup the text-to-speech results tab."""
        self.tts_tab = StyledWidget()
        tts_layout = QVBoxLayout(self.tts_tab)
        tts_layout.setSpacing(10)

        tts_header = QLabel("Audio Summary")
        tts_header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        tts_layout.addWidget(tts_header)

        tts_layout.addWidget(QLabel("TTS File:"))
        self.tts_path = QLineEdit()
        self.tts_path.setReadOnly(True)
        tts_layout.addWidget(self.tts_path)

        self.play_tts_btn = QPushButton("Play Audio")
        self.play_tts_btn.clicked.connect(self.play_tts)
        self.play_tts_btn.setEnabled(False)
        self.play_tts_btn.setMinimumHeight(36)
        tts_layout.addWidget(self.play_tts_btn)

        tts_layout.addStretch()
        self.results_tabs.addTab(self.tts_tab, "Audio")

    def setup_json_tab(self):
        """Setup the JSON results tab."""
        self.json_tab = StyledWidget()
        json_layout = QVBoxLayout(self.json_tab)
        json_layout.setSpacing(10)

        json_header = QLabel("Full JSON Output")
        json_header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        json_layout.addWidget(json_header)

        self.json_text = QTextEdit()
        self.json_text.setReadOnly(True)
        self.json_text.setFont(QFont("Consolas", 10))
        json_layout.addWidget(self.json_text)

        self.results_tabs.addTab(self.json_tab, "Full JSON")

    def browse_image(self):
        """Open file dialog to select an image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.image_path.setText(file_path)

    def browse_audio(self):
        """Open file dialog to select an audio file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio", "", "Audio Files (*.mp3 *.wav *.ogg)")
        if file_path:
            self.audio_path.setText(file_path)
        else:
            self.audio_path.setText("RECORD")

    def run_workflow(self):
        """Run the product conversation workflow."""
        # Get inputs
        text_input = self.text_input.toPlainText().strip()
        image_input = self.image_path.text().strip()
        audio_input = self.audio_path.text().strip()
        generate_audio = self.generate_audio_checkbox.isChecked()

        if not text_input and not image_input and not audio_input:
            QMessageBox.warning(
                self, "Input Error",
                "Please provide at least one input (text, image, or audio).")
            return

        # Update manager with inputs
        self.manager = ProductConversationManager(
            text_input=text_input,
            image_input=image_input if image_input else None,
            audio_input=audio_input if audio_input else None
        )

        # Show progress bar
        self.progress_bar.setVisible(True)
        self.run_btn.setEnabled(False)
        self.status_bar.showMessage("Running workflow...")

        # Clear previous results
        self.clear_all_results()

        # Create and start worker thread
        self.worker = WorkerThread(self.manager, generate_audio)
        self.worker.finished.connect(self.workflow_finished)
        self.worker.progress.connect(self.update_progress)
        self.worker.user_input_required.connect(self.get_user_input)
        self.worker.clarifier_question.connect(self.show_clarifier_question)
        self.worker.start()

    def clear_all_results(self):
        """Clear all previous results from the tabs."""
        self.clarifier_display.clear()
        self.clarifier_response.clear()
        self.send_response_btn.setEnabled(False)

        self.summary_text.clear()

        self.log_display.clear()

        self.diagram_url.clear()
        self.open_diagram_btn.setEnabled(False)

        self.tts_path.clear()
        self.play_tts_btn.setEnabled(False)

        self.json_text.clear()

    def update_progress(self, message):
        """Update progress message and log display."""
        self.status_bar.showMessage(message)
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.log_display.append(f"[{timestamp}] {message}")

    def show_clarifier_question(self, question):
        """Display clarifier question and enable response input."""
        formatted_question = f"Clarifier: {question}\n"
        self.clarifier_display.append(formatted_question)

        # Enable response input
        self.clarifier_response.clear()
        self.clarifier_response.setFocus()
        self.send_response_btn.setEnabled(True)

        # Update status
        self.status_bar.showMessage("Waiting for your response to clarifier question...")

        # Switch to the clarifier tab
        self.results_tabs.setCurrentWidget(self.clarifier_tab)

    def send_clarifier_response(self):
        """Send user response to clarifier question."""
        response = self.clarifier_response.text().strip()
        if response:
            self.clarifier_display.append(f"You: {response}")
            self.worker.clarifier_response_queue.put(response)
            self.clarifier_response.clear()
            self.send_response_btn.setEnabled(False)
            self.status_bar.showMessage("Processing your response...")
        else:
            QMessageBox.warning(self, "Input Error", "Please enter a response.")

    def get_user_input(self, question):
        """Get user input through dialog."""
        text, ok = QInputDialog.getText(self, "User Input Required", question)
        if ok:
            self.worker.answer_queue.put(text)
        else:
            self.worker.answer_queue.put("")

    def workflow_finished(self, result):
        """Handle workflow completion."""
        # Hide progress bar
        self.progress_bar.setVisible(False)
        self.run_btn.setEnabled(True)
        self.send_response_btn.setEnabled(False)

        if not isinstance(result, dict):
            QMessageBox.critical(
                self, "Workflow Error",
                f"Invalid result format: {result}")
            return

        if "error" in result:
            QMessageBox.critical(
                self, "Workflow Error",
                f"Error: {result['error']}")
            self.status_bar.showMessage("Workflow failed")
            return

        # Update UI with results
        self.status_bar.showMessage("Workflow completed successfully")

        # Update summary tab
        if "summary" in result and result["summary"]:
            self.summary_text.setText(result["summary"])
        else:
            self.summary_text.setText("No summary available")

        # Update diagram tab
        if "diagram_url" in result and result["diagram_url"]:
            self.diagram_url.setText(result["diagram_url"])
            self.open_diagram_btn.setEnabled(True)
        else:
            self.diagram_url.setText("No diagram generated")
            self.open_diagram_btn.setEnabled(False)

        # Update TTS tab
        if "tts_file" in result and result["tts_file"]:
            self.tts_path.setText(result["tts_file"])
            self.play_tts_btn.setEnabled(True)
        else:
            self.tts_path.setText("No audio file generated")
            self.play_tts_btn.setEnabled(False)

        # Update JSON tab
        try:
            json_str = json.dumps(result, indent=2)
            self.json_text.setText(json_str)
        except Exception as e:
            self.json_text.setText(f"Error displaying JSON: {str(e)}")

        # Set a timer to switch to the summary tab after a short delay
        self.tab_switch_timer.start(1000)  # 1 second delay

    def switch_to_summary_tab(self):
        """Switch to the summary tab after delay."""
        self.tab_switch_timer.stop()
        self.results_tabs.setCurrentWidget(self.summary_tab)

    def open_diagram_in_browser(self):
        """Open the diagram URL in a web browser."""
        diagram_url = self.diagram_url.text()
        if diagram_url and diagram_url != "No diagram generated":
            webbrowser.open(diagram_url)
            self.status_bar.showMessage("Opened diagram in browser")
        else:
            QMessageBox.warning(
                self, "Diagram Error",
                "No valid diagram URL available")

    def play_tts(self):
        """Play the generated TTS audio."""
        tts_file = self.tts_path.text()
        if not tts_file or not os.path.exists(tts_file):
            QMessageBox.warning(
                self, "Audio Error",
                "Audio file not found.")
            return

        try:
            pygame.mixer.init()
            pygame.mixer.music.load(tts_file)
            pygame.mixer.music.play()
            self.status_bar.showMessage("Playing audio...")
        except Exception as e:
            QMessageBox.critical(
                self, "Audio Error",
                f"Error playing audio: {str(e)}")

    def reset_inputs(self):
        """Reset all input fields and results."""
        self.text_input.clear()
        self.image_path.clear()
        self.audio_path.clear()
        self.clear_all_results()
        self.status_bar.showMessage("Inputs reset")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    window = ProductConversationGUI()
    window.show()
    sys.exit(app.exec_())
