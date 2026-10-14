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


test("UI keeps build preview separate from execution and labels execution as simulation", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const vm = require("node:vm");
  const core = require("../core.js");
  const source = fs.readFileSync(path.join(__dirname, "../app.js"), "utf8");
  const queue = [];
  let nextTimerId = 1;

  class FakeClassList {
    constructor(hidden = false) { this.values = new Set(hidden ? ["hidden"] : []); }
    add(value) { this.values.add(value); }
    remove(value) { this.values.delete(value); }
    contains(value) { return this.values.has(value); }
  }

  class FakeElement {
    constructor(id = "") {
      this.id = id;
      this.value = "";
      this.textContent = "";
      this.innerHTML = "";
      this.dataset = {};
      this.handlers = {};
      this.classList = new FakeClassList(["planView", "approvalBar", "executionPanel"].includes(id));
      this.children = [];
      this.statusElement = null;
    }
    addEventListener(name, fn) { this.handlers[name] = fn; }
    dispatch(name) { if (this.handlers[name]) this.handlers[name]({ target: this }); }
    focus() {}
    appendChild(child) { this.children.push(child); }
    querySelector(selector) {
      if (selector === ".state") return this.statusElement;
      return null;
    }
  }

  const elements = {};
  const ids = ["requestInput", "quality", "tokenMode", "budget", "validation", "planView",
    "approvalBar", "executionPanel", "emptyState", "planStatus", "executionStatus",
    "taskList", "finalBox", "planBtn", "approveBtn", "editBtn", "exampleBtn"];
  ids.forEach((id) => { elements[id] = new FakeElement(id); });
  elements.quality.value = "high";
  elements.tokenMode.value = "aggressive";
  elements.budget.value = "zero";

  const document = {
    querySelector(selector) {
      const id = selector.startsWith("#") ? selector.slice(1) : selector;
      if (id.startsWith("run-")) {
        return elements.taskList.children.find((child) => child.id === id) || null;
      }
      return elements[id] || null;
    },
    createElement() {
      const el = new FakeElement();
      Object.defineProperty(el, "id", {
        get() { return this._id || ""; },
        set(value) { this._id = value; }
      });
      const originalAdd = el.addEventListener.bind(el);
      el.addEventListener = originalAdd;
      return el;
    },
    querySelectorAll() { return []; }
  };
  const originalAppend = elements.taskList.appendChild.bind(elements.taskList);
  elements.taskList.appendChild = (child) => {
    if (!child.statusElement) {
      child.statusElement = new FakeElement();
      child.statusElement.className = "state running";
      child.statusElement.textContent = "در صف شبیه‌سازی";
      child.querySelector = (selector) => selector === ".state" ? child.statusElement : null;
    }
    originalAppend(child);
  };

  const setTimeoutFake = (fn) => {
    const id = nextTimerId++;
    queue.push({ id, fn });
    return id;
  };
  const clearTimeoutFake = (id) => {
    const index = queue.findIndex((item) => item.id === id);
    if (index >= 0) queue.splice(index, 1);
  };

  vm.runInNewContext(source, {
    document,
    window: { AIRouterCore: core },
    setTimeout: setTimeoutFake,
    clearTimeout: clearTimeoutFake
  });

  elements.requestInput.value = "یک پژوهش علمی درباره خواب با منابع معتبر تهیه کن و مقاله بنویس.";
  elements.planBtn.dispatch("click");
  assert.equal(elements.planView.classList.contains("hidden"), false);
  assert.equal(elements.approvalBar.classList.contains("hidden"), false);
  assert.equal(elements.executionPanel.classList.contains("hidden"), true);

  elements.approveBtn.dispatch("click");
  assert.equal(elements.executionPanel.classList.contains("hidden"), false);
  while (queue.length) queue.shift().fn();
  assert.match(elements.finalBox.innerHTML, /فقط شبیه‌سازی انجام شد/);
  assert.doesNotMatch(elements.finalBox.innerHTML, /پژوهش تولید شد|کد ساخته شد/);
});

test("changing request invalidates the previous preview and approval gate", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const vm = require("node:vm");
  const core = require("../core.js");
  const source = fs.readFileSync(path.join(__dirname, "../app.js"), "utf8");
  const elements = {};
  class FakeClassList {
    constructor(hidden = false) { this.values = new Set(hidden ? ["hidden"] : []); }
    add(value) { this.values.add(value); }
    remove(value) { this.values.delete(value); }
    contains(value) { return this.values.has(value); }
  }
  class FakeElement {
    constructor(id = "") { this.id=id; this.value=""; this.textContent=""; this.innerHTML=""; this.dataset={}; this.handlers={}; this.classList=new FakeClassList(["planView","approvalBar","executionPanel"].includes(id)); this.children=[]; }
    addEventListener(name,fn){this.handlers[name]=fn;}
    dispatch(name){if(this.handlers[name])this.handlers[name]({target:this});}
    focus(){}
    appendChild(child){this.children.push(child);}
  }
  ["requestInput","quality","tokenMode","budget","validation","planView","approvalBar","executionPanel","emptyState","planStatus","executionStatus","taskList","finalBox","planBtn","approveBtn","editBtn","exampleBtn"].forEach(id=>elements[id]=new FakeElement(id));
  elements.quality.value="high"; elements.tokenMode.value="aggressive"; elements.budget.value="zero";
  const document={querySelector(selector){return elements[selector.replace(/^#/,"")]||null;},createElement(){return new FakeElement();},querySelectorAll(){return [];}};
  vm.runInNewContext(source,{document,window:{AIRouterCore:core},setTimeout:()=>1,clearTimeout:()=>{}});
  elements.requestInput.value="یک پژوهش علمی درباره خواب با منابع معتبر تهیه کن.";
  elements.planBtn.dispatch("click");
  assert.equal(elements.approvalBar.classList.contains("hidden"),false);
  elements.requestInput.value="درخواست کاملاً متفاوتی برای سایت فروشگاهی";
  elements.requestInput.dispatch("input");
  assert.equal(elements.approvalBar.classList.contains("hidden"),true);
  assert.equal(elements.planView.classList.contains("hidden"),true);
  elements.approveBtn.dispatch("click");
  assert.equal(elements.executionPanel.classList.contains("hidden"),true);
});
