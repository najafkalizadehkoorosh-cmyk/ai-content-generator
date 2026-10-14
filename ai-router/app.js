"use strict";

const $ = (selector) => document.querySelector(selector);
const Core = window.AIRouterCore;

const state = {
  plan: null,
  approved: false,
  runId: 0,
  timer: null,
  backendAvailable: false,
  workspace: null,
  backendReady: null,
  persistencePromise: null,
  approvalPersistencePromise: null
};

function esc(value) {
  return String(value).replace(/[&<>"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;"
  }[char]));
}

function currentFingerprint() {
  return JSON.stringify({
    request: $("#requestInput").value.trim(),
    quality: $("#quality").value,
    tokenMode: $("#tokenMode").value,
    budget: $("#budget").value
  });
}

function qualityLabel(value) {
  return ({ high: "بالا", balanced: "متعادل", fast: "سریع" })[value] || "بالا";
}

function tokenModeLabel(value) {
  return ({
    aggressive: "تهاجمی (هدف طراحی، نه صرفه‌جویی اندازه‌گیری‌شده)",
    balanced: "متعادل (هدف طراحی، نه صرفه‌جویی اندازه‌گیری‌شده)",
    off: "خاموش"
  })[value] || "نامشخص";
}

async function apiRequest(path, options = {}) {
  if (typeof fetch !== "function") throw new Error("مرورگر به Backend محلی متصل نیست.");
  const headers = Object.assign({}, options.headers || {});
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, Object.assign({
    method: "GET",
    headers,
    cache: "no-store",
    credentials: "same-origin"
  }, options, { headers }));
  let payload = {};
  try {
    payload = await response.json();
  } catch (_) {
    payload = {};
  }
  if (!response.ok) {
    const message = payload && payload.error && payload.error.message;
    throw new Error(message || ("خطای Backend (" + response.status + ")"));
  }
  return payload;
}

function setBackendStatus(message) {
  const label = $("#backendStatusText");
  if (label) {
    label.textContent = message;
    return;
  }
  const badge = $("#backendStatus");
  if (badge) badge.textContent = message;
}

function statusLabel(status) {
  return ({
    draft: "پیش‌نویس",
    approved: "تأیید شده",
    simulated: "شبیه‌سازی شده",
    cancelled: "لغو شده",
    failed: "ناموفق"
  })[status] || "نامشخص";
}

function renderHistory(records) {
  const container = $("#historyList");
  if (!container) return;
  if (!Array.isArray(records) || records.length === 0) {
    container.innerHTML = '<p class="history-empty">هنوز طرحی در SQLite ذخیره نشده است.</p>';
    return;
  }
  container.innerHTML = records.map((record) => {
    const timestamp = new Date(record.created_at).toLocaleString("fa-IR");
    return '<div class="history-item"><div class="history-copy"><strong>نسخه ' +
      esc(record.version) + ' · ' + esc(record.title) + '</strong><small>' +
      esc(timestamp) + '</small></div><span class="history-status">' +
      esc(statusLabel(record.status)) + '</span></div>';
  }).join("");
}

async function refreshWorkspace() {
  const workspace = await apiRequest("/api/workspace");
  state.workspace = workspace.project;
  renderHistory(workspace.recent_plans || []);
  return workspace;
}

function formatModelSize(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value <= 0) return "حجم نامشخص";
  if (value >= 1024 ** 3) return (value / (1024 ** 3)).toFixed(1) + " GiB";
  return (value / (1024 ** 2)).toFixed(0) + " MiB";
}

