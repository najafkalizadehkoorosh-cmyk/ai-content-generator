"use strict";

const RULES = [
  { keys: ["پژوهش", "تحقیق", "مقاله", "علمی", "منبع", "research", "paper", "study"], add: ["research", "evidence", "writing", "factcheck"] },
  { keys: ["سایت", "وب", "فروشگاه", "website", "frontend", "صفحه", "واکنش‌گرا", "web app"], add: ["architecture", "ui", "frontend", "seo", "security", "testing"] },
  { keys: ["کد", "برنامه", "پایتون", "اپ", "اتوماسیون", "csv", "excel", "code", "script"], add: ["architecture", "coding", "testing", "security"] },
  { keys: ["عکس", "تصویر", "پوستر", "visual", "image", "illustration"], add: ["visual"] },
  { keys: ["امنیت", "رمز", "login", "احراز", "security"], add: ["security"] },
  { keys: ["تست", "testing", "bug", "خطا", "test"], add: ["testing"] }
];

const CATALOG = {
  architecture: { name: "معماری و طراحی راه‌حل", kind: "Planning", desc: "تبدیل هدف به ساختار، اجزای اصلی و وابستگی‌ها.", base: 3 },
  research: { name: "تحقیق و جمع‌آوری منابع", kind: "Research", desc: "پیدا کردن اطلاعات و منابع مرتبط؛ هر ادعای مهم باید منبع داشته باشد.", base: 4 },
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

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function difficulty(text, base) {
  let score = base;
  if (text.length > 220) score += 1;
  if (/پیچیده|حرفه‌ای|تخصصی|کامل|enterprise|production|advanced/i.test(text)) score += 1;
  if (/ساده|سریع|مختصر|simple|quick/i.test(text)) score -= 1;
  return clamp(score, 1, 5);
}

// Heuristic only. Actual token counts require the selected model's tokenizer or usage metadata.
function estimateTokens(text) {
  return Math.max(1, Math.ceil(String(text).length / 4));
}

function detectTypes(text) {
  const request = String(text || "");
  const lower = request.toLowerCase();
  const found = new Set(["architecture"]);

  for (const rule of RULES) {
    if (rule.keys.some((key) => request.includes(key) || lower.includes(key.toLowerCase()))) {
      rule.add.forEach((type) => found.add(type));
    }
  }

  if (found.has("research")) found.add("factcheck");
  if (found.has("frontend")) found.add("testing");
  return Array.from(found);
}

function providerFor(kind) {
  if (kind === "Visual") return "مسیر تصویر رایگان/محلی باید بررسی شود";
  return "مدل محلی یا Provider رایگان؛ هنوز متصل/تأیید نشده";
}

function createPlan(request, options = {}) {
  const text = String(request || "").trim();
  if (text.length < 12) {
    const error = new Error("درخواست خیلی کوتاه است؛ لطفاً یک جمله کامل‌تر بنویس.");
    error.code = "REQUEST_TOO_SHORT";
    throw error;
  }

  const quality = options.quality || "high";
  const tokenMode = options.tokenMode || "aggressive";
  const budget = options.budget || "zero";
  const types = detectTypes(text);

  const tasks = types.map((type, index) => {
    const item = CATALOG[type] || CATALOG.architecture;
    const score = difficulty(text, item.base);
    const inputTokens = estimateTokens(text) + 40 + score * 12;
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
      provider: providerFor(item.kind),
      status: "planned"
    };
  });

  return {
    title: text.length > 70 ? text.slice(0, 67) + "…" : text,
    goal: text,
    quality,
    tokenMode,
    budget,
    costPolicy: "zero-cost-only",
    executionMode: "simulation-only",
    tasks,
    totalTokens: tasks.reduce((sum, task) => sum + task.totalTokens, 0),
    estimateType: "heuristic",
    warnings: [
      "تخمین توکن تقریبی است و مصرف واقعی Provider نیست.",
      "هیچ Provider واقعی به این نسخه متصل نیست.",
      "حالت صرفه‌جویی هنوز Context را واقعاً فشرده نمی‌کند."
    ]
  };
}

function isPlanCurrent(planFingerprint, currentFingerprint) {
  return typeof planFingerprint === "string" &&
    planFingerprint.length > 0 &&
    planFingerprint === currentFingerprint;
}

const api = { CATALOG, clamp, difficulty, estimateTokens, detectTypes, providerFor, createPlan, isPlanCurrent };

if (typeof module !== "undefined" && module.exports) module.exports = api;
if (typeof window !== "undefined") window.AIRouterCore = api;
