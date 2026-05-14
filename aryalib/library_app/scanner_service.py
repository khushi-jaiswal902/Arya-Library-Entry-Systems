import time

from library_app.config import COOLDOWN_SECONDS, VISITS_FILE, WINDOW_NAME
from library_app.data_store import ensure_students_file, ensure_visits_file, get_students_file, process_scan


def open_camera():
    import cv2

    for index in (0, 1, 2):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            return cap
        cap.release()
    return None


def run_scanner():
    import cv2
    from pyzbar.pyzbar import ZBarSymbol, decode

    ensure_students_file()
    ensure_visits_file()

    cap = open_camera()
    if cap is None:
        print("Camera not found. Close other camera apps and try again.")
        return

    last_scan_value = ""
    last_scan_time = 0.0
    status_text = "Barcode/QR ko camera ke saamne layein"
    status_color = (255, 0, 0)

    print("Library Management System started.")
    print(f"Student database: {get_students_file()}")
    print(f"Visit log: {VISITS_FILE}")
    print("Press 'q' to quit.")

    should_close_after_scan = False

    while True:
        success, frame = cap.read()
        if not success:
            status_text = "Camera frame read failed"
            status_color = (0, 0, 255)
            time.sleep(1)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detected_codes = decode(
            gray,
            symbols=[
                ZBarSymbol.CODE128,
                ZBarSymbol.CODE39,
                ZBarSymbol.EAN13,
                ZBarSymbol.EAN8,
                ZBarSymbol.QRCODE,
            ],
        )
        current_time = time.time()

        for code in detected_codes:
            barcode_value = code.data.decode("utf-8", errors="ignore").strip()
            print(f"Detected raw barcode: {barcode_value}")
            x, y, w, h = code.rect

            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                frame,
                barcode_value,
                (x, max(20, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            is_same_scan = (
                barcode_value == last_scan_value
                and current_time - last_scan_time < COOLDOWN_SECONDS
            )
            if not barcode_value or is_same_scan:
                continue

            last_scan_value = barcode_value
            last_scan_time = current_time

            ok, message = process_scan(barcode_value)
            print(message)
            status_text = message
            status_color = (0, 150, 0) if ok else (0, 0, 255)
            if ok:
                should_close_after_scan = True
            break

        cv2.putText(
            frame,
            status_text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2,
        )
        cv2.putText(
            frame,
            "Press q to close",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (80, 80, 80),
            2,
        )

        cv2.imshow(WINDOW_NAME, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        if should_close_after_scan:
            cv2.waitKey(1200)
            break

    cap.release()
    cv2.destroyAllWindows()
