const $ = (selector) => document.querySelector(selector);

const state = {
  plan: null,
  approved: false,
  runId: 0,
  timer: null
};

const rules = [
  { keys: ["پژوهش", "تحقیق", "مقاله", "علمی", "منبع", "research"], add: ["research", "evidence", "writing", "factcheck"] },
  { keys: ["سایت", "وب", "فروشگاه", "website", "frontend", "صفحه", "واکنش‌گرا"], add: ["architecture", "ui", "frontend", "seo", "security", "testing"] },
  { keys: ["کد", "برنامه", "پایتون", "اپ", "اتوماسیون", "csv", "excel"], add: ["architecture", "coding", "testing", "security"] },
  { keys: ["عکس", "تصویر", "پوستر", "visual", "image"], add: ["visual"] },
  { keys: ["امنیت", "رمز", "login", "احراز"], add: ["security"] },
  { keys: ["تست", "testing", "bug", "خطا"], add: ["testing"] }
];

const catalog = {
  architecture: { name: "معماری و طراحی راه‌حل", kind: "Planning", desc: "تبدیل هدف به ساختار، اجزای اصلی و وابستگی‌ها.", base: 3 },
  research: { name: "تحقیق و جمع‌آوری منابع", kind: "Research", desc: "پیدا کردن اطلاعات و منابع مرتبط؛ بدون ساخت ادعای بی‌منبع.", base: 4 },
  evidence: { name: "استخراج شواهد", kind: "Analysis", desc: "تبدیل منابع به یافته‌ها، اعداد و نکات قابل استناد.", base: 4 },
  writing: { name: "نگارش خروجی", kind: "Writing", desc: "تبدیل شواهد و طرح به متن نهایی با ساختار مشخص.", base: 3 },
  factcheck: { name: "راستی‌آزمایی", kind: "Quality", desc: "بررسی ادعاها، تناقض‌ها و پیوند ادعا به منبع.", base: 4 },
  ui: { name: "طراحی رابط کاربری", kind: "Design", desc: "تعیین ساختار صفحات، اجزا، حالات و رفتار واکنش‌گرا.", base: 3 },
  frontend: { name: "پیاده‌سازی Frontend", kind: "Build", desc: "تبدیل طرح به کد قابل اجرا و responsive.", base: 4 },
  seo: { name: "SEO", kind: "Quality", desc: "ساختار معنایی، metadata و دسترسی‌پذیری.", base: 3 },
  security: { name: "بررسی امنیت", kind: "Security", desc: "جست‌وجوی الگوهای پرخطر و ارائه اصلاح مشخص.", base: 4 },
  testing: { name: "تست و کنترل کیفیت", kind: "QA", desc: "تعریف و اجرای آزمون‌های لازم و کنترل خطاهای اصلی.", base: 3 },
  coding: { name: "تولید کد", kind: "Build", desc: "پیاده‌سازی Task در فناوری مناسب پروژه.", base: 4 },
  visual: { name: "تولید یا طراحی تصویر", kind: "Visual", desc: "تعریف تصویر موردنیاز و انتخاب مسیر تولید مناسب.", base: 3 }
};

function esc(value) {
  return String(value).replace(/[&<>"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;"
  }[char]));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function difficulty(text, base) {
  let score = base;
  if (text.length > 220) score++;
  if (/پیچیده|حرفه‌ای|تخصصی|کامل|enterprise|production/i.test(text)) score++;
  if (/ساده|سریع|مختصر/i.test(text)) score--;
  return clamp(score, 1, 5);
}

// Heuristic only. Actual token counts require the selected provider's tokenizer/usage data.
function estimateTokens(text) {
  return Math.max(1, Math.ceil(text.length / 4));
}

function detectTypes(text) {
  const found = new Set(["architecture"]);
  const lower = text.toLowerCase();

  rules.forEach((rule) => {
    if (rule.keys.some((key) => text.includes(key) || lower.includes(key.toLowerCase()))) {
      rule.add.forEach((type) => found.add(type));
    }
  });

  if (found.has("research")) found.add("factcheck");
  if (found.has("frontend")) found.add("testing");
  return Array.from(found);
}

function providerFor(kind) {
  if (kind === "Visual") return "مسیر تصویر رایگان/محلی باید بررسی شود";
  return "مدل محلی یا Provider رایگان؛ هنوز متصل/تأیید نشده";
}

function currentFingerprint() {
  return JSON.stringify({
    request: $("#requestInput").value.trim(),
    quality: $("#quality").value,
    tokenMode: $("#tokenMode").value,
    budget: $("#budget").value
  });
}