function renderProviderResult(diagnostic) {
  const container = $("#providerResult");
  if (!container) return;
  if (!diagnostic || !diagnostic.available) {
    const message = diagnostic && diagnostic.message
      ? diagnostic.message
      : "Backend محلی در دسترس نیست؛ ابتدا start_local.bat را اجرا کن.";
    container.innerHTML = '<div class="provider-state unavailable"><strong>Ollama تأیید نشد</strong><p>' +
      esc(message) + '</p><small>هیچ مدل اجرا یا دانلود نشد.</small></div>';
    return;
  }

  const models = Array.isArray(diagnostic.models) ? diagnostic.models : [];
  const modelMarkup = models.map((model) => {
    const details = [model.parameter_size, model.quantization, model.family]
      .filter((item) => typeof item === "string" && item.trim().length > 0)
      .join(" · ");
    return '<div class="provider-model"><div><strong>' + esc(model.name) +
      '</strong><small>' + esc(details || "جزئیات مدل اعلام نشده") +
      '</small></div><span>' + esc(formatModelSize(model.size_bytes)) + '</span></div>';
  }).join("");

  container.innerHTML = '<div class="provider-state available"><strong>سرویس Ollama پاسخ داد</strong><p>' +
    esc(diagnostic.message || "فهرست محلی خوانده شد.") + '</p><div class="provider-summary">تعداد مدل‌های محلی: ' +
    esc(diagnostic.model_count || 0) + '</div>' +
    (models.length
      ? '<div class="provider-models">' + modelMarkup + '</div>'
      : '<p class="history-empty">سرویس فعال است، اما مدل محلی‌ای در فهرست نیست.</p>') +
    '<small>این بررسی فقط GET /api/tags را می‌خواند؛ تعداد درخواست‌های تولید متن: ۰، دانلود جدید: ۰.</small></div>';
}

async function checkProviders() {
  const container = $("#providerResult");
  const button = $("#providerCheckBtn");
  if (!state.backendAvailable) {
    if (container) container.innerHTML =
      '<p class="history-empty">Backend در دسترس نیست؛ برنامه را با start_local.bat اجرا کن.</p>';
    return;
  }
  if (button) {
    button.disabled = true;
    button.textContent = "در حال بررسی...";
  }
  if (container) container.innerHTML = '<p class="history-empty">در حال بررسی سرویس محلی؛ مدل اجرا یا دانلود نمی‌شود...</p>';
  try {
    const result = await apiRequest("/api/providers");
    renderProviderResult(result.ollama);
  } catch (error) {
    if (container) container.innerHTML = '<div class="provider-state unavailable"><strong>بررسی ناموفق</strong><p>' +
      esc(error.message) + '</p></div>';
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "بررسی دوباره";
    }
  }
}

async function initBackend() {
  if (typeof fetch !== "function") {
    setBackendStatus("Backend خاموش • ذخیره‌سازی غیرفعال");
    return false;
  }
  try {
    const health = await apiRequest("/api/health");
    const workspace = await refreshWorkspace();
    state.backendAvailable = true;
    setBackendStatus(
      health.storage === "sqlite"
        ? "Backend محلی + SQLite فعال • بدون AI"
        : "Backend محلی فعال • وضعیت AI تأیید نشده"
    );
    renderHistory(workspace.recent_plans || []);
    void checkProviders();
    return true;
  } catch (_) {
    state.backendAvailable = false;
    state.workspace = null;
    setBackendStatus("Backend خاموش • طرح‌ها در این حالت ذخیره نمی‌شوند");
    const container = $("#historyList");
    if (container) container.innerHTML =
      '<p class="history-empty">برای ذخیره پایدار، رابط را با فایل start_local.bat یا دستور پایتون اجرا کن.</p>';
    return false;
  }
}

function stopSimulation() {
  state.runId += 1;
  if (state.timer !== null) {
    clearTimeout(state.timer);
    state.timer = null;
  }
}

function invalidatePlan(reason = "ورودی تغییر کرد؛ Preview تازه بساز.") {
  stopSimulation();
  state.plan = null;
  state.approved = false;
  state.persistencePromise = null;
  state.approvalPersistencePromise = null;
  $("#planView").classList.add("hidden");
  $("#approvalBar").classList.add("hidden");
  $("#executionPanel").classList.add("hidden");
  $("#emptyState").classList.remove("hidden");
  $("#planStatus").textContent = reason;
  $("#executionStatus").textContent = "متوقف";
  $("#taskList").innerHTML = "";
  $("#finalBox").textContent = "";
}

function persistPlan(plan) {
  return (async () => {
    const available = await state.backendReady;
    if (!available || !state.workspace) return false;
    try {
      const result = await apiRequest("/api/plans", {
        method: "POST",
        body: JSON.stringify({
          project_id: state.workspace.id,
          fingerprint: plan.fingerprint,
          plan
        })
      });
      plan.recordId = result.record.id;
      plan.version = result.record.version;
      plan.persistedStatus = result.record.status;
      if (state.plan === plan) {
        $("#planStatus").textContent = "Preview ذخیره شد • نسخه " + plan.version + " • تأیید نشده";
      }
      const workspace = await refreshWorkspace();
      renderHistory(workspace.recent_plans || []);
      return true;
    } catch (error) {
      if (state.plan === plan) {
        $("#planStatus").textContent = "Preview آماده است، اما ذخیره SQLite ناموفق بود: " + error.message;
      }
      return false;
    }
  })();
}

