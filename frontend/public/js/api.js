// Shared helpers for the JASS TECHNOLOGIES storefront.
// All requests go through the dev-server proxy to FastAPI on /api/*.

const API_BASE = "/api";

const Auth = {
  get token() {
    return localStorage.getItem("jt_token") || "";
  },
  get username() {
    return localStorage.getItem("jt_username") || "";
  },
  get role() {
    return localStorage.getItem("jt_role") || "";
  },
  isLoggedIn() {
    return !!this.token;
  },
  isAdmin() {
    return this.role === "admin";
  },
  set(token, username, role) {
    localStorage.setItem("jt_token", token);
    localStorage.setItem("jt_username", username);
    localStorage.setItem("jt_role", role);
  },
  clear() {
    localStorage.removeItem("jt_token");
    localStorage.removeItem("jt_username");
    localStorage.removeItem("jt_role");
  },
};

async function api(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && Auth.token) headers["Authorization"] = `Bearer ${Auth.token}`;

  const res = await fetch(API_BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data;
  try {
    data = await res.json();
  } catch (e) {
    data = { success: false, message: `HTTP ${res.status}` };
  }
  if (!res.ok && !("success" in data)) {
    data = { success: false, message: data.detail || `Error ${res.status}` };
  }
  return data;
}

// ---------- Cart (localStorage) ----------
const Cart = {
  key: "jt_cart",
  get() {
    try {
      return JSON.parse(localStorage.getItem(this.key) || "[]");
    } catch {
      return [];
    }
  },
  save(items) {
    localStorage.setItem(this.key, JSON.stringify(items));
    this.refreshBadge();
  },
  add(product, qty = 1) {
    const items = this.get();
    const existing = items.find((i) => i.product_id === product.id);
    if (existing) {
      existing.quantity += qty;
    } else {
      items.push({
        product_id: product.id,
        name: product.name,
        price: product.price,
        image: product.image,
        category: product.category,
        quantity: qty,
      });
    }
    this.save(items);
  },
  setQty(productId, qty) {
    const items = this.get().map((i) =>
      i.product_id === productId ? { ...i, quantity: Math.max(1, qty) } : i
    );
    this.save(items);
  },
  remove(productId) {
    this.save(this.get().filter((i) => i.product_id !== productId));
  },
  clear() {
    this.save([]);
  },
  count() {
    return this.get().reduce((s, i) => s + i.quantity, 0);
  },
  subtotal() {
    return this.get().reduce((s, i) => s + i.price * i.quantity, 0);
  },
  refreshBadge() {
    document.querySelectorAll(".cart-badge").forEach((el) => {
      el.textContent = this.count();
    });
  },
};

// ---------- Page-level helpers ----------
function fmtINR(n) {
  return "₹" + Number(n || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });
}

function fmtDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

// Replace nav login link with username menu when logged in
function renderAuthNav() {
  const navLogin = document.querySelector(".nav-links a.btn-nav");
  if (!navLogin) return;
  if (Auth.isLoggedIn()) {
    const ul = navLogin.parentElement.parentElement;
    navLogin.parentElement.remove();

    const profileLi = document.createElement("li");
    profileLi.innerHTML = `<a href="profile.html">Hi, ${Auth.username}</a>`;
    ul.appendChild(profileLi);

    if (Auth.isAdmin()) {
      const adminLi = document.createElement("li");
      adminLi.innerHTML = `<a href="admin.html" class="btn-nav">Admin</a>`;
      ul.appendChild(adminLi);
    }

    const outLi = document.createElement("li");
    outLi.innerHTML = `<a href="#" id="logoutLink">Logout</a>`;
    ul.appendChild(outLi);
    document.getElementById("logoutLink").addEventListener("click", (e) => {
      e.preventDefault();
      Auth.clear();
      Cart.clear();
      window.location.href = "index.html";
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  Cart.refreshBadge();
  renderAuthNav();
});

window.JT = { api, Auth, Cart, fmtINR, fmtDate };
