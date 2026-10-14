"use strict";

const $ = (selector) => document.querySelector(selector);
const Core = window.AIRouterCore;

const state = { plan: null, approved: false, runId: 0, timer: null };

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
  $("#planView").classList.add("hidden");
  $("#approvalBar").classList.add("hidden");
  $("#executionPanel").classList.add("hidden");
  $("#emptyState").classList.remove("hidden");
  $("#planStatus").textContent = reason;
  $("#executionStatus").textContent = "متوقف";
  $("#taskList").innerHTML = "";
  $("#finalBox").textContent = "";
}

function buildPlan() {
  $("#validation").textContent = "";

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

    $("#executionPanel").classList.add("hidden");
    $("#emptyState").classList.add("hidden");
    $("#planView").classList.remove("hidden");
    $("#approvalBar").classList.remove("hidden");
    $("#planStatus").textContent = "Preview آماده است — تأیید نشده";
    renderPlan();
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

  state.approved = true;
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