const statsRoot = document.getElementById("stats");
const recentRows = document.getElementById("recentRows");
const insideList = document.getElementById("insideList");
const dailySummaryRows = document.getElementById("dailySummaryRows");
const weeklySummaryRows = document.getElementById("weeklySummaryRows");
const feedback = document.getElementById("feedback");
const scanForm = document.getElementById("scanForm");
const studentIdInput = document.getElementById("studentId");
const refreshBtn = document.getElementById("refreshBtn");
const startCameraBtn = document.getElementById("startCameraBtn");
const stopCameraBtn = document.getElementById("stopCameraBtn");
const cameraShell = document.getElementById("cameraShell");
const cameraVideo = document.getElementById("cameraVideo");
const cameraNote = document.getElementById("cameraNote");
const resultCard = document.getElementById("resultCard");
const resultAction = document.getElementById("resultAction");
const resultName = document.getElementById("resultName");
const resultStudentId = document.getElementById("resultStudentId");
const resultFatherName = document.getElementById("resultFatherName");
const resultPhone = document.getElementById("resultPhone");
const resultCourse = document.getElementById("resultCourse");
const resultDate = document.getElementById("resultDate");
const resultEntry = document.getElementById("resultEntry");
const resultExit = document.getElementById("resultExit");
const logoutBtn = document.getElementById("logoutBtn");
const downloadVisitsBtn = document.getElementById("downloadVisitsBtn");
const clearVisitsBtn = document.getElementById("clearVisitsBtn");
const backTopButtons = document.querySelectorAll('[data-back-top="true"]');
const backAdminButtons = document.querySelectorAll('[data-back-admin="true"]');
const DASHBOARD_CACHE_KEY = "arya-library-dashboard-cache-v1";

let cameraStream = null;
let detector = null;
let scanLoopId = null;
let cameraBusy = false;
let lastDetectedValue = "";
let lastDetectedAt = 0;
let zxingReader = null;

function setText(element, value, fallback = "-") {
  if (element) {
    element.textContent = value || fallback;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderStats(summary) {
  if (!statsRoot) {
    return;
  }
  const cards = [
    ["Students", summary.student_count],
    ["Total Visits", summary.total_visits],
    ["Today's Visits", summary.today_visits],
    ["Inside Now", summary.inside_count],
  ];
  statsRoot.innerHTML = cards.map(([label, value]) => `
    <article class="stat-card">
      <div class="stat-label">${escapeHtml(label)}</div>
      <div class="stat-value">${escapeHtml(value)}</div>
    </article>
  `).join("");
}

function renderRecent(visits) {
  if (!recentRows) {
    return;
  }
  if (!visits.length) {
    recentRows.innerHTML = `<tr><td colspan="7">No visits for today yet.</td></tr>`;
    return;
  }

  recentRows.innerHTML = visits.map((visit) => `
    <tr>
      <td>${escapeHtml(visit.student_id)}</td>
      <td>${escapeHtml(visit.name)}</td>
      <td>${escapeHtml(visit.father_name || "-")}</td>
      <td>${escapeHtml(visit.course || "-")}</td>
      <td>${escapeHtml(visit.date)}</td>
      <td>${escapeHtml(visit.entry_time)}</td>
      <td>${escapeHtml(visit.exit_time || "Inside")}</td>
    </tr>
  `).join("");
}

function renderInside(visits) {
  if (!insideList) {
    return;
  }
  if (!visits.length) {
    insideList.innerHTML = `<div class="student-card"><p class="student-name">No active entries</p><div class="panel-note">All scanned students are currently checked out.</div></div>`;
    return;
  }

  insideList.innerHTML = visits.map((visit) => `
    <article class="student-card">
      <p class="student-name">${escapeHtml(visit.name)}</p>
      <div class="panel-note">Code ${escapeHtml(visit.student_id)}</div>
      <div class="meta">
        <span>Father ${escapeHtml(visit.father_name || "-")}</span>
        <span>Branch ${escapeHtml(visit.course || "-")}</span>
        <span>Date ${escapeHtml(visit.date)}</span>
        <span>Entry ${escapeHtml(visit.entry_time)}</span>
      </div>
    </article>
  `).join("");
}

function renderDailySummary(rows) {
  if (!dailySummaryRows) {
    return;
  }
  if (!rows.length) {
    dailySummaryRows.innerHTML = `<tr><td colspan="4">No daily report data yet.</td></tr>`;
    return;
  }

  dailySummaryRows.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.date)}</td>
      <td>${escapeHtml(row.total_visits)}</td>
      <td>${escapeHtml(row.completed_visits)}</td>
      <td>${escapeHtml(row.inside_count)}</td>
    </tr>
  `).join("");
}

function renderWeeklySummary(rows) {
  if (!weeklySummaryRows) {
    return;
  }
  if (!rows.length) {
    weeklySummaryRows.innerHTML = `<tr><td colspan="7">No completed weekly files yet.</td></tr>`;
    return;
  }

  weeklySummaryRows.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.week_label)}</td>
      <td>${escapeHtml(row.start_date)}</td>
      <td>${escapeHtml(row.end_date)}</td>
      <td>${escapeHtml(row.total_visits)}</td>
      <td>${escapeHtml(row.completed_visits)}</td>
      <td>${escapeHtml(row.inside_count)}</td>
      <td><button class="ghost-button small-button weekly-download-btn" data-week="${escapeHtml(row.week_label)}">Download File</button></td>
    </tr>
  `).join("");

  document.querySelectorAll(".weekly-download-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const week = button.getAttribute("data-week");
      if (week) {
        window.location.href = `/api/export-visits?week=${encodeURIComponent(week)}`;
      }
    });
  });
}

