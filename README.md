# Student Performance Analytics Portal

A clean, responsive web application for managing student performances, computing subject-wise scores, determining academic ranks fairly across different departments, and exporting standings as CSV reports.

## Features
- **Dynamic Dashboard:** View overall school statistics and department performance.
- **Fair Rankings:** Ranks students based on average percentage rather than total scores, ensuring fairness across departments with different numbers of subjects.
- **Dynamic Theming:** Color schemes adapt to the selected department (e.g., green for CSE, blue for Civil, etc.).
- **CSV Export:** Download department or overall leaderboards directly to CSV.

## Prerequisites
- Python 3.8 or higher installed on your computer.

## Getting Started

Follow these steps to run the application locally:

### 1. Clone the Repository
```bash
git clone https://github.com/aswin742/Student-Performance.git
cd Student-Performance
```

### 2. Create and Activate a Virtual Environment
**On Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

Open your browser and navigate to **`http://127.0.0.1:5000`**.

## Running Tests
To run the automated test suite, use:
```bash
python test_app.py
```
