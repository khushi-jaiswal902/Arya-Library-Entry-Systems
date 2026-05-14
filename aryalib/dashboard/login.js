const loginForm = document.getElementById("loginForm");
const loginFeedback = document.getElementById("loginFeedback");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const togglePasswordBtn = document.getElementById("togglePasswordBtn");

function setFeedback(message, type = "") {
  loginFeedback.textContent = message;
  loginFeedback.className = `feedback ${type}`.trim();
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    setFeedback("Enter both username and password.", "error");
    return;
  }

  setFeedback("Signing in...");

  const response = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json();
  if (!response.ok || !data.ok) {
    setFeedback(data.message || "Login failed.", "error");
    return;
  }

  setFeedback("Login successful. Opening admin panel...", "ok");
  window.location.href = "/admin";
});

if (togglePasswordBtn) {
  togglePasswordBtn.addEventListener("click", () => {
    const showing = passwordInput.type === "text";
    passwordInput.type = showing ? "password" : "text";
    togglePasswordBtn.textContent = showing ? "Show" : "Hide";
    togglePasswordBtn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    passwordInput.focus();
  });
}
