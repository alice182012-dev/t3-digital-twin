const APP = "http://100.67.84.55:8082";
const HOOK = `(() => { window.__t = {}; const iv = setInterval(() => { if (!window.__t.canvas && document.querySelector("canvas")) window.__t.canvas = Math.round(performance.now()); }, 20); setTimeout(() => clearInterval(iv), 30000); })()`;

async function load(label, network, settleMs) {
  const pg = await openTab("about:blank");
  await pg._sendToTarget("Page.addScriptToEvaluateOnNewDocument", { source: HOOK });
  await pg._sendToTarget("Network.enable", {});
  await pg._sendToTarget("Network.setCacheDisabled", { cacheDisabled: true });
  if (network) await pg._sendToTarget("Network.emulateNetworkConditions", network);
  await pg.goto(APP + "/");
  await sleep(settleMs);
  const r = await pg.evaluate(() => {
    const res = performance.getEntriesByType("resource");
    const fl = res.filter(r => r.name.includes("/flood-extent/"));
    const s = x => (x / 1000).toFixed(1);
    return `first map ${s(window.__t.canvas)} s, flood layer first tile ${s(Math.min(...fl.map(r => r.responseEnd)))} s, last tile ${s(Math.max(...fl.map(r => r.responseEnd)))} s, ${fl.length} tiles, ${Math.round(fl.reduce((a, r) => a + (r.transferSize || 0), 0) / 1024)} KB`;
  });
  await closeTab(pg);
  console.log(label + ": " + r);
}

async function noConnection(profile) {
  const pg = await openTab("about:blank");
  await pg._sendToTarget("Network.enable", {});
  await pg._sendToTarget("Network.setCacheDisabled", { cacheDisabled: true });
  await pg.goto(`${APP}/?point=20.999844%2C105.742304&point=21.004652%2C105.752604&profile=${profile}`);
  const r = await pg.evaluate(async () => {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    let box = null;
    const start = performance.now();
    while (performance.now() - start < 40000) {
      const b = document.querySelector("[class*=sidebarOpenButton]");
      if (b) b.click();
      if (/No safe route available/i.test(document.body.innerText)) { box = performance.now(); break; }
      await sleep(50);
    }
    const routes = performance.getEntriesByType("resource").filter(r => /\/route/.test(r.name));
    return { box: box === null ? "never" : (box / 1000).toFixed(1) + " s", requests: routes.length, slowest: (Math.max(...routes.map(r => r.duration)) / 1000).toFixed(2) + " s" };
  });
  await closeTab(pg);
  console.log(`${profile}: yellow box at ${r.box} after page start, ${r.requests} /route requests, slowest ${r.slowest}`);
}

console.log("1. Cold page load (cache off), no throttling");
for (let i = 1; i <= 3; i++) await load("   run " + i, null, 6000);
console.log("2. Cold page load, emulated regular 4G (9 Mbit/s, 170 ms)");
for (let i = 1; i <= 2; i++) await load("   run " + i, { offline: false, latency: 170, downloadThroughput: 9e6 / 8, uploadThroughput: 4.5e6 / 8 }, 9000);
console.log("3. Wait for the yellow No safe route box, pair 20.999844,105.742304 to 21.004652,105.752604");
for (const p of ["motorbike", "truck"]) for (let i = 1; i <= 3; i++) await noConnection(p);
console.log("GSTACK_STEP_OK");
