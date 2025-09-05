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

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QGroupBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QHeaderView, QComboBox
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QFont, QColor


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
        
    def run(self):
        """Main validation process"""
        self.queue = Queue()
        
        # Add all domains to queue
        for domain in self.domains:
            self.queue.put(domain)
        
        # Start worker threads
        threads = []
        for _ in range(min(self.max_threads, len(self.domains))):
            thread = threading.Thread(target=self._worker)
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        self.queue.join()
        self.finished.emit()
    
    def _worker(self):
        """Worker thread function"""
        while not self.queue.empty() and not self.stop_requested:
            try:
                domain = self.queue.get_nowait()
                is_valid, error_msg = self._check_domain(domain)
                
                if is_valid:
                    self.valid_domains.append(domain)
                else:
                    self.invalid_domains.append(domain)
                
                self.domain_processed.emit(domain, is_valid, error_msg)
                self.processed_count += 1
                self.progress_updated.emit(self.processed_count)
                self.queue.task_done()
                
            except Exception as e:
                break
    
    def _check_domain(self, domain: str) -> tuple:
        """Check if domain exists using DNS lookup"""
        try:
            # Clean domain name
            domain = domain.strip().lower()
            if domain.startswith(('http://', 'https://')):
                domain = domain.split('://', 1)[1]
            if '/' in domain:
                domain = domain.split('/')[0]
            
            # DNS lookup with timeout
            socket.setdefaulttimeout(5)
            socket.gethostbyname(domain)
            return True, ""
            
        except socket.gaierror as e:
            return False, f"DNS Error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def stop(self):
        """Stop the validation process"""
        self.stop_requested = True


class DomainValidatorGUI(QMainWindow):
    """Main GUI application"""
    
    def __init__(self):
        super().__init__()
        self.domains = []
        self.valid_domains = []
        self.invalid_domains = []
        self.worker = None
        self.start_time = None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Domain Validator Pro")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Domain Validator Pro")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        main_layout.addWidget(title_label)
        
        # File selection section
        file_group = QGroupBox("1. Select Domain File")
        file_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.browse_btn = QPushButton("Browse File")
        self.browse_btn.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_btn)
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # Settings section
        settings_group = QGroupBox("2. Validation Settings")
        settings_layout = QHBoxLayout()
        
        settings_layout.addWidget(QLabel("Max Threads:"))
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 200)
        self.threads_spin.setValue(50)
        settings_layout.addWidget(self.threads_spin)
        
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # Control section
        control_group = QGroupBox("3. Validation Control")
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Validation")
        self.start_btn.clicked.connect(self.start_validation)
        self.start_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_validation)
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
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
        main_layout.addWidget(progress_group)
        
        # Results section with tabs
        self.tab_widget = QTabWidget()
        
        # Log tab
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.tab_widget.addTab(self.log_text, "Processing Log")
        
        # Results table tab
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Domain", "Status", "Error"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tab_widget.addTab(self.results_table, "Results")
        
        main_layout.addWidget(self.tab_widget)
        
        # Export section
        export_group = QGroupBox("5. Export Results")
        export_layout = QHBoxLayout()
        
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
        export_layout.addStretch()
        
        export_group.setLayout(export_layout)
        main_layout.addWidget(export_group)
        
        # Timer for updating stats
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        
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
        """Stop the validation process"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        
        self.validation_finished()
        self.log("Validation stopped by user")
    
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
        
        # Update UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        
        # Enable export buttons
        self.export_valid_btn.setEnabled(True)
        self.export_invalid_btn.setEnabled(True)
        self.export_all_btn.setEnabled(True)
        
        # Final stats
        total_time = time.time() - self.start_time if self.start_time else 0
        total_processed = len(self.valid_domains) + len(self.invalid_domains)
        
        self.log(f"\n{'='*50}")
        self.log("VALIDATION COMPLETE")
        self.log(f"{'='*50}")
        self.log(f"Total domains: {len(self.domains):,}")
        self.log(f"Valid domains: {len(self.valid_domains):,}")
        self.log(f"Invalid domains: {len(self.invalid_domains):,}")
        self.log(f"Processing time: {total_time:.1f} seconds")
        self.log(f"Average speed: {total_processed/total_time:.1f} domains/sec" if total_time > 0 else "N/A")
        
        QMessageBox.information(
            self, "Validation Complete",
            f"Processing complete!\n\n"
            f"Valid domains: {len(self.valid_domains):,}\n"
            f"Invalid domains: {len(self.invalid_domains):,}\n"
            f"Time: {total_time:.1f} seconds"
        )
    
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
