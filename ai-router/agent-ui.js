"use strict";

(() => {
  const $ = (selector) => document.querySelector(selector);
  const oldButton = $("#approveBtn");
  if (!oldButton) return;
  const executeButton = oldButton.cloneNode(true);
  executeButton.textContent = "تأیید طرح و اجرای ایجنت";
  executeButton.disabled = true;
  oldButton.replaceWith(executeButton);

  const modelSelect = $("#agentModelSelect");
  const modelHelp = $("#agentModelHelp");
  const agentPanel = $("#agentResultPanel");
  const agentMeta = $("#agentRunMeta");
  const agentOutput = $("#agentOutput");
  const finalBox = $("#finalBox");
  const requestFields = ["#requestInput", "#quality", "#tokenMode", "#budget"];
  const state = { models: [], previewFingerprint: null, busy: false };

  function fingerprint() {
    return JSON.stringify({
      request: $("#requestInput").value.trim(),
      quality: $("#quality").value,
      tokenMode: $("#tokenMode").value,
      budget: $("#budget").value
    });
  }

  function updateButton() {
    const visible = !$("#planView").classList.contains("hidden");
    executeButton.disabled = state.busy || !state.models.length ||
      !state.previewFingerprint || !visible || state.previewFingerprint !== fingerprint();
  }

  async function api(path, options = {}) {
    const headers = Object.assign({}, options.headers || {});
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(path, Object.assign({
      method: "GET", headers, cache: "no-store", credentials: "same-origin"
    }, options, { headers }));
    let payload = {};
    try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok) {
      const error = new Error(payload && payload.error && payload.error.message
        ? payload.error.message : "درخواست Backend ناموفق بود (" + response.status + ").");
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  function setBusy(value) {
    state.busy = value;
    requestFields.forEach((selector) => { $(selector).disabled = value; });
    modelSelect.disabled = value || state.models.length === 0;
    $("#planBtn").disabled = value;
    executeButton.textContent = value ? "در حال اجرای مدل محلی..." : "تأیید طرح و اجرای ایجنت";
    updateButton();
  }

  function safeInt(value) {
    return Number.isInteger(value) && value >= 0 ? value : 0;
  }

  async function refreshModels() {
    try {
      const result = await api("/api/providers");
      const diagnostic = result.ollama || {};
      const detected = diagnostic.available && Array.isArray(diagnostic.models)
        ? diagnostic.models.filter((item) => item && typeof item.name === "string" && item.name.trim())
        : [];
      const isCloud = (item) => item.is_cloud === true || item.name.toLowerCase().endsWith(":cloud");
      const cloudCount = detected.filter(isCloud).length;
      state.models = detected.filter((item) => !isCloud(item));
      const previous = modelSelect.value;
      modelSelect.replaceChildren();
      if (!state.models.length) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = cloudCount
          ? "فقط مدل ابری شناسایی شد؛ برای نسخه صفرهزینه مدل محلی لازم است."
          : (diagnostic.message || "مدل محلی نصب‌شده پیدا نشد");
        modelSelect.appendChild(option);
        modelHelp.textContent = cloudCount
          ? "مدل‌های :cloud در اجرای ایجنت مسدودند تا درخواست به سرویس ابری یا اعتبار مصرفی نرود. هیچ مدلی دانلود نشد."
          : "Ollama یا مدل محلی نصب‌شده در دسترس نیست؛ هیچ دانلود یا درخواست ابری انجام نشد.";
      } else {
        state.models.forEach((model) => {
          const option = document.createElement("option");
          option.value = model.name;
          option.textContent = model.name;
          modelSelect.appendChild(option);
        });
        modelSelect.value = state.models.some((item) => item.name === previous)
          ? previous : state.models[0].name;
        modelHelp.textContent = cloudCount
          ? "فقط مدل محلی انتخاب‌پذیر است؛ " + cloudCount + " مدل ابری از ایجنت حذف شده. اجرای مدل فقط پس از تأیید همین Preview انجام می‌شود."
          : "مدل فقط پس از تأیید همین Preview فراخوانی می‌شود؛ دانلود خودکار انجام نمی‌شود.";
        const status = $("#backendStatusText");
        if (status) status.textContent = "Backend محلی + SQLite فعال • مدل محلی شناسایی شد";
      }
      modelSelect.disabled = state.busy || state.models.length === 0;
    } catch (error) {
      state.models = [];
      modelSelect.replaceChildren();
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Backend محلی در دسترس نیست";
      modelSelect.appendChild(option);
      modelHelp.textContent = error.message;
      modelSelect.disabled = true;
    }
    updateButton();
  }

  async function findCurrentPlan(currentFingerprint) {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const workspace = await api("/api/workspace");
      const recent = Array.isArray(workspace.recent_plans) ? workspace.recent_plans.slice(0, 4) : [];
      for (const item of recent) {
        if (!item || typeof item.id !== "string") continue;
        const response = await api("/api/plans/" + encodeURIComponent(item.id));
        if (response.record && response.record.fingerprint === currentFingerprint) return response.record;
      }
      await new Promise((resolve) => setTimeout(resolve, 150));
    }
    throw new Error("طرح تازه در SQLite پیدا نشد. Backend محلی را بررسی کن و دوباره Preview بساز.");
  }

  function showRunCard(status, details) {
    const taskList = $("#taskList");
    taskList.replaceChildren();
    const card = document.createElement("div");
    card.className = "run-card";
    const head = document.createElement("div");
    head.className = "run-head";
    const name = document.createElement("strong");
    name.textContent = "تولید خروجی متنی با مدل محلی";
    const label = document.createElement("span");
    label.className = "state " + (status === "succeeded" ? "done" : status === "running" ? "running" : "");
    label.textContent = status === "succeeded" ? "موفق" : status === "running" ? "در حال اجرا" : "ناموفق";
    head.append(name, label);
    const description = document.createElement("p");
    description.style.cssText = "color:var(--muted);font-size:12px;margin:8px 0 0;line-height:1.8";
    description.textContent = details || "فقط مدل محلی انتخاب‌شده فراخوانی می‌شود.";
    card.append(head, description);
    taskList.appendChild(card);
  }

  async function executeApprovedPlan() {
    if (state.busy) return;
    if (!state.previewFingerprint || state.previewFingerprint !== fingerprint() ||
        $("#planView").classList.contains("hidden")) {
      $("#planStatus").textContent = "ورودی تغییر کرده؛ Preview تازه بساز.";
      state.previewFingerprint = null;
      updateButton();
      return;
    }
    const model = modelSelect.value;
    if (!model || !state.models.some((item) => item.name === model)) {
      modelHelp.textContent = "ابتدا یک مدل نصب‌شده را انتخاب کن.";
      return;
    }

    const current = state.previewFingerprint;
    setBusy(true);
    $("#executionPanel").classList.remove("hidden");
    $("#executionStatus").textContent = "در حال اجرای واقعی مدل محلی";
    finalBox.textContent = "درخواست واقعی به مدل محلی ارسال می‌شود؛ مدت اجرا به مدل و سخت‌افزار بستگی دارد.";
    agentPanel.classList.remove("hidden");
    agentMeta.textContent = "مدل: " + model + " • در حال اجرا • وب‌گردی یا تغییر فایل انجام نمی‌شود.";
    agentOutput.textContent = "";
    showRunCard("running", "منتظر پاسخ مدل محلی هستیم. پنجره Backend را تا پایان درخواست باز نگه دار.");
    try {
      const planRecord = await findCurrentPlan(current);
      if (planRecord.status === "draft") {
        await api("/api/plans/" + encodeURIComponent(planRecord.id) + "/approve", {
          method: "POST", body: JSON.stringify({ fingerprint: current })
        });
      } else if (planRecord.status !== "approved") {
        throw new Error("وضعیت این طرح قابل اجرا نیست؛ Preview جدید بساز و دوباره تأیید کن.");
      }

      const result = await api("/api/plans/" + encodeURIComponent(planRecord.id) + "/execute", {
        method: "POST", body: JSON.stringify({ fingerprint: current, model })
      });
      const record = result.record;
      if (!result.real_execution || !record || record.status !== "succeeded" ||
          typeof record.output_text !== "string" || !record.output_text.trim()) {
        throw new Error("مدل پاسخ موفق و قابل ذخیره برنگرداند؛ موفقیت ثبت نشد.");
      }
      $("#executionStatus").textContent = "اجرای واقعی کامل شد";
      $("#planStatus").textContent = "مدل محلی پاسخ داد • نتیجه در SQLite ذخیره شد";
      finalBox.textContent = "اجرای واقعی انجام شد. نتیجه در SQLite محلی ذخیره شده است.";
      agentMeta.textContent = "مدل: " + record.model + " • تلاش: " + safeInt(record.attempt) +
        " • توکن ورودی اعلام‌شده: " + safeInt(record.prompt_tokens) +
        " • توکن خروجی اعلام‌شده: " + safeInt(record.output_tokens) +
        " • زمان ثبت‌شده: " + safeInt(record.duration_ms) + " ms";
      agentOutput.textContent = record.output_text;
      showRunCard("succeeded", "پاسخ واقعی دریافت و در SQLite ذخیره شد.");
      if (typeof window.renderHistory === "function") {
        const workspace = await api("/api/workspace");
        window.renderHistory(workspace.recent_plans || []);
      }
    } catch (error) {
      const record = error.payload && error.payload.record;
      $("#executionStatus").textContent = "اجرای مدل ناموفق";
      $("#planStatus").textContent = "اجرای واقعی کامل نشد";
      finalBox.textContent = "مدل پاسخ موفق نداد؛ برنامه موفقیت جعلی ثبت نکرده است.";
      if (record && record.status === "failed") {
        agentMeta.textContent = "مدل: " + record.model + " • وضعیت: failed • " + (record.error_message || error.message);
        agentOutput.textContent = "";
        showRunCard("failed", record.error_message || error.message);
      } else {
        agentMeta.textContent = "اجرا آغاز نشد یا پیش‌شرط‌ها تأیید نشدند.";
        agentOutput.textContent = error.message;
        showRunCard("failed", error.message);
      }
    } finally {
      setBusy(false);
      updateButton();
    }
  }

  executeButton.addEventListener("click", () => { void executeApprovedPlan(); });
  modelSelect.addEventListener("change", updateButton);
  $("#planBtn").addEventListener("click", () => {
    state.previewFingerprint = null;
    setTimeout(() => {
      const visible = !$("#planView").classList.contains("hidden") &&
        $("#planView").textContent.trim().length > 0 &&
        !$("#validation").textContent.trim();
      state.previewFingerprint = visible ? fingerprint() : null;
      updateButton();
    }, 0);
  });
  requestFields.forEach((selector) => {
    $(selector).addEventListener("input", () => { state.previewFingerprint = null; updateButton(); });
    $(selector).addEventListener("change", () => { state.previewFingerprint = null; updateButton(); });
  });
  const providerButton = $("#providerCheckBtn");
  if (providerButton) providerButton.addEventListener("click", () => { void refreshModels(); });
  void refreshModels();
})();
