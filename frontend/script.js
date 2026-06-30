const API_BASE = "http://127.0.0.1:5000";

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem("smartpantry_user") || "null");
  } catch {
    return null;
  }
}

function setCurrentUser(user) {
  localStorage.setItem("smartpantry_user", JSON.stringify(user));
}

function logout() {
  localStorage.removeItem("smartpantry_user");
  localStorage.removeItem("smartpantry_selected_receipt");
  window.location.href = "login.html";
}

async function registerUser() {
  const username = document.getElementById("regUsername").value.trim();
  const email = document.getElementById("regEmail").value.trim();
  const phone = document.getElementById("regPhone").value.trim();
  const password = document.getElementById("regPassword").value;
  const msg = document.getElementById("registerMsg");

  msg.textContent = "Creating account...";

  try {
    const res = await fetch(`${API_BASE}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, phone, password })
    });

    const data = await res.json();

    if (!res.ok) {
      msg.textContent = data.error || "Registration failed";
      return;
    }

    setCurrentUser(data.user);
    window.location.href = "dashboard.html";
  } catch (err) {
    msg.textContent = "Server error";
    console.error(err);
  }
}

async function loginUser() {
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  const msg = document.getElementById("loginMsg");

  msg.textContent = "Logging in...";

  try {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      msg.textContent = data.error || "Login failed";
      return;
    }

    setCurrentUser(data.user);
    window.location.href = "dashboard.html";
  } catch (err) {
    msg.textContent = "Server error";
    console.error(err);
  }
}

async function initDashboard() {
  const user = getCurrentUser();
  if (!user) {
    window.location.href = "login.html";
    return;
  }

  document.getElementById("topUsername").textContent = user.username || "User";
  document.getElementById("topUserEmail").textContent = user.email || "";
  document.getElementById("topUserPhone").textContent = user.phone || "";
  await loadHistory();
}

async function uploadReceipt() {
  const user = getCurrentUser();
  if (!user) {
    window.location.href = "login.html";
    return;
  }

  const input = document.getElementById("receiptInput");
  const dashboard = document.getElementById("dashboard");
  const receiptSummary = document.getElementById("receiptSummary");

  if (!input.files.length) {
    alert("Please select a receipt image.");
    return;
  }

  const formData = new FormData();
  formData.append("receipt", input.files[0]);
  formData.append("email", user.email);
  formData.append("phone", user.phone || "");

  dashboard.innerHTML = "<div class='empty-state'>Processing receipt...</div>";

  try {
    const response = await fetch(`${API_BASE}/upload-receipt`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (data.error) {
      dashboard.innerHTML = `<div class='empty-state'>Error: ${data.error}</div>`;
      return;
    }

    const receipt = data.receipt || {};
    const items = data.items || [];
    const warning = data.receipt_warning || "";

    receiptSummary.innerHTML = `
      <div class="summary-box"><p class="label">Store</p><p class="value">${receipt.store_name || "Not found"}</p></div>
      <div class="summary-box"><p class="label">Address</p><p class="value">${receipt.store_address || "Not found"}</p></div>
      <div class="summary-box"><p class="label">Date</p><p class="value">${receipt.purchase_date || "Not found"}</p></div>
      <div class="summary-box"><p class="label">Total</p><p class="value">${receipt.receipt_total || "Not found"}</p></div>
      <div class="summary-box"><p class="label">Payment</p><p class="value">${receipt.payment_method || "Not found"}</p></div>
    `;

    let html = "";

    if (warning) {
      html += `<div class="old-receipt-warning">${warning}</div>`;
    }

    if (items.length > 0) {
      html += items.map(product => {
        // Map backend configuration tags to badge styles
        let badgeColorClass = "badge-green";
        if (product.color_tag === "red") badgeColorClass = "badge-red";
        if (product.color_tag === "yellow") badgeColorClass = "badge-yellow";

        return `
          <div class="product-card">
            <div class="status-badge ${badgeColorClass}">${product.risk_label || "Unknown"}</div>
            <h3>${product.name || "Unknown item"}</h3>
            <p><b>Brand:</b> ${product.brand || "Generic"}</p>
            <p><b>Price:</b> ${product.price || "Not found"}</p>
            <p><b>Estimated Shelf Life:</b> ${product.estimated_shelf_life || "Not found"}</p>
            ${
              product.hide_expiry
                ? `<p><b>Expiry:</b> Not shown for old receipt</p>`
                : `<p><b>Estimated Expiry:</b> ${product.estimated_expiry_start || "Not found"} to ${product.estimated_expiry_end || "Not found"} <small>(estimated)</small></p>`
            }
            <p><b>Storage:</b> ${product.storage || "Not found"}</p>
            <p><b>Nutrition Value:</b> ${product.nutrition_value || "N/A"}</p>
            <p><b>Confidence:</b> ${product.confidence ? Math.round(product.confidence * 100) + "%" : "N/A"}</p>
          </div>
        `;
      }).join("");
    } else {
      html += "<div class='empty-state'>No items detected.</div>";
    }

    dashboard.innerHTML = html;
    await loadHistory();
  } catch (error) {
    dashboard.innerHTML = "<div class='empty-state'>Error connecting to backend.</div>";
    console.error(error);
  }
}

async function loadHistory() {
  const user = getCurrentUser();
  const historyList = document.getElementById("historyList");
  if (!user || !historyList) return;

  try {
    const res = await fetch(`${API_BASE}/history?email=${encodeURIComponent(user.email)}`);
    const data = await res.json();

    if (!res.ok) {
      historyList.innerHTML = "<div class='empty-state'>Unable to load history.</div>";
      return;
    }

    const history = data.history || [];

    if (history.length === 0) {
      historyList.innerHTML = "<div class='empty-state'>No history yet.</div>";
      return;
    }

    historyList.innerHTML = history.map((receipt, index) => {
      // Safely capture the exact target database ID identifier string
      const rId = receipt._id || receipt.id || index;
      
      return `
        <div class="product-card" style="margin-bottom:14px;">
          <h3 style="margin-bottom:6px;">${receipt.store_name || "Unknown store"}</h3>
          <p><b>Date:</b> ${receipt.purchase_date || "Not found"}</p>
          <p><b>Total:</b> ${receipt.receipt_total || "Not found"}</p>
          <p><b>Payment:</b> ${receipt.payment_method || "Not found"}</p>
          <p><b>Items:</b> ${(receipt.items || []).map(i => i.name).filter(Boolean).join(", ") || "None"}</p>
          <div style="margin-top:10px; display: flex; gap: 8px;">
            <button onclick="openReceiptByIndex(${index})">View Receipt</button>
            <button style="background-color: #dc2626; color: white; border-color: #b91c1c;" onclick="deleteReceipt('${rId}', '${receipt.store_name || "this store"}')">Delete</button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    historyList.innerHTML = "<div class='empty-state'>Unable to load history.</div>";
    console.error(err);
  }
}
async function deleteReceipt(receiptId, storeName) {
  const user = getCurrentUser();
  if (!user) return;

  const confirmed = await appConfirm({
    title: "Delete receipt?",
    message: `Are you sure you want to delete the receipt from <b>${storeName}</b>? This can't be undone.`,
    confirmText: "Delete",
    cancelText: "Cancel",
    danger: true
  });
  if (!confirmed) return;

  try {
    const res = await fetch(`${API_BASE}/receipt/${receiptId}?email=${encodeURIComponent(user.email)}`, {
      method: "DELETE"
    });

    const data = await res.json();

    if (!res.ok) {
      await appAlert({ title: "Couldn't delete", message: data.error || "Failed to delete receipt", success: false });
      return;
    }

    await appAlert({ title: "Receipt deleted", message: "It's been removed from your history.", success: true });
    await loadHistory();
  } catch (err) {
    console.error("Delete sequence communication failure:", err);
    await appAlert({ title: "Connection error", message: "Couldn't reach the server to delete this receipt.", success: false });
  }
}

async function openReceiptByIndex(index) {
  const user = getCurrentUser();
  if (!user) {
    window.location.href = "login.html";
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/history?email=${encodeURIComponent(user.email)}`);
    const data = await res.json();

    if (!res.ok) {
      alert(data.error || "Unable to load receipt");
      return;
    }

    const receipt = (data.history || [])[index];
    if (!receipt) {
      alert("Receipt not found.");
      return;
    }

    localStorage.setItem("smartpantry_selected_receipt", JSON.stringify(receipt));
    window.location.href = "receipt.html";
  } catch (err) {
    console.error(err);
    alert("Unable to open receipt.");
  }
}

function goBackToDashboard() {
  window.location.href = "dashboard.html";
}

async function initReceiptPage() {
  const user = getCurrentUser();
  if (!user) {
    window.location.href = "login.html";
    return;
  }

  const saved = localStorage.getItem("smartpantry_selected_receipt");

  if (!saved) {
    document.getElementById("receiptMeta").textContent =
      "Receipt not selected. Go back and click View Receipt.";
    document.getElementById("receiptItems").innerHTML =
      "<div class='empty-state'>No receipt selected.</div>";
    return;
  }

  const receipt = JSON.parse(saved);
  const items = receipt.items || [];

  document.getElementById("receiptMeta").textContent =
    `${receipt.store_name || "Unknown store"} • ${receipt.purchase_date || "Date not found"}`;

  document.getElementById("receiptSummary").innerHTML = `
    <div class="summary-box"><p class="label">Store</p><p class="value">${receipt.store_name || "Not found"}</p></div>
    <div class="summary-box"><p class="label">Address</p><p class="value">${receipt.store_address || "Not found"}</p></div>
    <div class="summary-box"><p class="label">Date</p><p class="value">${receipt.purchase_date || "Not found"}</p></div>
    <div class="summary-box"><p class="label">Total</p><p class="value">${receipt.receipt_total || "Not found"}</p></div>
    <div class="summary-box"><p class="label">Payment</p><p class="value">${receipt.payment_method || "Not found"}</p></div>
  `;

  const itemsBox = document.getElementById("receiptItems");

  if (!items.length) {
    itemsBox.innerHTML = "<div class='empty-state'>No items saved for this receipt.</div>";
    return;
  }

  itemsBox.innerHTML = items.map(item => {
    // Map backend configuration tags to badge styles for the static selection summary
    let badgeColorClass = "badge-green";
    if (item.color_tag === "red") badgeColorClass = "badge-red";
    if (item.color_tag === "yellow") badgeColorClass = "badge-yellow";

    return `
      <div class="product-card">
        <div class="status-badge ${badgeColorClass}">${item.risk_label || "Unknown"}</div>
        <h3>${item.name || "Unknown item"}</h3>
        <p><b>Brand:</b> ${item.brand || "Generic"}</p>
        <p><b>Price:</b> ${item.price || "Not found"}</p>
        <p><b>Category:</b> ${item.category || "Unknown"}</p>
        <p><b>Estimated Shelf Life:</b> ${item.estimated_shelf_life || "Not found"}</p>
        <p><b>Estimated Expiry:</b> ${item.estimated_expiry_start || "Not found"} to ${item.estimated_expiry_end || "Not found"}</p>
        <p><b>Storage:</b> ${item.storage || "Not found"}</p>
        <p><b>Nutrition Value:</b> ${item.nutrition_value || "N/A"}</p>
      </div>
    `;
  }).join("");
}