
async function getCurrentUser() {
  try {
    const response = await fetch("/api/users/me", {
      method: "GET",
      credentials: "include"
    });

    if (!response.ok) {
      return null;
    }

    return await response.json();

  } catch (error) {
    console.error("Failed to get current user:", error);
    return null;
  }
}
async function logout() {
  try {
    await fetch("/api/logout", {
      method: "POST",
      credentials: "include"
    });
  } catch (error) {
    console.warn("Logout request failed:", error);
  }

  localStorage.removeItem("current_user_id");
  localStorage.removeItem("current_user_name");

  window.location.href = "login.html";
}
async function renderAuthChip(containerId) {

  const container = document.getElementById(containerId);

  if (!container) {
    return;
  }

  const user = await getCurrentUser();

  if (user) {

    const initial =
      (user.name || "Account")
        .trim()
        .charAt(0)
        .toUpperCase() || "U";

    container.innerHTML = `
      <div class="auth-chip-wrap" style="position:relative;">

        <button
          id="auth-chip-btn"
          style="
            display:flex;
            align-items:center;
            gap:8px;
            background:transparent;
            border:1px solid rgba(167,139,250,0.15);
            padding:6px 12px 6px 6px;
            border-radius:999px;
            cursor:pointer;
            font-family:inherit;
            color:#f5f3ff;
            font-size:13px;
          "
        >

          <span
            style="
              width:26px;
              height:26px;
              border-radius:50%;
              background:linear-gradient(135deg,#7c3aed,#4c1d95);
              display:flex;
              align-items:center;
              justify-content:center;
              font-weight:700;
              font-size:12px;
              color:#fff;
            "
          >
            ${initial}
          </span>

          ${user.name || "Account"}

        </button>

        <div
          id="auth-chip-menu"
          style="
            display:none;
            position:absolute;
            top:calc(100% + 8px);
            right:0;
            background:#111120;
            border:1px solid rgba(167,139,250,0.15);
            border-radius:10px;
            padding:6px;
            min-width:140px;
            box-shadow:0 20px 40px -12px rgba(0,0,0,0.6);
            z-index:50;
          "
        >

          <a
            href="preferences.html"
            style="
              display:block;
              padding:8px 10px;
              border-radius:6px;
              font-size:13px;
              color:#a1a1c2;
              text-decoration:none;
            "
          >
            Preferences
          </a>

          <button
            onclick="logout()"
            style="
              display:block;
              width:100%;
              text-align:left;
              padding:8px 10px;
              border-radius:6px;
              font-size:13px;
              color:#f87171;
              background:transparent;
              border:none;
              cursor:pointer;
              font-family:inherit;
            "
          >
            Log Out
          </button>

        </div>

      </div>
    `;

    const btn =
      document.getElementById("auth-chip-btn");

    const menu =
      document.getElementById("auth-chip-menu");

    btn.addEventListener("click", () => {

      menu.style.display =
        menu.style.display === "none"
          ? "block"
          : "none";

    });

    document.addEventListener("click", (event) => {

      if (!container.contains(event.target)) {
        menu.style.display = "none";
      }

    });

  } else {

    container.innerHTML = `
      <a
        href="login.html"
        style="
          font-size:14px;
          color:#a1a1c2;
          text-decoration:none;
        "
      >
        Log In
      </a>
    `;

  }
}