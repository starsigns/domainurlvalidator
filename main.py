"""
Domain Validator Pro - PyQt6 Edition
A production-ready domain validation tool for processing millions of domains
"""

import sys
import os
import socket
import threading
from datetime import datetime
from queue import Queue
from typing import List, Set
import time
import psutil

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QGroupBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QHeaderView, QComboBox, QStatusBar, QMenuBar, QSplitter,
    QCheckBox, QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt, QSettings
from PyQt6.QtGui import QFont, QColor, QAction, QKeySequence, QPalette


class DomainValidationWorker(QThread):
    """Worker thread for domain validation"""
    
    progress_updated = pyqtSignal(int)
    domain_processed = pyqtSignal(str, bool, str)  # domain, is_valid, error_msg
    finished = pyqtSignal()
    
    def __init__(self, domains: List[str], max_threads: int = 50):
        super().__init__()
        self.domains = domains
        self.max_threads = max_threads
        self.stop_requested = False
        self.processed_count = 0
        self.valid_domains = []
        self.invalid_domains = []
        self.worker_threads = []
        
    def run(self):
        """Main validation process"""
        self.queue = Queue()
        
        # Add all domains to queue
        for domain in self.domains:
            if self.stop_requested:
                break
            self.queue.put(domain)
        
        # Start worker threads
        self.worker_threads = []
        for _ in range(min(self.max_threads, len(self.domains))):
            if self.stop_requested:
                break
            thread = threading.Thread(target=self._worker)
            thread.daemon = True  # Daemon threads will be killed when main thread exits
            thread.start()
            self.worker_threads.append(thread)
        
        # Wait for completion or stop request
        while not self.queue.empty() and not self.stop_requested:
            self.msleep(100)  # Check every 100ms
        
        # Signal completion
        if not self.stop_requested:
            self.finished.emit()
    
    def _worker(self):
        """Worker thread function"""
        while not self.stop_requested:
            try:
                domain = self.queue.get_nowait()
                
                # Double-check stop request before processing
                if self.stop_requested:
                    self.queue.task_done()
                    break
                
                is_valid, error_msg = self._check_domain(domain)
                
                # Check again after potentially slow DNS lookup
                if self.stop_requested:
                    self.queue.task_done()
                    break
                
                if is_valid:
                    self.valid_domains.append(domain)
                else:
                    self.invalid_domains.append(domain)
                
                self.domain_processed.emit(domain, is_valid, error_msg)
                self.processed_count += 1
                self.progress_updated.emit(self.processed_count)
                self.queue.task_done()
                
            except:
                # Queue is empty or error occurred
                break
    
    def _check_domain(self, domain: str) -> tuple:
        """Check if domain exists using DNS lookup with stop support"""
        try:
            # Return immediately if stop requested
            if self.stop_requested:
                return False, "Stopped"
            
            # Clean domain name
            domain = domain.strip().lower()
            if domain.startswith(('http://', 'https://')):
                domain = domain.split('://', 1)[1]
            if '/' in domain:
                domain = domain.split('/')[0]
            
            # DNS lookup with shorter timeout for responsiveness
            socket.setdefaulttimeout(3)  # Reduced from 5 to 3 seconds
            socket.gethostbyname(domain)
            return True, ""
            
        except socket.gaierror as e:
            return False, f"DNS Error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def stop(self):
        """Stop the validation process immediately"""
        self.stop_requested = True
        
        # Clear the queue to prevent further processing
        try:
            while not self.queue.empty():
                self.queue.get_nowait()
                self.queue.task_done()
        except:
            pass


