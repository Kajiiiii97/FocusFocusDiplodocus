// Tells the Focus Cat desktop app which tab is active, and closes it when the cat says so.
// Nothing leaves your computer: the only address this talks to is 127.0.0.1.

const ENDPOINT = "http://127.0.0.1:47321/report";
const EVERY_MS = 2000;

let firefoxFocused = true;
let inFlight = false;

async function report() {
  if (inFlight) return;
  inFlight = true;
  try {
    let tab = null;
    try {
      [tab] = await browser.tabs.query({ active: true, lastFocusedWindow: true });
    } catch (e) {
      tab = null;
    }
    const body = {
      url: tab ? tab.url || "" : "",
      tabId: tab ? tab.id : null,
      focused: firefoxFocused && !!tab,
    };
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Focus-Cat": "1" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (Number.isInteger(data.close)) {
      await browser.tabs.remove(data.close).catch(() => {});
    }
  } catch (e) {
    // The cat app isn't running. Try again next time.
  } finally {
    inFlight = false;
  }
}

browser.windows.onFocusChanged.addListener((windowId) => {
  firefoxFocused = windowId !== browser.windows.WINDOW_ID_NONE;
  report();
});
browser.tabs.onActivated.addListener(() => report());
browser.tabs.onUpdated.addListener((tabId, info, tab) => {
  if (tab.active && info.url) report();
});

browser.windows.getLastFocused().then((win) => {
  firefoxFocused = !!(win && win.focused);
}).catch(() => {});

setInterval(report, EVERY_MS);
report();
