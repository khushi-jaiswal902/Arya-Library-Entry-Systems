from library_app.data_store import (
    ensure_students_file,
    ensure_visits_file,
    get_active_visits,
    get_dashboard_summary,
    get_recent_visits,
    get_students_file,
    load_students,
    load_visits,
    process_scan,
    process_scan_result,
    save_visits,
)
from library_app.scanner_service import open_camera, run_scanner


__all__ = [
    "ensure_students_file",
    "ensure_visits_file",
    "get_active_visits",
    "get_dashboard_summary",
    "get_recent_visits",
    "get_students_file",
    "load_students",
    "load_visits",
    "open_camera",
    "process_scan",
    "process_scan_result",
    "run_scanner",
    "save_visits",
]


if __name__ == "__main__":
    run_scanner()
