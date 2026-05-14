import json
import csv
import io
import os
import traceback
import threading
import webbrowser
from urllib.parse import parse_qs, urlparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime

from library_app.auth import (
    clear_password_reset_otp,
    create_password_reset_otp,
    create_session,
    is_authenticated,
    load_admin_credentials,
    mask_email,
    remove_session,
    save_admin_credentials,
    store_password_reset_otp,
    verify_admin_password,
    verify_password_reset_otp,
)
from library_app.config import (
    CAMERA_HTML_FILE,
    CSS_FILE,
    FAVICON_FILE,
    HOST,
    HTML_FILE,
    JS_FILE,
    LOGIN_CSS_FILE,
    LOGIN_HTML_FILE,
    LOGIN_JS_FILE,
    PORT,
    RECENT_VISITS_HTML_FILE,
    STUDENTS_INSIDE_HTML_FILE,
    WEEKLY_REPORT_HTML_FILE,
    ARYA_LOGO_FILE,
    ACE_LOGO_FILE,
)
from library_app.data_store import (
    build_dashboard_payload,
    build_daily_summary,
    build_weekly_summary,
    clear_visit_history,
    get_recent_visits,
    get_students_file,
    load_students,
    process_scan_result,
)
from library_app.mailer import send_password_recovery_email
from library_app.time_utils import today_local
from library_app.utils import read_text_file