function setFeedback(message, type = "") {
  if (!feedback) {
    return;
  }
  feedback.textContent = message;
  feedback.className = `feedback ${type}`.trim();
}

function renderDashboardData(data) {
  if (!data) {
    return;
  }
  renderStats(data.summary || {});
  renderRecent(data.recent_visits_with_students || data.recent_visits || []);
  renderInside(data.active_visits || []);
  renderDailySummary(data.daily_summary || []);
  renderWeeklySummary(data.weekly_summary || []);
}

function readDashboardCache() {
  try {
    const raw = window.sessionStorage.getItem(DASHBOARD_CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    return null;
  }
}

function writeDashboardCache(data) {
  try {
    window.sessionStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(data));
  } catch (error) {
  }
}

async function loadDashboard() {
  const response = await fetch("/api/dashboard");
  if (response.status === 401) {
    window.location.href = "/";
    return;
  }
  const data = await response.json();
  writeDashboardCache(data);
  renderDashboardData(data);
}

async function submitScan(studentId) {
  const response = await fetch("/api/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId }),
  });
  if (response.status === 401) {
    window.location.href = "/";
    return { ok: false, message: "Session expired. Please log in again." };
  }
  return response.json();
}

function renderResultCard(result) {
  if (!resultCard) {
    return;
  }

  if (!result || !result.student) {
    resultCard.classList.add("hidden");
    return;
  }

  resultCard.classList.remove("hidden");
  setText(
    resultAction,
    result.action === "entry"
      ? "Entry Recorded"
      : result.action === "exit"
        ? "Exit Recorded"
        : result.action === "duplicate"
          ? "Duplicate Scan Blocked"
          : "Latest Scan",
    "Latest Scan"
  );
  setText(resultName, result.student.name, "Unknown Student");
  setText(resultStudentId, result.student.student_id);
  setText(resultFatherName, result.student.father_name);
  setText(resultPhone, result.student.phone);
  setText(resultCourse, result.student.course);
  setText(resultDate, result.visit?.date);
  setText(resultEntry, result.visit?.entry_time);
  setText(resultExit, result.visit?.exit_time || (result.action === "entry" ? "Inside" : "-"));
}

async function stopCameraScan() {
  if (scanLoopId) {
    cancelAnimationFrame(scanLoopId);
    scanLoopId = null;
  }

  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }

  if (zxingReader && typeof zxingReader.stopContinuousDecode === "function") {
    try {
      zxingReader.stopContinuousDecode();
    } catch (error) {
    }
  }

  if (cameraVideo) {
    cameraVideo.srcObject = null;
  }
  if (cameraShell) {
    cameraShell.classList.add("hidden");
  }
  cameraBusy = false;
  lastDetectedValue = "";
  lastDetectedAt = 0;
  if (cameraNote) {
    cameraNote.textContent = "Camera ready. Hold the barcode clearly inside the frame.";
  }
}

async function detectFrame() {
  if (!detector || !cameraVideo.srcObject || cameraBusy) {
    scanLoopId = requestAnimationFrame(detectFrame);
    return;
  }

  try {
    const barcodes = await detector.detect(cameraVideo);
    if (barcodes.length) {
      const rawValue = (barcodes[0].rawValue || "").trim();
      if (rawValue) {
        await handleDetectedValue(rawValue);
        return;
      }
    }
  } catch (error) {
    setFeedback("Camera barcode detection failed.", "error");
    cameraNote.textContent = "Barcode could not be detected. Adjust the angle and improve lighting.";
  }

  scanLoopId = requestAnimationFrame(detectFrame);
}

async function handleDetectedValue(rawValue) {
  const now = Date.now();
  if (rawValue === lastDetectedValue && now - lastDetectedAt < 2500) {
    return;
  }

  lastDetectedValue = rawValue;
  lastDetectedAt = now;
  cameraBusy = true;
  cameraNote.textContent = `Detected: ${rawValue}`;
  setFeedback(`Detected barcode: ${rawValue}. Saving scan...`, "");
  const data = await submitScan(rawValue);
  renderResultCard(data);

  if (data.ok) {
    setFeedback(data.message, "ok");
    await loadDashboard();
    await stopCameraScan();
  } else {
    setFeedback(data.message, "error");
    cameraNote.textContent = data.message;
    cameraBusy = false;
  }
}