class DomainValidatorGUI(QMainWindow):
    """Main GUI application"""
    
    def __init__(self):
        super().__init__()
        self.domains = []
        self.valid_domains = []
        self.invalid_domains = []
        self.worker = None
        self.start_time = None
        
        # UI state variables
        self.settings = QSettings('DomainValidator', 'Settings')
        self.is_dark_theme = self.settings.value('dark_theme', False, type=bool)
        self.is_fullscreen = False
        
        # System monitoring
        self.system_timer = QTimer()
        self.system_timer.timeout.connect(self.update_system_info)
        self.system_timer.start(1000)  # Update every second
        
        self.init_ui()
        self.apply_theme()
        self.create_menu_bar()
        self.create_status_bar()
        self.restore_settings()
        
    def init_ui(self):
        """Initialize the user interface with resizable panels"""
        self.setWindowTitle("Domain Validator Pro")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        
        # Central widget with main splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Main horizontal splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Left panel (controls)
        self.left_panel = self.create_left_panel()
        self.main_splitter.addWidget(self.left_panel)
        
        # Right panel (results) with vertical splitter
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.addWidget(self.right_splitter)
        
        # Results panel
        self.results_panel = self.create_results_panel()
        self.right_splitter.addWidget(self.results_panel)
        
        # Log panel
        self.log_panel = self.create_log_panel()
        self.right_splitter.addWidget(self.log_panel)
        
        # Set initial splitter sizes
        self.main_splitter.setSizes([350, 850])
        self.right_splitter.setSizes([500, 200])
        
        # Make panels collapsible
        self.main_splitter.setCollapsible(0, True)
        self.main_splitter.setCollapsible(1, False)
        self.right_splitter.setCollapsible(0, False)
        self.right_splitter.setCollapsible(1, True)
        
    def create_left_panel(self):
        """Create the left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title_label = QLabel("Domain Validator Pro")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # File selection section
        file_group = QGroupBox("1. Select Domain File")
        file_layout = QVBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.browse_btn = QPushButton("Browse File")
        self.browse_btn.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Settings section
        settings_group = QGroupBox("2. Validation Settings")
        settings_layout = QVBoxLayout()
        
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel("Max Threads:"))
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 200)
        self.threads_spin.setValue(50)
        self.threads_spin.setMinimumWidth(80)  # Set minimum width for 3 digits
        self.threads_spin.setMaximumWidth(100)  # Prevent it from getting too wide
        self.threads_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thread_layout.addWidget(self.threads_spin)
        thread_layout.addStretch()
        
        settings_layout.addLayout(thread_layout)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Control section
        control_group = QGroupBox("3. Validation Control")
        control_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("Start Validation")
        self.start_btn.clicked.connect(self.start_validation)
        self.start_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_validation)
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Progress section
        progress_group = QGroupBox("4. Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to start")
        self.stats_label = QLabel("Valid: 0 | Invalid: 0 | Speed: 0 domains/sec")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.stats_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Export section
        export_group = QGroupBox("5. Export Results")
        export_layout = QVBoxLayout()
        
        self.export_valid_btn = QPushButton("Export Valid Domains")
        self.export_valid_btn.clicked.connect(lambda: self.export_domains("valid"))
        self.export_valid_btn.setEnabled(False)
        
        self.export_invalid_btn = QPushButton("Export Invalid Domains")
        self.export_invalid_btn.clicked.connect(lambda: self.export_domains("invalid"))
        self.export_invalid_btn.setEnabled(False)
        
        self.export_all_btn = QPushButton("Export All Results")
        self.export_all_btn.clicked.connect(lambda: self.export_domains("all"))
        self.export_all_btn.setEnabled(False)
        
        export_layout.addWidget(self.export_valid_btn)
        export_layout.addWidget(self.export_invalid_btn)
        export_layout.addWidget(self.export_all_btn)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        return panel
    
    def create_results_panel(self):
        """Create the results panel with tabs"""
        self.tab_widget = QTabWidget()
        
        # Results table tab
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Domain", "Status", "Error"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tab_widget.addTab(self.results_table, "Results")
        
        return self.tab_widget
    
    def create_log_panel(self):
        """Create the log panel"""
        log_group = QGroupBox("Processing Log")
        layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMaximumHeight(200)
        
        layout.addWidget(self.log_text)
        
        # Timer for updating stats
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        
        return log_group
    
    def create_menu_bar(self):
        """Create menu bar with theme toggle and view options"""
        menubar = self.menuBar()
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        # Theme toggle
        self.theme_action = QAction('Dark Theme', self)
        self.theme_action.setCheckable(True)
        self.theme_action.setChecked(self.is_dark_theme)
        self.theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.theme_action)
        
        view_menu.addSeparator()
        
        # Full screen
        self.fullscreen_action = QAction('Full Screen', self)
        self.fullscreen_action.setShortcut(QKeySequence('F11'))
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)
        
        view_menu.addSeparator()
        
        # Panel visibility
        self.show_left_panel_action = QAction('Show Control Panel', self)
        self.show_left_panel_action.setCheckable(True)
        self.show_left_panel_action.setChecked(True)
        self.show_left_panel_action.triggered.connect(self.toggle_left_panel)
        view_menu.addAction(self.show_left_panel_action)
        
        self.show_log_panel_action = QAction('Show Log Panel', self)
        self.show_log_panel_action.setCheckable(True)
        self.show_log_panel_action.setChecked(True)
        self.show_log_panel_action.triggered.connect(self.toggle_log_panel)
        view_menu.addAction(self.show_log_panel_action)
    
    def create_status_bar(self):
        """Create status bar with system information"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # System info labels
        self.cpu_label = QLabel("CPU: 0%")
        self.memory_label = QLabel("Memory: 0%")
        self.network_label = QLabel("Network: 0 KB/s")
        
        # Add permanent widgets to status bar
        self.status_bar.addWidget(QLabel("System:"))
        self.status_bar.addWidget(self.cpu_label)
        self.status_bar.addWidget(QLabel("|"))
        self.status_bar.addWidget(self.memory_label)
        self.status_bar.addWidget(QLabel("|"))
        self.status_bar.addWidget(self.network_label)
        
        # Add stretch to push system info to the right
        self.status_bar.addPermanentWidget(QFrame())
        
    def update_system_info(self):
        """Update system information in status bar"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent()
            self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_label.setText(f"Memory: {memory.percent:.1f}%")
            
            # Network usage (simplified)
            net_io = psutil.net_io_counters()
            if hasattr(self, 'prev_net_io'):
                bytes_sent = net_io.bytes_sent - self.prev_net_io.bytes_sent
                bytes_recv = net_io.bytes_recv - self.prev_net_io.bytes_recv
                total_bytes = bytes_sent + bytes_recv
                kb_per_sec = total_bytes / 1024
                self.network_label.setText(f"Network: {kb_per_sec:.1f} KB/s")
            self.prev_net_io = net_io
            
        except Exception as e:
            # Silently handle errors
            pass
    
    def apply_theme(self):
        """Apply comprehensive eye-friendly dark or light theme"""
        if self.is_dark_theme:
            # Comprehensive dark theme with proper visibility
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2d2d30;
                    color: #c8c8c8;
                }
                QWidget {
                    color: #c8c8c8;
                    background-color: #2d2d30;
                }
                QLabel {
                    color: #c8c8c8;
                    background-color: transparent;
                }
                QGroupBox {
                    font-weight: 500;
                    border: 1px solid #505053;
                    border-radius: 6px;
                    margin-top: 1ex;
                    padding-top: 6px;
                    background-color: #343437;
                    color: #c8c8c8;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #87afd7;
                }
                QPushButton {
                    background-color: #414144;
                    border: 1px solid #5a5a5d;
                    border-radius: 4px;
                    padding: 6px 12px;
                    color: #c8c8c8;
                    font-weight: 500;
                    min-width: 70px;
                }
                QPushButton:hover {
                    background-color: #4682b4;
                    border-color: #5a90c4;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: #3a6fa0;
                }
                QPushButton:disabled {
                    background-color: #383838;
                    border-color: #4a4a4a;
                    color: #787878;
                }
                QSpinBox {
                    background-color: #343437;
                    border: 1px solid #505053;
                    border-radius: 3px;
                    padding: 4px 8px;
                    color: #c8c8c8;
                    min-width: 80px;
                    max-width: 100px;
                    font-weight: 500;
                }
                QSpinBox::up-button, QSpinBox::down-button {
                    background-color: #414144;
                    border: 1px solid #505053;
                    width: 16px;
                }
                QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                    background-color: #4682b4;
                }
                QProgressBar {
                    border: 1px solid #505053;
                    border-radius: 3px;
                    text-align: center;
                    font-weight: 500;
                    background-color: #343437;
                    color: #c8c8c8;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6bb6a8, stop:1 #5ca99a);
                    border-radius: 2px;
                }
                QTableWidget {
                    gridline-color: #505053;
                    background-color: #343437;
                    alternate-background-color: #3a3a3e;
                    border: 1px solid #505053;
                    color: #c8c8c8;
                }
                QHeaderView::section {
                    background-color: #414144;
                    padding: 4px;
                    border: 1px solid #505053;
                    font-weight: 500;
                    color: #c8c8c8;
                }
                QTabWidget::pane {
                    border: 1px solid #505053;
                    background-color: #343437;
                }
                QTabBar::tab {
                    background-color: #414144;
                    border: 1px solid #505053;
                    padding: 6px 12px;
                    margin-right: 1px;
                    color: #c8c8c8;
                }
                QTabBar::tab:selected {
                    background-color: #4682b4;
                    color: white;
                }
                QTextEdit {
                    background-color: #343437;
                    border: 1px solid #505053;
                    border-radius: 3px;
                    padding: 2px;
                    color: #c8c8c8;
                }
                QStatusBar {
                    background-color: #414144;
                    border-top: 1px solid #505053;
                    color: #c8c8c8;
                }
                QMenuBar {
                    background-color: #414144;
                    border-bottom: 1px solid #505053;
                    color: #c8c8c8;
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 4px 8px;
                    color: #c8c8c8;
                }
                QMenuBar::item:selected {
                    background-color: #4682b4;
                    color: white;
                }
                QMenu {
                    background-color: #343437;
                    border: 1px solid #505053;
                    color: #c8c8c8;
                }
                QMenu::item {
                    padding: 4px 20px;
                    background-color: transparent;
                }
                QMenu::item:selected {
                    background-color: #4682b4;
                    color: white;
                }
                QSplitter::handle {
                    background-color: #505053;
                }
                QSplitter::handle:hover {
                    background-color: #4682b4;
                }
            """)
        else:
            # Comprehensive light theme with proper visibility
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #fcfcfa;
                    color: #3c3c3a;
                }
                QWidget {
                    color: #3c3c3a;
                    background-color: #fcfcfa;
                }
                QLabel {
                    color: #3c3c3a;
                    background-color: transparent;
                }
                QGroupBox {
                    font-weight: 500;
                    border: 1px solid #dcdcda;
                    border-radius: 6px;
                    margin-top: 1ex;
                    padding-top: 6px;
                    background-color: #ffffff;
                    color: #3c3c3a;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #4678aa;
                }
                QPushButton {
                    background-color: #f0f0ee;
                    border: 1px solid #d0d0ce;
                    border-radius: 4px;
                    padding: 6px 12px;
                    color: #3c3c3a;
                    font-weight: 500;
                    min-width: 70px;
                }
                QPushButton:hover {
                    background-color: #6496c8;
                    border-color: #5486b8;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #5486b8;
                }
                QPushButton:disabled {
                    background-color: #f8f8f6;
                    border-color: #e8e8e6;
                    color: #8c8c8a;
                }
                QSpinBox {
                    background-color: #ffffff;
                    border: 1px solid #dcdcda;
                    border-radius: 3px;
                    padding: 4px 8px;
                    color: #3c3c3a;
                    min-width: 80px;
                    max-width: 100px;
                    font-weight: 500;
                }
                QSpinBox::up-button, QSpinBox::down-button {
                    background-color: #f0f0ee;
                    border: 1px solid #dcdcda;
                    width: 16px;
                }
                QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                    background-color: #6496c8;
                }
                QProgressBar {
                    border: 1px solid #dcdcda;
                    border-radius: 3px;
                    text-align: center;
                    font-weight: 500;
                    background-color: #f8f8f6;
                    color: #3c3c3a;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #7bb573, stop:1 #6aa563);
                    border-radius: 2px;
                }
                QTableWidget {
                    gridline-color: #e0e0de;
                    background-color: #ffffff;
                    alternate-background-color: #f8f8f6;
                    border: 1px solid #dcdcda;
                    color: #3c3c3a;
                }
                QHeaderView::section {
                    background-color: #f0f0ee;
                    padding: 4px;
                    border: 1px solid #dcdcda;
                    font-weight: 500;
                    color: #3c3c3a;
                }
                QTabWidget::pane {
                    border: 1px solid #dcdcda;
                    background-color: #ffffff;
                }
                QTabBar::tab {
                    background-color: #f0f0ee;
                    border: 1px solid #dcdcda;
                    padding: 6px 12px;
                    margin-right: 1px;
                    color: #3c3c3a;
                }
                QTabBar::tab:selected {
                    background-color: #6496c8;
                    color: white;
                }
                QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #dcdcda;
                    border-radius: 3px;
                    padding: 2px;
                    color: #3c3c3a;
                }
                QStatusBar {
                    background-color: #f0f0ee;
                    border-top: 1px solid #dcdcda;
                    color: #3c3c3a;
                }
                QMenuBar {
                    background-color: #f0f0ee;
                    border-bottom: 1px solid #dcdcda;
                    color: #3c3c3a;
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 4px 8px;
                    color: #3c3c3a;
                }
                QMenuBar::item:selected {
                    background-color: #6496c8;
                    color: white;
                }
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #dcdcda;
                    color: #3c3c3a;
                }
                QMenu::item {
                    padding: 4px 20px;
                    background-color: transparent;
                }
                QMenu::item:selected {
                    background-color: #6496c8;
                    color: white;
                }
                QSplitter::handle {
                    background-color: #dcdcda;
                }
                QSplitter::handle:hover {
                    background-color: #6496c8;
                }
            """)
            # Eye-friendly Dark theme - Warm, low contrast colors
            dark_palette = QPalette()
            
            # Warm dark backgrounds - easier on the eyes
            dark_palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))        # Warm dark gray
            dark_palette.setColor(QPalette.ColorRole.Base, QColor(52, 52, 55))          # Input fields
            dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(58, 58, 62)) # Alternating rows
            
            # Soft text colors - reduced contrast for comfort
            dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(200, 200, 200)) # Soft white
            dark_palette.setColor(QPalette.ColorRole.Text, QColor(200, 200, 200))       # Input text
            dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(220, 220, 220)) # Bright text
            
            # Comfortable button colors
            dark_palette.setColor(QPalette.ColorRole.Button, QColor(65, 65, 68))        # Button bg
            dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(200, 200, 200)) # Button text
            
            # Soft blue highlights - not too bright
            dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(70, 130, 180))   # Steel blue
            dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            
            # Gentle accent colors
            dark_palette.setColor(QPalette.ColorRole.Link, QColor(135, 175, 215))       # Soft blue
            dark_palette.setColor(QPalette.ColorRole.LinkVisited, QColor(175, 135, 215)) # Soft purple
            
            # Tooltips
            dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(60, 60, 63))
            dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(200, 200, 200))
            
            # Borders and separators - very subtle
            dark_palette.setColor(QPalette.ColorRole.Mid, QColor(80, 80, 83))
            dark_palette.setColor(QPalette.ColorRole.Dark, QColor(35, 35, 38))
            dark_palette.setColor(QPalette.ColorRole.Shadow, QColor(0, 0, 0, 50))
            
            # Disabled colors - subtle difference
            dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(120, 120, 120))
            dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(120, 120, 120))
            dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(120, 120, 120))
            
            QApplication.instance().setPalette(dark_palette)
            
            # Soft styling for dark theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2d2d30;
                }
                QGroupBox {
                    font-weight: 500;
                    border: 1px solid #505053;
                    border-radius: 6px;
                    margin-top: 1ex;
                    padding-top: 6px;
                    background-color: #343437;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #87afd7;
                }
                QPushButton {
                    background-color: #414144;
                    border: 1px solid #5a5a5d;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: 500;
                    min-width: 70px;
                }
                QPushButton:hover {
                    background-color: #4682b4;
                    border-color: #5a90c4;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: #3a6fa0;
                }
                QPushButton:disabled {
                    background-color: #383838;
                    border-color: #4a4a4a;
                    color: #787878;
                }
                QProgressBar {
                    border: 1px solid #505053;
                    border-radius: 3px;
                    text-align: center;
                    font-weight: 500;
                    background-color: #343437;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6bb6a8, stop:1 #5ca99a);
                    border-radius: 2px;
                }
                QTableWidget {
                    gridline-color: #505053;
                    background-color: #343437;
                    alternate-background-color: #3a3a3e;
                    border: 1px solid #505053;
                }
                QHeaderView::section {
                    background-color: #414144;
                    padding: 4px;
                    border: 1px solid #505053;
                    font-weight: 500;
                }
                QTabWidget::pane {
                    border: 1px solid #505053;
                    background-color: #343437;
                }
                QTabBar::tab {
                    background-color: #414144;
                    border: 1px solid #505053;
                    padding: 6px 12px;
                    margin-right: 1px;
                }
                QTabBar::tab:selected {
                    background-color: #4682b4;
                    color: white;
                }
                QStatusBar {
                    background-color: #414144;
                    border-top: 1px solid #505053;
                }
                QMenuBar {
                    background-color: #414144;
                    border-bottom: 1px solid #505053;
                }
                QMenuBar::item:selected {
                    background-color: #4682b4;
                    color: white;
                }
                QMenu {
                    background-color: #343437;
                    border: 1px solid #505053;
                }
                QMenu::item:selected {
                    background-color: #4682b4;
                    color: white;
                }
                QSplitter::handle {
                    background-color: #505053;
                }
                QSplitter::handle:hover {
                    background-color: #4682b4;
                }
                QTextEdit, QLineEdit, QSpinBox {
                    background-color: #343437;
                    border: 1px solid #505053;
                    border-radius: 3px;
                    padding: 2px;
                }
                QSpinBox {
                    min-width: 80px;
                    max-width: 100px;
                    padding: 4px 8px;
                    font-weight: 500;
                }
                QSpinBox::up-button, QSpinBox::down-button {
                    background-color: #414144;
                    border: 1px solid #505053;
                    width: 16px;
                }
                QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                    background-color: #4682b4;
                }
            """)
    
    def toggle_theme(self):
        """Toggle between dark and light theme"""
        self.is_dark_theme = not self.is_dark_theme
        self.settings.setValue('dark_theme', self.is_dark_theme)
        self.apply_theme()
        self.theme_action.setChecked(self.is_dark_theme)
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_action.setText('Full Screen')
        else:
            self.showFullScreen()
            self.fullscreen_action.setText('Exit Full Screen')
    
    def toggle_left_panel(self):
        """Toggle left panel visibility"""
        if self.show_left_panel_action.isChecked():
            self.main_splitter.setSizes([350, 850])
        else:
            self.main_splitter.setSizes([0, 1200])
    
    def toggle_log_panel(self):
        """Toggle log panel visibility"""
        if self.show_log_panel_action.isChecked():
            self.right_splitter.setSizes([500, 200])
        else:
            self.right_splitter.setSizes([700, 0])
    
    def restore_settings(self):
        """Restore saved window geometry and splitter states"""
        # Restore window geometry
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore splitter states
        main_splitter_state = self.settings.value('main_splitter')
        if main_splitter_state:
            self.main_splitter.restoreState(main_splitter_state)
        
        right_splitter_state = self.settings.value('right_splitter')
        if right_splitter_state:
            self.right_splitter.restoreState(right_splitter_state)
        
    def browse_file(self):
        """Browse and select domain file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Domain File", "", "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.domains = [line.strip() for line in f if line.strip()]
                
                self.file_label.setText(f"Loaded: {len(self.domains):,} domains")
                self.start_btn.setEnabled(True)
                self.log(f"Loaded {len(self.domains):,} domains from {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
    
    def start_validation(self):
        """Start the domain validation process"""
        if not self.domains:
            QMessageBox.warning(self, "Warning", "No domains loaded!")
            return
        
        # Reset results
        self.valid_domains.clear()
        self.invalid_domains.clear()
        self.results_table.setRowCount(0)
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        
        # Setup progress
        self.progress_bar.setMaximum(len(self.domains))
        self.progress_bar.setValue(0)
        self.start_time = time.time()
        
        # Start worker
        max_threads = self.threads_spin.value()
        self.worker = DomainValidationWorker(self.domains, max_threads)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.domain_processed.connect(self.domain_processed)
        self.worker.finished.connect(self.validation_finished)
        self.worker.start()
        
        # Start stats timer
        self.stats_timer.start(1000)  # Update every second
        
        self.log(f"Started validation of {len(self.domains):,} domains with {max_threads} threads")
    
    def stop_validation(self):
        """Stop the validation process immediately without blocking"""
        if self.worker and self.worker.isRunning():
            # Stop the worker immediately
            self.worker.stop()
            
            # Set a timer to force terminate if worker doesn't stop gracefully
            self.stop_timer = QTimer()
            self.stop_timer.setSingleShot(True)
            self.stop_timer.timeout.connect(self._force_stop_worker)
            self.stop_timer.start(2000)  # Force stop after 2 seconds
            
            # Connect to finished signal to clean up when worker stops
            self.worker.finished.connect(self._on_worker_stopped)
            
            # Immediately update UI to show stopping state
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("Stopping...")
            self.stats_timer.stop()
            
            self.log("Stopping validation...")
        else:
            self.validation_finished()
    
    def _on_worker_stopped(self):
        """Called when worker stops gracefully"""
        if hasattr(self, 'stop_timer'):
            self.stop_timer.stop()
        self.validation_finished()
        self.log("Validation stopped successfully")
    
    def _force_stop_worker(self):
        """Force terminate the worker if it doesn't stop gracefully"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()  # Force terminate
            self.worker.wait(1000)    # Wait up to 1 second
            self.validation_finished()
            self.log("Validation force stopped")
    
    def update_progress(self, processed_count):
        """Update progress bar"""
        self.progress_bar.setValue(processed_count)
        percentage = (processed_count / len(self.domains)) * 100
        self.progress_label.setText(f"Processed: {processed_count:,} / {len(self.domains):,} ({percentage:.1f}%)")
    
    def domain_processed(self, domain, is_valid, error_msg):
        """Handle processed domain result"""
        if is_valid:
            self.valid_domains.append(domain)
            status = "Valid"
            color = QColor(0, 150, 0)
        else:
            self.invalid_domains.append(domain)
            status = "Invalid"
            color = QColor(200, 0, 0)
        
        # Add to results table (limit to prevent memory issues)
        if self.results_table.rowCount() < 10000:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            self.results_table.setItem(row, 0, QTableWidgetItem(domain))
            
            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.results_table.setItem(row, 1, status_item)
            
            self.results_table.setItem(row, 2, QTableWidgetItem(error_msg))
    
    def update_stats(self):
        """Update statistics display"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            processed = len(self.valid_domains) + len(self.invalid_domains)
            speed = processed / elapsed if elapsed > 0 else 0
            
            self.stats_label.setText(
                f"Valid: {len(self.valid_domains):,} | "
                f"Invalid: {len(self.invalid_domains):,} | "
                f"Speed: {speed:.1f} domains/sec"
            )
    
    def validation_finished(self):
        """Handle validation completion"""
        self.stats_timer.stop()
        
        # Clean up timers
        if hasattr(self, 'stop_timer'):
            self.stop_timer.stop()
            del self.stop_timer
        
        # Update UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("Stop")  # Reset button text
        self.browse_btn.setEnabled(True)
        
        # Enable export buttons if we have results
        has_results = len(self.valid_domains) > 0 or len(self.invalid_domains) > 0
        self.export_valid_btn.setEnabled(has_results and len(self.valid_domains) > 0)
        self.export_invalid_btn.setEnabled(has_results and len(self.invalid_domains) > 0)
        self.export_all_btn.setEnabled(has_results)
        
        # Final stats
        if self.start_time:
            total_time = time.time() - self.start_time
            total_processed = len(self.valid_domains) + len(self.invalid_domains)
            
            self.log(f"\n{'='*50}")
            self.log("VALIDATION COMPLETE")
            self.log(f"{'='*50}")
            self.log(f"Total domains: {len(self.domains):,}")
            self.log(f"Valid domains: {len(self.valid_domains):,}")
            self.log(f"Invalid domains: {len(self.invalid_domains):,}")
            self.log(f"Processing time: {total_time:.1f} seconds")
            if total_time > 0:
                self.log(f"Average speed: {total_processed/total_time:.1f} domains/sec")
            
            # Only show completion message if we actually processed domains
            if total_processed > 0:
                QMessageBox.information(
                    self, "Validation Complete",
                    f"Processing complete!\n\n"
                    f"Valid domains: {len(self.valid_domains):,}\n"
                    f"Invalid domains: {len(self.invalid_domains):,}\n"
                    f"Time: {total_time:.1f} seconds"
                )
        
        # Clean up worker
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
    
    def export_domains(self, export_type):
        """Export domains to file"""
        if export_type == "valid":
            domains_to_export = self.valid_domains
            default_name = "valid_domains.txt"
        elif export_type == "invalid":
            domains_to_export = self.invalid_domains
            default_name = "invalid_domains.txt"
        else:  # all
            domains_to_export = self.valid_domains + self.invalid_domains
            default_name = "all_domains.txt"
        
        if not domains_to_export:
            QMessageBox.warning(self, "Warning", f"No {export_type} domains to export!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Export {export_type.title()} Domains", default_name, "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for domain in domains_to_export:
                        f.write(f"{domain}\n")
                
                self.log(f"Exported {len(domains_to_export):,} {export_type} domains to {os.path.basename(file_path)}")
                QMessageBox.information(self, "Success", f"Exported {len(domains_to_export):,} domains successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")
    
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key.Key_F11:
            # Toggle fullscreen with F11
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Save window geometry and splitter states
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('main_splitter', self.main_splitter.saveState())
        self.settings.setValue('right_splitter', self.right_splitter.saveState())
        
        # Stop worker if running
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, 'Confirm Exit',
                'Validation is still running. Do you want to stop it and exit?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Force immediate stop for application exit
                self.worker.stop()
                if self.worker.isRunning():
                    self.worker.terminate()
                    self.worker.wait(1000)  # Wait up to 1 second
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Domain Validator Pro")
    app.setApplicationVersion("1.0")
    
    window = DomainValidatorGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