class LibraryDashboardHandler(BaseHTTPRequestHandler):
    def _path_name(self):
        return urlparse(self.path).path

    def _query_params(self):
        return parse_qs(urlparse(self.path).query)

    def _parse_cookies(self):
        cookies = {}
        raw_cookie = self.headers.get("Cookie", "")
        for chunk in raw_cookie.split(";"):
            if "=" not in chunk:
                continue
            key, value = chunk.strip().split("=", 1)
            cookies[key] = value
        return cookies

    def _is_authenticated(self):
        session_id = self._parse_cookies().get("library_session")
        return is_authenticated(session_id)

    def _json_response(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html_response(self, html):
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text_response(self, content, content_type):
        body = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def _set_session_cookie(self, session_id):
        self.send_header("Set-Cookie", f"library_session={session_id}; HttpOnly; Path=/; SameSite=Lax")

    def _clear_session_cookie(self):
        self.send_header("Set-Cookie", "library_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax")

    def do_GET(self):
        try:
            self._do_get()
        except Exception as error:
            traceback.print_exc()
            try:
                self._json_response({"ok": False, "message": f"Server error: {error}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:
                return

    def _do_get(self):
        path = self._path_name()

        if path in ("/", "/login", "/login.html"):
            if self._is_authenticated():
                self._redirect("/admin")
                return
            self._html_response(read_text_file(LOGIN_HTML_FILE))
            return

        if path in ("/admin", "/admin/"):
            if not self._is_authenticated():
                self._redirect("/")
                return
            self._html_response(read_text_file(HTML_FILE))
            return

        if path in ("/camera", "/camera/", "/admin/camera"):
            if not self._is_authenticated():
                self._redirect("/")
                return
            self._html_response(read_text_file(CAMERA_HTML_FILE))
            return

        if path in ("/recent-visits", "/recent-visits/"):
            if not self._is_authenticated():
                self._redirect("/")
                return
            self._html_response(read_text_file(RECENT_VISITS_HTML_FILE))
            return

        if path in ("/students-inside", "/students-inside/"):
            if not self._is_authenticated():
                self._redirect("/")
                return
            self._html_response(read_text_file(STUDENTS_INSIDE_HTML_FILE))
            return

        if path in ("/weekly-report", "/weekly-report/"):
            if not self._is_authenticated():
                self._redirect("/")
                return
            self._html_response(read_text_file(WEEKLY_REPORT_HTML_FILE))
            return

        if path == "/static/styles.css":
            self._text_response(read_text_file(CSS_FILE), "text/css")
            return

        if path == "/static/app.js":
            self._text_response(read_text_file(JS_FILE), "application/javascript")
            return

        if path == "/static/login.css":
            self._text_response(read_text_file(LOGIN_CSS_FILE), "text/css")
            return

        if path == "/static/login.js":
            self._text_response(read_text_file(LOGIN_JS_FILE), "application/javascript")
            return

        if path == "/static/favicon.svg":
            self._text_response(read_text_file(FAVICON_FILE), "image/svg+xml")
            return

        if path == "/static/arya_logo.svg":
            self._text_response(read_text_file(ARYA_LOGO_FILE), "image/svg+xml")
            return

        if path == "/static/ace_logo.jpeg":
            body = ACE_LOGO_FILE.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/dashboard":
            if not self._is_authenticated():
                self._json_response({"ok": False, "message": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return
            payload = build_dashboard_payload(recent_limit=12)
            payload["student_file"] = get_students_file().name
            self._json_response(payload)
            return

        if path == "/api/daily-summary":
            if not self._is_authenticated():
                self._json_response({"ok": False, "message": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return

            self._json_response({"summary": build_daily_summary(get_recent_visits(limit=None))})
            return

        if path == "/api/export-visits":
            if not self._is_authenticated():
                self._json_response({"ok": False, "message": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return

            students = load_students()
            visits = get_recent_visits(limit=None)
            week_filter = self._query_params().get("week", [""])[0].strip()
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(
                [
                    "visit_id",
                    "student_id",
                    "name",
                    "father_name",
                    "branch",
                    "date",
                    "entry_time",
                    "exit_time",
                ]
            )
            for visit in reversed(visits):
                if week_filter:
                    visit_date = datetime.strptime(visit["date"], "%Y-%m-%d").date()
                    iso_year, iso_week, _ = visit_date.isocalendar()
                    visit_week = f"{iso_year}-W{iso_week:02d}"
                    if visit_week != week_filter:
                        continue
                student = students.get(visit["student_id"], {})
                writer.writerow(
                    [
                        visit["visit_id"],
                        visit["student_id"],
                        visit["name"],
                        student.get("father_name", visit.get("father_name", "")),
                        student.get("course", visit.get("course", "")),
                        visit["date"],
                        visit["entry_time"],
                        visit["exit_time"],
                    ]
                )

            body = buffer.getvalue().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            filename = "library_visits_report.csv" if not week_filter else f"library_visits_{week_filter}.csv"
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/weekly-summary":
            if not self._is_authenticated():
                self._json_response({"ok": False, "message": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return

            self._json_response({"summary": build_weekly_summary(get_recent_visits(limit=None), today=today_local())})
            return

        self._json_response({"ok": False, "message": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        try:
            self._do_post()
        except Exception as error:
            traceback.print_exc()
            try:
                self._json_response({"ok": False, "message": f"Server error: {error}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:
                return

    def _do_post(self):
        if self.path == "/api/login":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length or 0)
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json_response({"ok": False, "message": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
                return

            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", ""))
            credentials = load_admin_credentials()
            if username != credentials["username"] or not verify_admin_password(password, credentials):
                self._json_response({"ok": False, "message": "Invalid librarian credentials."}, status=HTTPStatus.UNAUTHORIZED)
                return

            session_id = create_session(username)
            body = json.dumps({"ok": True, "message": "Login successful."}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._set_session_cookie(session_id)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/logout":
            session_id = self._parse_cookies().get("library_session")
            remove_session(session_id)
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._clear_session_cookie()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/forgot-password":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length or 0)
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json_response({"ok": False, "message": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
                return

            credentials = load_admin_credentials()
            requested_username = str(payload.get("username", "")).strip()
            if requested_username != credentials["username"]:
                self._json_response({"ok": False, "message": "Username does not match the admin account."}, status=HTTPStatus.BAD_REQUEST)
                return
            admin_email = credentials.get("email", "")
            otp_code = create_password_reset_otp()
            ok, message = send_password_recovery_email(admin_email, requested_username, otp_code)
            if ok:
                store_password_reset_otp(requested_username, otp_code)
            self._json_response({"ok": ok, "message": message, "admin_email": mask_email(admin_email)}, status=HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST)
            return

        if self.path == "/api/reset-password":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length or 0)
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json_response({"ok": False, "message": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
                return

            credentials = load_admin_credentials()
            username = str(payload.get("username", "")).strip()
            otp = str(payload.get("otp", "")).strip()
            new_password = str(payload.get("new_password", ""))

            if username != credentials["username"]:
                self._json_response({"ok": False, "message": "Username does not match the admin account."}, status=HTTPStatus.BAD_REQUEST)
                return
            if len(new_password) < 6:
                self._json_response({"ok": False, "message": "New password must be at least 6 characters."}, status=HTTPStatus.BAD_REQUEST)
                return

            ok, message = verify_password_reset_otp(username, otp)
            if not ok:
                self._json_response({"ok": False, "message": message}, status=HTTPStatus.BAD_REQUEST)
                return

            save_admin_credentials(username, new_password, credentials.get("email", ""))
            clear_password_reset_otp(username)
            self._json_response({"ok": True, "message": "Password reset successful. Please log in with the new password."})
            return

        if self.path == "/api/clear-visits":
            if not self._is_authenticated():
                self._json_response({"ok": False, "message": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return
            clear_visit_history()
            self._json_response({"ok": True, "message": "All visit entries have been cleared."})
            return

        if self.path != "/api/scan":
            self._json_response({"ok": False, "message": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        if not self._is_authenticated():
            self._json_response({"ok": False, "message": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length or 0)

        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json_response({"ok": False, "message": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            return

        student_id = str(payload.get("student_id", "")).strip()
        if not student_id:
            self._json_response({"ok": False, "message": "Student ID is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        result = process_scan_result(student_id)
        self._json_response(result)

    def log_message(self, format, *args):
        return


def run_server():
    server = ThreadingHTTPServer((HOST, PORT), LibraryDashboardHandler)
    app_url = f"http://{HOST}:{PORT}"
    print(f"Library dashboard running at {app_url}")
    print("Press Ctrl+C to stop.")
    auto_open = os.environ.get("LIBRARY_AUTO_OPEN_BROWSER", "1").strip().lower()
    if auto_open not in {"0", "false", "no", "off"}:
        threading.Timer(1.0, lambda: webbrowser.open(app_url)).start()
    server.serve_forever()