function persistApproval(plan) {
  return (async () => {
    const saved = state.persistencePromise ? await state.persistencePromise : false;
    if (!saved || !plan.recordId || !state.backendAvailable) return false;
    try {
      const result = await apiRequest("/api/plans/" + encodeURIComponent(plan.recordId) + "/approve", {
        method: "POST",
        body: JSON.stringify({ fingerprint: plan.fingerprint })
      });
      plan.persistedStatus = result.record.status;
      return true;
    } catch (error) {
      setBackendStatus("SQLite فعال • ثبت تأیید ناموفق");
      if (state.plan === plan) {
        $("#planStatus").textContent = "شبیه‌سازی محلی شروع شد، اما تأیید در SQLite ثبت نشد: " + error.message;
      }
      return false;
    }
  })();
}

function persistSimulation(plan) {
  return (async () => {
    const approved = state.approvalPersistencePromise
      ? await state.approvalPersistencePromise
      : false;
    if (!approved || !plan.recordId || !state.backendAvailable) return false;
    try {
      await apiRequest("/api/plans/" + encodeURIComponent(plan.recordId) + "/simulation", {
        method: "POST",
        body: JSON.stringify({})
      });
      plan.persistedStatus = "simulated";
      const workspace = await refreshWorkspace();
      renderHistory(workspace.recent_plans || []);
      return true;
    } catch (error) {
      setBackendStatus("SQLite فعال • ثبت وضعیت شبیه‌سازی ناموفق");
      return false;
    }
  })();
}

function buildPlan() {
  $("#validation").textContent = "";
  stopSimulation();

  try {
    const plan = Core.createPlan($("#requestInput").value, {
      quality: $("#quality").value,
      tokenMode: $("#tokenMode").value,
      budget: $("#budget").value
    });

    plan.fingerprint = currentFingerprint();
    plan.id = Date.now();
    state.plan = plan;
    state.approved = false;
    state.approvalPersistencePromise = null;

    $("#executionPanel").classList.add("hidden");
    $("#emptyState").classList.add("hidden");
    $("#planView").classList.remove("hidden");
    $("#approvalBar").classList.remove("hidden");
    $("#planStatus").textContent = "Preview آماده است — تأیید نشده";
    renderPlan();
    state.persistencePromise = persistPlan(plan);
  } catch (error) {
    $("#validation").textContent = error.message || "ساخت Preview ناموفق بود.";
  }
}

function renderPlan() {
  const plan = state.plan;
  const taskMarkup = plan.tasks.map((task) => {
    return '<div class="task-card">' +
      '<div class="task-top"><div class="task-name">' + task.id + '. ' + esc(task.name) + '</div><span class="tag">' + esc(task.kind) + '</span></div>' +
      '<p style="color:var(--muted);font-size:12px;line-height:1.8">' + esc(task.desc) + '</p>' +
      '<div class="task-grid">' +
        '<div>سختی<strong>' + task.difficulty + '/5</strong></div>' +
        '<div>مسیر پیشنهادی<strong>' + esc(task.provider) + '</strong></div>' +
        '<div>ورودی تخمینی<strong>' + task.inputTokens.toLocaleString("en-US") + '</strong></div>' +
        '<div>خروجی تخمینی<strong>' + task.outputTokens.toLocaleString("en-US") + '</strong></div>' +
      '</div></div>';
  }).join("");

  const warnings = plan.warnings.map((warning) => "<li>" + esc(warning) + "</li>").join("");
  $("#planView").innerHTML =
    '<div class="plan-wrap"><div class="hero-card"><div class="hero-title">' + esc(plan.title) + '</div><div class="meta-grid">' +
      '<div class="meta"><small>کیفیت مطلوب</small><strong>' + esc(qualityLabel(plan.quality)) + '</strong></div>' +
      '<div class="meta"><small>سیاست هزینه</small><strong>فقط رایگان</strong></div>' +
      '<div class="meta"><small>توکن تخمینی</small><strong>' + plan.totalTokens.toLocaleString("en-US") + '</strong></div>' +
      '<div class="meta"><small>تعداد Task</small><strong>' + plan.tasks.length + '</strong></div>' +
    '</div></div>' +
    '<div class="section-title">جزئیات برنامه</div>' + taskMarkup +
    '<div class="section-title">صرفه‌جویی و محدودیت‌ها</div>' +
    '<div class="task-card"><p style="margin:0;color:var(--muted);font-size:12px;line-height:1.9">' +
      esc(tokenModeLabel(plan.tokenMode)) + '. هیچ Provider واقعی به این نسخه وصل نیست و اعداد توکن صرفاً تخمینی هستند. ' +
      'دکمه تأیید فقط شبیه‌سازی را اجرا می‌کند؛ نه خود پژوهش، سایت یا کد را.' +
      '<ul>' + warnings + '</ul>' +
    '</p></div></div>';
}

