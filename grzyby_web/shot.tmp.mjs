import { chromium } from "@playwright/test";
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1400, height: 900 } });
const bad = [];
p.on("console", (m) => { if (m.type() === "error") bad.push(m.text().slice(0, 150)); });
p.on("response", (r) => { if (r.url().includes("/api/") && r.status() >= 400) bad.push(r.status() + " " + r.url()); });
await p.goto("http://localhost:13000/"); await p.waitForTimeout(12000);
console.log(JSON.stringify(bad.slice(0, 8), null, 1));
console.log("has Platforma:", await p.getByText("Platforma").count());
await p.screenshot({ path: "/tmp/claude-1000/-home-maniumek-repos-automat-lokumwyceny/75d281de-1c22-4d5d-adf1-d619a6824a48/scratchpad/hub.png", fullPage: true }); await b.close();
