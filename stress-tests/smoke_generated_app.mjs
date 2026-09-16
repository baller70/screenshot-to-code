#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const puppeteerModuleUrl = pathToFileURL(
  path.resolve(process.cwd(), "node_modules/puppeteer/lib/esm/puppeteer/puppeteer.js")
).href;
const { default: puppeteer } = await import(puppeteerModuleUrl);

function parseArgs(argv) {
  const args = { width: 1440, height: 1800 };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--html") args.html = argv[++index];
    else if (arg === "--output") args.output = argv[++index];
    else if (arg === "--width") args.width = Number(argv[++index]);
    else if (arg === "--height") args.height = Number(argv[++index]);
  }
  if (!args.html || !args.output) {
    throw new Error("Usage: smoke_generated_app.mjs --html file.html --output report.json");
  }
  return args;
}

function browserExecutablePath() {
  if (process.env.PUPPETEER_EXECUTABLE_PATH) return process.env.PUPPETEER_EXECUTABLE_PATH;
  return [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].find((candidate) => fs.existsSync(candidate));
}

async function routeRegistry(page) {
  return page.evaluate(() => {
    const registry = globalThis.MIRROR_ROUTE_REGISTRY;
    if (Array.isArray(registry)) {
      return registry
        .map((entry) => ({
          name: String(entry.label || entry.route || "route"),
          route: String(entry.route || ""),
        }))
        .filter((entry) => entry.route);
    }
    const seen = new Set();
    return Array.from(document.querySelectorAll("a[href^='#']"))
      .map((link) => ({
        name: link.textContent.trim() || link.getAttribute("href"),
        route: link.getAttribute("href"),
      }))
      .filter((entry) => {
        if (!entry.route || entry.route === "#" || seen.has(entry.route)) return false;
        seen.add(entry.route);
        return true;
      });
  });
}

async function fillForms(page) {
  return page.evaluate(() => {
    const results = [];
    for (const [formIndex, form] of Array.from(document.querySelectorAll("form")).entries()) {
      for (const input of Array.from(form.querySelectorAll("input, textarea"))) {
        const name = input.getAttribute("name") || "";
        const type = input.getAttribute("type") || "text";
        if (type === "email" || name.toLowerCase().includes("email")) input.value = "test@example.com";
        else if (type === "tel" || name.toLowerCase().includes("phone")) input.value = "555-0100";
        else input.value = "Test Value";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const submit = form.querySelector("button[type='submit'], button:not([type]), input[type='submit']");
      results.push({
        formIndex,
        fields: Array.from(form.querySelectorAll("[name]")).map((field) => field.getAttribute("name")),
        hasSubmit: Boolean(submit),
      });
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    }
    return results;
  });
}

const args = parseArgs(process.argv.slice(2));
const browser = await puppeteer.launch({
  headless: "new",
  executablePath: browserExecutablePath(),
  args: ["--no-sandbox", "--disable-setuid-sandbox"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: args.width, height: args.height, deviceScaleFactor: 1 });
  const baseUrl = pathToFileURL(path.resolve(args.html)).toString();
  await page.goto(baseUrl, { waitUntil: "networkidle0" });
  await page.evaluate(() => document.fonts?.ready);

  const routes = await routeRegistry(page);
  const routeResults = [];
  for (const route of routes) {
    await page.goto(`${baseUrl}${route.route}`, { waitUntil: "networkidle0" });
    await page.evaluate(() => document.fonts?.ready);
    const metrics = await page.evaluate(() => ({
      hash: window.location.hash,
      activePageId: document.querySelector(".page.active")?.id || null,
      textLength: document.body.innerText.trim().length,
      mirrorNodeCount: document.querySelectorAll("[data-mirror-id]").length,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    routeResults.push({
      ...route,
      ...metrics,
      ok: metrics.textLength > 0 && metrics.scrollWidth <= metrics.clientWidth,
    });
  }

  const formResults = await fillForms(page);
  const failures = [
    ...routeResults
      .filter((route) => !route.ok)
      .map((route) => `Route failed smoke check: ${route.route}`),
    ...formResults
      .filter((form) => !form.hasSubmit)
      .map((form) => `Form ${form.formIndex} has no submit control`),
  ];

  const report = {
    html: args.html,
    routeCount: routeResults.length,
    formCount: formResults.length,
    routes: routeResults,
    forms: formResults,
    failures,
    ok: failures.length === 0,
  };
  fs.writeFileSync(args.output, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = report.ok ? 0 : 1;
} finally {
  await browser.close();
}