function stopSimulation() {
  state.runId++;
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

function qualityLabel(value) {
  return ({ high: "بالا", balanced: "متعادل", fast: "سریع" })[value] || "بالا";
}

function tokenModeLabel(value) {
  return ({ aggressive: "هدف کاهش Context: تهاجمی", balanced: "هدف کاهش Context: متعادل", off: "کاهش Context: خاموش" })[value] || "نامشخص";
}

function buildPlan() {
  const request = $("#requestInput").value.trim();
  $("#validation").textContent = "";

  if (request.length < 12) {
    $("#validation").textContent = "درخواست خیلی کوتاه است؛ لطفاً یک جمله کامل‌تر بنویس.";
    return;
  }

  stopSimulation();
  const types = detectTypes(request);
  const tasks = types.map((type, index) => {
    const item = catalog[type] || catalog.architecture;
    const score = difficulty(request, item.base);
    // Rough planning estimates, not observed usage. Do not apply fake percentage discounts.
    const inputTokens = estimateTokens(request) + 40 + score * 12;
    const outputTokens = 100 + score * 60;

    return {
      id: index + 1,
      type,
      name: item.name,
      kind: item.kind,
      desc: item.desc,
      difficulty: score,
      inputTokens,
      outputTokens,
      totalTokens: inputTokens + outputTokens,
      provider: providerFor(item.kind)
    };
  });

  const settings = {
    quality: $("#quality").value,
    tokenMode: $("#tokenMode").value,
    budget: $("#budget").value
  };

  state.plan = {
    id: Date.now(),
    fingerprint: currentFingerprint(),
    title: request.length > 70 ? request.slice(0, 67) + "…" : request,
    goal: request,
    quality: qualityLabel(settings.quality),
    tokenMode: tokenModeLabel(settings.tokenMode),
    budget: "۰ تومان در این نسخه؛ هیچ API فراخوانی نمی‌شود",
    tasks,
    totalTokens: tasks.reduce((sum, task) => sum + task.totalTokens, 0)
  };
  state.approved = false;

  $("#executionPanel").classList.add("hidden");
  $("#emptyState").classList.add("hidden");
  $("#planView").classList.remove("hidden");
  $("#approvalBar").classList.remove("hidden");
  $("#planStatus").textContent = "Preview آماده است — تأیید نشده";
  renderPlan();
}

function renderPlan() {
  const plan = state.plan;
  let html = '<div class="plan-wrap"><div class="hero-card"><div class="hero-title">' + esc(plan.title) + '</div><div class="meta-grid">';
  html += '<div class="meta"><small>کیفیت مطلوب</small><strong>' + esc(plan.quality) + '</strong></div>';
  html += '<div class="meta"><small>هزینه این نسخه</small><strong>۰ تومان</strong></div>';
  html += '<div class="meta"><small>توکن تخمینی</small><strong>' + plan.totalTokens.toLocaleString("en-US") + '</strong></div>';
  html += '<div class="meta"><small>تعداد Task</small><strong>' + plan.tasks.length + '</strong></div></div></div>';
  html += '<div class="section-title">جزئیات برنامه</div>';

  plan.tasks.forEach((task) => {
    html += '<div class="task-card"><div class="task-top"><div class="task-name">' + task.id + '. ' + esc(task.name) + '</div><span class="tag">' + esc(task.kind) + '</span></div>';
    html += '<p style="color:var(--muted);font-size:12px;line-height:1.8">' + esc(task.desc) + '</p>';
    html += '<div class="task-grid"><div>سختی<strong>' + task.difficulty + '/5</strong></div><div>مسیر پیشنهادی<strong>' + esc(task.provider) + '</strong></div><div>ورودی تخمینی<strong>' + task.inputTokens.toLocaleString("en-US") + '</strong></div><div>خروجی تخمینی<strong>' + task.outputTokens.toLocaleString("en-US") + '</strong></div></div></div>';
  });

  html += '<div class="section-title">صرفه‌جویی و محدودیت‌ها</div><div class="task-card"><p style="margin:0;color:var(--muted);font-size:12px;line-height:1.9">';
  html += esc(plan.tokenMode) + '. این نسخه فقط طرح صرفه‌جویی را نمایش می‌دهد؛ هنوز Context فشرده یا درخواست AI ارسال نمی‌شود. اعداد توکن تقریبی‌اند و مصرف واقعی محسوب نمی‌شوند. ';
  html += 'هیچ Provider واقعی به این نسخه وصل نیست. دکمه تأیید، فقط شبیه‌سازی را اجرا می‌کند، نه خود پژوهش/سایت/کد را.';
  html += '</p></div></div>';

  $("#planView").innerHTML = html;
}

function approveAndSimulate() {
  if (!state.plan) return;

  if (state.plan.fingerprint !== currentFingerprint()) {
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
    card.innerHTML = '<div class="run-head"><strong>' + esc(task.name) + '</strong><span class="state running">شبیه‌سازی در صف</span></div><p style="color:var(--muted);font-size:12px;margin:8px 0 0">' + esc(task.provider) + '</p>';
    $("#taskList").appendChild(card);
  });

  let index = 0;
  const step = () => {
    if (thisRun !== state.runId) return;
    if (index >= state.plan.tasks.length) {
      state.timer = null;
      $("#executionStatus").textContent = "شبیه‌سازی تمام شد";
      $("#finalBox").innerHTML = "<strong>فقط شبیه‌سازی انجام شد؛ هیچ Task واقعی اجرا نشد.</strong><p style='margin:7px 0 0;color:var(--muted);font-size:12px'>مدل هوش مصنوعی، ابزار تحقیق یا تولید تصویر هنوز متصل نیست. این وضعیت موفقیت پروژه اصلی محسوب نمی‌شود.</p>";
      return;
    }

    const task = state.plan.tasks[index];
    const status = $("#run-" + task.id).querySelector(".state");
    status.textContent = "شبیه‌سازی شد";
    status.className = "state done";
    index++;
    state.timer = setTimeout(step, 180);
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