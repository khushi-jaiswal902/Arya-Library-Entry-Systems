import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

DEFAULT_STUDENTS_FILE = BASE_DIR / "students.csv"
LIBRARY_DATA_FILE = BASE_DIR / "library_management - Sheet1 (2).csv"
EXCEL_STUDENTS_FILE = BASE_DIR / "ACE DATA-2024-25. Librar.xlsx"
VISITS_FILE = BASE_DIR / "visits.csv"
ADMIN_CONFIG_FILE = BASE_DIR / "admin_config.json"
EMAIL_CONFIG_FILE = BASE_DIR / "email_config.json"
LIBRARY_DB_FILE = BASE_DIR / "library_data.db"

WINDOW_NAME = "Library Management Scanner"
COOLDOWN_SECONDS = 2
DUPLICATE_SCAN_GAP_SECONDS = 8

VISIT_FIELDS = [
    "visit_id",
    "student_id",
    "name",
    "father_name",
    "date",
    "entry_time",
    "exit_time",
]

HOST = "127.0.0.1"
PORT = 8000
APP_TIMEZONE = os.environ.get("LIBRARY_TIMEZONE", "Asia/Kolkata").strip() or "Asia/Kolkata"

HTML_FILE = DASHBOARD_DIR / "index.html"
LOGIN_HTML_FILE = DASHBOARD_DIR / "login.html"
CAMERA_HTML_FILE = DASHBOARD_DIR / "camera.html"
RECENT_VISITS_HTML_FILE = DASHBOARD_DIR / "recent_visits.html"
STUDENTS_INSIDE_HTML_FILE = DASHBOARD_DIR / "students_inside.html"
WEEKLY_REPORT_HTML_FILE = DASHBOARD_DIR / "weekly_report.html"
CSS_FILE = DASHBOARD_DIR / "styles.css"
JS_FILE = DASHBOARD_DIR / "app.js"
LOGIN_CSS_FILE = DASHBOARD_DIR / "login.css"
LOGIN_JS_FILE = DASHBOARD_DIR / "login.js"
FAVICON_FILE = DASHBOARD_DIR / "favicon.svg"
ARYA_LOGO_FILE = DASHBOARD_DIR / "arya_logo.svg"
ACE_LOGO_FILE = BASE_DIR / "ACE LOGO.jpg.jpeg"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "ChangeMe123!"
DEFAULT_ADMIN_EMAIL = ""
