const state = {
  orders: [],
  printers: [],
  selectedPrinter: "",
};

const el = (id) => document.getElementById(id);

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function renderService(ok) {
  el("serviceStatus").textContent = ok ? "Activo" : "Sin conexión";
  el("serviceDot").className = `status-dot ${ok ? "ok" : "bad"}`;
}

function renderPrinters() {
  const select = el("printerSelect");
  select.innerHTML = "";
  state.printers.forEach((printer) => {
    const option = document.createElement("option");
    option.value = printer.name;
    option.textContent = printer.name;
    if (printer.name === state.selectedPrinter) option.selected = true;
    select.appendChild(option);
  });
  el("selectedPrinter").textContent = state.selectedPrinter || "-";
}

function orderStatusClass(status) {
  if (status === "printed") return "badge";
  if (status === "done") return "badge";
  if (status === "cancelled") return "badge";
  return "badge";
}

function renderOrders() {
  const grid = el("ordersGrid");
  el("orderCount").textContent = String(state.orders.length);
  grid.innerHTML = "";
  if (!state.orders.length) {
    grid.innerHTML = '<p class="muted">No hay órdenes para mostrar.</p>';
    return;
  }

  state.orders.forEach((order) => {
    const card = document.createElement("article");
    card.className = "order-card";
    card.innerHTML = `
      <div class="order-top">
        <div>
          <strong>${order.reference}</strong>
          <div class="meta">${order.customer_name || "-"} · ${order.currency} ${Number(order.total || 0).toFixed(2)}</div>
        </div>
        <span class="${orderStatusClass(order.status)}">${order.status}</span>
      </div>
      <div class="meta">
        <div>Creada: ${formatDate(order.created_at)}</div>
        <div>Actualizada: ${formatDate(order.updated_at)}</div>
        <div>Pago: ${order.payment_method || "-"} · ${order.payment_status || "-"}</div>
        <div>Entrega: ${order.fulfillment_method || "-"}</div>
        <div>Items: ${order.items?.length || 0}</div>
      </div>
      <div class="order-actions">
        <button data-action="reprint" data-id="${order.id}" class="secondary">Reimprimir</button>
      </div>
    `;
    grid.appendChild(card);
  });
}

async function loadHealth() {
  try {
    await api("/api/health");
    renderService(true);
  } catch {
    renderService(false);
  }
}

async function loadPrinters() {
  const data = await api("/api/orders/printers");
  state.printers = data.printers || [];
  state.selectedPrinter = data.selected_printer || data.default_printer || "";
  renderPrinters();
}

async function loadOrders() {
  const data = await api("/api/orders");
  state.orders = data.orders || [];
  el("lastSync").textContent = new Date().toLocaleTimeString();
  renderOrders();
}

async function syncNow() {
  el("syncNowBtn").disabled = true;
  try {
    await api("/api/sync/goodbarber", { method: "POST", body: "{}" });
    await Promise.all([loadOrders(), loadHealth()]);
  } finally {
    el("syncNowBtn").disabled = false;
  }
}

async function savePrinter() {
  const printerName = el("printerSelect").value;
  await api("/api/orders/printers/select", {
    method: "POST",
    body: JSON.stringify({ printer_name: printerName }),
  });
  state.selectedPrinter = printerName;
  renderPrinters();
}

async function testPrinter() {
  await api("/api/orders/printers/test", {
    method: "POST",
    body: JSON.stringify({ printer_name: el("printerSelect").value }),
  });
}

async function reprintOrder(orderId) {
  await api(`/api/orders/${orderId}/print`, { method: "POST", body: "{}" });
  await loadOrders();
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;

  try {
    if (button.id === "syncNowBtn") return syncNow();
    if (button.id === "refreshBtn") return Promise.all([loadHealth(), loadPrinters(), loadOrders()]);
    if (button.id === "savePrinterBtn") return savePrinter();
    if (button.id === "testPrinterBtn") return testPrinter();
    if (button.dataset.action === "reprint") return reprintOrder(button.dataset.id);
  } catch (error) {
    alert(`Error: ${error.message}`);
  }
});

document.addEventListener("DOMContentLoaded", async () => {
  await Promise.all([loadHealth(), loadPrinters(), loadOrders()]);
});
