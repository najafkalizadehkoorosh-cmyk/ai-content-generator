"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const Core = require("../core.js");

test("rejects empty or unhelpfully short requests", () => {
  assert.throws(() => Core.createPlan("   "), { code: "REQUEST_TOO_SHORT" });
  assert.throws(() => Core.createPlan("سایت"), { code: "REQUEST_TOO_SHORT" });
});

test("research request includes research, evidence, writing and fact-check tasks", () => {
  const plan = Core.createPlan("یک پژوهش علمی درباره خواب با منابع معتبر تهیه کن و مقاله بنویس.");
  const types = plan.tasks.map((task) => task.type);
  assert.ok(types.includes("research"));
  assert.ok(types.includes("evidence"));
  assert.ok(types.includes("writing"));
  assert.ok(types.includes("factcheck"));
});

test("website request includes design, frontend, SEO, security and testing", () => {
  const plan = Core.createPlan("یک سایت فروشگاهی واکنش‌گرا بساز و امنیت و SEO را بررسی کن.");
  const types = plan.tasks.map((task) => task.type);
  for (const type of ["ui", "frontend", "seo", "security", "testing"]) {
    assert.ok(types.includes(type), "missing task type: " + type);
  }
});

test("image requests produce a visual task but do not claim an image provider is connected", () => {
  const plan = Core.createPlan("برای مقاله چند تصویر و اینفوگرافیک مناسب تولید کن.");
  const visual = plan.tasks.find((task) => task.type === "visual");
  assert.ok(visual);
  assert.match(visual.provider, /باید بررسی شود/);
  assert.equal(plan.executionMode, "simulation-only");
});

test("token figures are explicitly heuristic and do not apply a fabricated discount", () => {
  const request = "Prepare a research report about renewable energy with references.";
  const planAggressive = Core.createPlan(request, { tokenMode: "aggressive" });
  const planOff = Core.createPlan(request, { tokenMode: "off" });
  assert.equal(planAggressive.estimateType, "heuristic");
  assert.equal(planAggressive.totalTokens, planOff.totalTokens);
  assert.ok(planAggressive.totalTokens > 0);
  assert.equal(planAggressive.costPolicy, "zero-cost-only");
});

test("difficulty stays in the supported 1..5 range", () => {
  assert.ok(Core.difficulty("ساده", 1) >= 1);
  assert.ok(Core.difficulty("یک پروژه حرفه‌ای و پیچیده", 5) <= 5);
});

test("approval fingerprint only passes when the planned inputs are unchanged", () => {
  assert.equal(Core.isPlanCurrent('{"request":"site","quality":"high"}', '{"request":"site","quality":"high"}'), true);
  assert.equal(Core.isPlanCurrent('{"request":"site","quality":"high"}', '{"request":"new site","quality":"high"}'), false);
  assert.equal(Core.isPlanCurrent("", ""), false);
});

test("provider recommendations remain unverified rather than promising free quota", () => {
  const plan = Core.createPlan("یک برنامه پایتون بساز و تست کن.");
  assert.ok(plan.tasks.every((task) => /هنوز متصل|باید بررسی شود/.test(task.provider)));
  assert.equal(plan.costPolicy, "zero-cost-only");
});

test("static UI references exist and planner core loads before the UI controller", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const html = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");
  const app = fs.readFileSync(path.join(__dirname, "../app.js"), "utf8");

  const requiredIds = [
    "requestInput", "quality", "tokenMode", "budget", "planBtn", "validation",
    "emptyState", "planView", "approvalBar", "approveBtn", "editBtn",
    "executionPanel", "executionStatus", "taskList", "finalBox", "exampleBtn", "planStatus"
  ];
  for (const id of requiredIds) {
    assert.match(html, new RegExp('id="' + id + '"'), "missing HTML id: " + id);
    assert.ok(app.includes('$("' + "#" + id + '")'), "app.js does not reference expected id: " + id);
  }

  const coreScript = html.indexOf('<script src="core.js"></script>');
  const appScript = html.indexOf('<script src="app.js"></script>');
  assert.ok(coreScript >= 0, "core.js script tag is missing");
  assert.ok(appScript > coreScript, "core.js must load before app.js");
});
