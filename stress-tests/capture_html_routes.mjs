#!/usr/bin/env node
import path from "node:path";
import { pathToFileURL } from "node:url";
import fs from "node:fs";

const puppeteerModuleUrl = pathToFileURL(
  path.resolve(process.cwd(), "node_modules/puppeteer/lib/esm/puppeteer/puppeteer.js")
).href;
const { default: puppeteer } = await import(puppeteerModuleUrl);

function browserExecutablePath() {
  if (process.env.PUPPETEER_EXECUTABLE_PATH) {
    return process.env.PUPPETEER_EXECUTABLE_PATH;
  }
  const candidates = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ];
  return candidates.find((candidate) => fs.existsSync(candidate));
}

function parseArgs(argv) {
  const args = {
    width: 1440,
    height: 1800,
    routes: [],
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--html") args.html = argv[++index];
    else if (arg === "--output-dir") args.outputDir = argv[++index];
    else if (arg === "--route") args.routes.push(argv[++index]);
    else if (arg === "--width") args.width = Number(argv[++index]);
    else if (arg === "--height") args.height = Number(argv[++index]);
  }
  if (!args.html || !args.outputDir || args.routes.length === 0) {
    throw new Error(
      "Usage: capture_html_routes.mjs --html file.html --output-dir dir --route name:#hash"
    );
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));
const browser = await puppeteer.launch({
  headless: "new",
  executablePath: browserExecutablePath(),
  args: ["--no-sandbox", "--disable-setuid-sandbox"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({
    width: args.width,
    height: args.height,
    deviceScaleFactor: 1,
  });

  const baseUrl = pathToFileURL(path.resolve(args.html)).toString();
  const results = [];
  for (const route of args.routes) {
    const [name, hash] = route.split(":", 2);
    if (!name || !hash) throw new Error(`Invalid route: ${route}`);

    await page.goto(`${baseUrl}${hash}`, { waitUntil: "networkidle0" });
    await page.evaluate(() => document.fonts?.ready);
    await page.waitForFunction(
      () => document.body && document.body.innerText.trim().length > 0,
      { timeout: 10000 }
    );

    const outputPath = path.join(args.outputDir, `${name}.png`);
    await page.screenshot({ path: outputPath, fullPage: true });
    const metrics = await page.evaluate(() => ({
      title: document.title,
      hash: window.location.hash,
      textLength: document.body.innerText.length,
      mirrorNodeCount: document.querySelectorAll("[data-mirror-id]").length,
      activePageId: document.querySelector(".page.active")?.id || null,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      scrollHeight: document.documentElement.scrollHeight,
    }));
    results.push({ name, hash, outputPath, ...metrics });
  }

  console.log(JSON.stringify({ html: args.html, viewport: args, results }, null, 2));
} finally {
  await browser.close();
}
