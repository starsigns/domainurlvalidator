# Domain Validator Pro

A high-performance PyQt6 GUI application for validating millions of domain names using DNS lookups.

## Features

- **GUI Interface**: Easy-to-use PyQt6 interface
- **Bulk Processing**: Handle millions of domains efficiently
- **Multi-threading**: Concurrent domain validation for speed
- **Real-time Progress**: Live progress tracking and statistics
- **Export Options**: Export valid, invalid, or all domains to text files
- **DNS Validation**: Uses DNS lookups to verify domain existence

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python main.py
```

2. Click "Browse File" to select your domain list (text file, one domain per line)
3. Adjust thread count if needed (default: 50 threads)
4. Click "Start Validation" to begin processing
5. Monitor progress in real-time
6. Export results when complete

## Input Format

Your domain file should contain one domain per line:
```
example.com
google.com
invalid-domain-xyz.com
facebook.com
```

## Performance

- Processes 50-200 domains per second (depending on network and thread count)
- Memory efficient - handles millions of domains
- Concurrent DNS lookups with configurable thread count

## Requirements

- Python 3.8+
- PyQt6
- Internet connection for DNS lookups

## Architecture

- **GUI Layer**: PyQt6 main window with progress tracking
- **Worker Thread**: Background domain validation
- **DNS Validation**: Socket-based domain existence checking
- **Export Module**: Text file generation for results