function approveAndSimulate() {
  if (!state.plan) return;

  if (!Core.isPlanCurrent(state.plan.fingerprint, currentFingerprint())) {
    invalidatePlan("طرح با ورودی فعلی مطابقت ندارد؛ Preview جدید بساز.");
    return;
  }

  const approvedPlan = state.plan;
  state.approved = true;
  state.approvalPersistencePromise = persistApproval(approvedPlan);
  $("#approvalBar").classList.add("hidden");
  $("#executionPanel").classList.remove("hidden");
  $("#executionStatus").textContent = "شبیه‌سازی در حال اجرا";
  $("#taskList").innerHTML = "";
  $("#finalBox").textContent = "";

  const thisRun = ++state.runId;

  state.plan.tasks.forEach((task) => {
    const card = document.createElement("div");
    card.className = "run-card";
    card.id = "run-" + task.id;
    card.innerHTML = '<div class="run-head"><strong>' + esc(task.name) + '</strong><span class="state running">در صف شبیه‌سازی</span></div>' +
      '<p style="color:var(--muted);font-size:12px;margin:8px 0 0">' + esc(task.provider) + '</p>';
    $("#taskList").appendChild(card);
  });

  let index = 0;
  const step = () => {
    if (thisRun !== state.runId) return;
    if (index >= state.plan.tasks.length) {
      state.timer = null;
      $("#executionStatus").textContent = "شبیه‌سازی تمام شد";
      $("#finalBox").innerHTML = "<strong>فقط شبیه‌سازی انجام شد؛ هیچ Task واقعی اجرا نشد.</strong>" +
        "<p style='margin:7px 0 0;color:var(--muted);font-size:12px'>برای اجرای واقعی باید یک Provider رایگان و قابل دسترس به Backend متصل و آزمایش شود.</p>";
      void persistSimulation(approvedPlan);
      return;
    }

    const status = $("#run-" + state.plan.tasks[index].id).querySelector(".state");
    status.textContent = "شبیه‌سازی شد";
    status.className = "state done";
    index += 1;
    state.timer = setTimeout(step, 150);
  };

  step();
}

$("#planBtn").addEventListener("click", buildPlan);
$("#approveBtn").addEventListener("click", approveAndSimulate);
$("#editBtn").addEventListener("click", () => {
  invalidatePlan("طرح لغو شد؛ تغییرات را اعمال کن و Preview جدید بساز.");
  $("#requestInput").focus();
});

["#requestInput", "#quality", "#tokenMode", "#budget"].forEach((selector) => {
  $(selector).addEventListener("input", () => {
    if (state.plan || state.approved) invalidatePlan();
  });
  $(selector).addEventListener("change", () => {
    if (state.plan || state.approved) invalidatePlan();
  });
});

$("#exampleBtn").addEventListener("click", () => {
  $("#requestInput").value = "یک پژوهش علمی درباره تأثیر خواب بر حافظه دانش‌آموزان تهیه کن؛ منابع معتبر، ساختار مقاله و پیشنهاد تصویر می‌خواهم.";
  invalidatePlan("نمونه بارگذاری شد؛ Preview جدید بساز.");
});

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    $("#requestInput").value = button.dataset.example;
    invalidatePlan("نمونه بارگذاری شد؛ Preview جدید بساز.");
  });
});

const providerCheckButton = $("#providerCheckBtn");
if (providerCheckButton) providerCheckButton.addEventListener("click", () => { void checkProviders(); });

state.backendReady = initBackend();