async function startZxingFallback() {
  if (!window.ZXingBrowser || !window.ZXingBrowser.BrowserMultiFormatReader) {
    setFeedback("Camera barcode scanning is not supported here. Please use manual scan input.", "error");
    return;
  }

  try {
    zxingReader = new window.ZXingBrowser.BrowserMultiFormatReader();
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "environment",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });

    if (!cameraVideo || !cameraShell || !cameraNote) {
      setFeedback("Camera UI is not available on this page.", "error");
      return;
    }

    cameraVideo.srcObject = cameraStream;
    cameraShell.classList.remove("hidden");
    cameraBusy = false;
    cameraNote.textContent = "Fallback scanner is active. Hold the barcode straight inside the frame.";
    setFeedback("Fallback camera scanner started.", "");
    await cameraVideo.play();

    zxingReader.decodeFromVideoElementContinuously(cameraVideo, async (result, error) => {
      if (cameraBusy) {
        return;
      }
      if (result?.getText) {
        await handleDetectedValue(result.getText().trim());
      }
    });
  } catch (error) {
    setFeedback("Fallback camera scanner could not start. Please allow camera access.", "error");
  }
}

async function startCameraScan() {
  if (!("mediaDevices" in navigator) || !navigator.mediaDevices.getUserMedia) {
    setFeedback("Camera access is not available in this browser.", "error");
    return;
  }

  if (!("BarcodeDetector" in window)) {
    await startZxingFallback();
    return;
  }

  try {
    try {
      const formats = await window.BarcodeDetector.getSupportedFormats();
      detector = new window.BarcodeDetector({
        formats: formats.filter((format) =>
          ["code_128", "code_39", "code_93", "codabar", "ean_13", "ean_8", "qr_code", "upc_a", "upc_e"].includes(format)
        ),
      });
    } catch (error) {
      detector = new window.BarcodeDetector();
    }

    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "environment",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });

    if (!cameraVideo || !cameraShell || !cameraNote) {
      setFeedback("Camera UI is not available on this page.", "error");
      return;
    }

    cameraVideo.srcObject = cameraStream;
    cameraShell.classList.remove("hidden");
    cameraBusy = false;
    cameraNote.textContent = "Camera is ready. Hold the barcode straight inside the frame.";
    setFeedback("Camera started. Place the barcode inside the scan area.", "");
    lastDetectedValue = "";
    lastDetectedAt = 0;
    scanLoopId = requestAnimationFrame(detectFrame);
  } catch (error) {
    await startZxingFallback();
  }
}

if (scanForm) {
  scanForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const studentId = studentIdInput.value.trim();
    if (!studentId) {
      setFeedback("Please enter or scan a student ID.", "error");
      studentIdInput.focus();
      return;
    }

    setFeedback("Saving scan...", "");
    const data = await submitScan(studentId);
    renderResultCard(data);

    if (data.ok) {
      setFeedback(data.message, "ok");
      studentIdInput.value = "";
      await loadDashboard();
    } else {
      setFeedback(data.message, "error");
    }

    studentIdInput.focus();
  });
}

if (refreshBtn) {
  refreshBtn.addEventListener("click", async () => {
    setFeedback("Refreshing dashboard...", "");
    await loadDashboard();
    setFeedback("Dashboard refreshed.", "ok");
    if (studentIdInput) {
      studentIdInput.focus();
    }
  });
}

if (startCameraBtn) {
  startCameraBtn.addEventListener("click", async () => {
    await startCameraScan();
  });
}

if (stopCameraBtn) {
  stopCameraBtn.addEventListener("click", async () => {
    await stopCameraScan();
    setFeedback("Camera stopped.", "");
    if (studentIdInput) {
      studentIdInput.focus();
    }
  });
}

if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/";
  });
}

if (downloadVisitsBtn) {
  downloadVisitsBtn.addEventListener("click", () => {
    window.location.href = "/api/export-visits";
  });
}

if (clearVisitsBtn) {
  clearVisitsBtn.addEventListener("click", async () => {
    const confirmed = window.confirm("Clear all entry and exit records? Student data will stay saved.");
    if (!confirmed) {
      return;
    }

    setFeedback("Clearing visit entries...", "");
    const response = await fetch("/api/clear-visits", { method: "POST" });
    if (response.status === 401) {
      window.location.href = "/";
      return;
    }

    const data = await response.json();
    if (!response.ok || !data.ok) {
      setFeedback(data.message || "Could not clear entries.", "error");
      return;
    }

    window.sessionStorage.removeItem(DASHBOARD_CACHE_KEY);
    await loadDashboard();
    setFeedback(data.message, "ok");
  });
}

if (backTopButtons.length) {
  backTopButtons.forEach((button) => {
    button.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

if (backAdminButtons.length) {
  backAdminButtons.forEach((button) => {
    button.addEventListener("click", () => {
      window.location.href = "/admin";
    });
  });
}

const cachedDashboard = readDashboardCache();
if (cachedDashboard) {
  renderDashboardData(cachedDashboard);
}

loadDashboard().then(() => {
  setFeedback("Dashboard ready. Scan box focused for next student.", "ok");
  if (studentIdInput) {
    studentIdInput.focus();
  }
}).catch(() => {
  if (cachedDashboard) {
    setFeedback("Showing cached dashboard data while live refresh failed.", "error");
    return;
  }
  setFeedback("Dashboard load failed. Please restart the web server.", "error");
});
