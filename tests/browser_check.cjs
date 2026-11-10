// Copyright 2026 Alessio Mattoccia
// SPDX-License-Identifier: Apache-2.0
"use strict";

const assert = require("node:assert/strict");
const { chromium } = require(process.env.DP_PLAYWRIGHT_MODULE || "playwright");

async function run() {
  const url = process.argv[2] || "http://127.0.0.1:8791/";
  const browser = await chromium.launch({headless: true, executablePath: process.env.DP_CHROMIUM || undefined});
  const page = await browser.newPage({viewport: {width: 1440, height: 980}, acceptDownloads: true});
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));
  try {
    await page.goto(url);
    await page.waitForFunction(() => document.getElementById("count-labs").textContent === "4");
    await page.waitForFunction(() => document.getElementById("coverage-formula").textContent.includes("952749326350107946598400000000"));
    await page.locator("#coverage-choices input[value='riemann.hertlein2']").uncheck();
    await page.waitForFunction(() => document.getElementById("coverage-formula").textContent.includes("1048576"));
    await page.locator("#coverage-choices input[value='riemann.hertlein2']").check();
    await page.locator("#kind-filter").selectOption("counterexample");
    await page.locator("#search-filter").fill("Controesempio alla commutazione");
    await page.getByRole("button", {name: /Controesempio alla commutazione delle medie/}).click();
    const sheet = page.getByRole("dialog");
    await sheet.waitFor();
    assert.match(await sheet.textContent(), /1\/24/);
    assert.match(await sheet.textContent(), /Grafo delle deduzioni/);
    assert.match(await sheet.textContent(), /DPR-003/);
    await page.getByRole("button", {name: "Chiudi scheda"}).click();
    await page.getByRole("button", {name: "Apri PT-002"}).click();
    await sheet.getByRole("table", {name: "Matrice simmetrica di Yukawa"}).waitFor();
    assert.match(await sheet.textContent(), /b\*\*2\*c\*\*2\*d/);
    assert.match(await sheet.textContent(), /rango generico 5/);
    await page.getByRole("button", {name: "Chiudi scheda"}).click();
    await page.locator("#search-filter").fill("");
    await page.locator("#kind-filter").selectOption("");
    const firstReport = page.locator("#runs a").first();
    await firstReport.waitFor();
    const download = page.waitForEvent("download");
    await firstReport.click();
    assert.match((await download).suggestedFilename(), /^dynamic-proof-\d+\.md$/);
    if (process.env.DP_SCREENSHOT) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({path: process.env.DP_SCREENSHOT, fullPage: false});
    }
    await page.setViewportSize({width: 390, height: 844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true);
    assert.deepEqual(failures, []);
    process.stdout.write("Dashboard verificata in Chromium · copertura, filtri, scheda, grafo, download e layout mobile\n");
  } finally {
    await browser.close();
  }
}

run().catch((error) => { console.error(error); process.exitCode = 1; });
