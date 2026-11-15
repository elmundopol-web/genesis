// Maneja Chrome sin ventana por el protocolo de depuración, sin dependencias.
// Uso: node herramientas/cdp.mjs plan.json
// El plan es una lista de pasos: {ir}, {esperar: expr}, {js: expr}, {clic: selector},
// {pausa: ms}, {foto: ruta, calidad}, {fotogramas: n, cada: ms, ruta: "x-%02d.jpg", js?: expr antes de cada uno}.
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const plan = JSON.parse(readFileSync(process.argv[2], "utf8"));
const CHROME = plan.chrome || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const puerto = 9300 + Math.floor(Math.random() * 500);
const perfil = mkdtempSync(join(tmpdir(), "genesis-cdp-"));
const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${puerto}`, `--user-data-dir=${perfil}`,
  `--window-size=${plan.ancho || 1440},${plan.alto || 900}`, "--hide-scrollbars", "--mute-audio",
  "--enable-gpu-rasterization", "--ignore-gpu-blocklist", "about:blank",
], { stdio: "ignore" });

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
let destino;
for (let i = 0; i < 80 && !destino; i++) {
  await dormir(150);
  try {
    const lista = await (await fetch(`http://127.0.0.1:${puerto}/json`)).json();
    destino = lista.find((t) => t.type === "page");
  } catch {}
}
if (!destino) throw new Error("Chrome no respondió");
const ws = new WebSocket(destino.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let n = 0;
const pendientes = new Map();
const errores = [];
ws.addEventListener("message", (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pendientes.has(d.id)) {
    pendientes.get(d.id)(d);
    pendientes.delete(d.id);
  } else if (d.method === "Runtime.exceptionThrown") {
    errores.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
  } else if (d.method === "Runtime.consoleAPICalled" && d.params.type === "error") {
    errores.push(d.params.args.map((a) => a.value ?? a.description).join(" "));
  }
});
const cdp = (method, params = {}) => new Promise((r, x) => {
  const id = ++n;
  pendientes.set(id, (d) => (d.error ? x(new Error(method + ": " + d.error.message)) : r(d.result)));
  ws.send(JSON.stringify({ id, method, params }));
});
const js = async (expr) => {
  const r = await cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(expr + " → " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
  return r.result.value;
};
const foto = async (ruta, calidad = 88) => {
  const r = await cdp("Page.captureScreenshot", { format: "jpeg", quality: calidad });
  writeFileSync(ruta, Buffer.from(r.data, "base64"));
};
await cdp("Page.enable");
await cdp("Runtime.enable");
await cdp("Emulation.setDeviceMetricsOverride", { width: plan.ancho || 1440, height: plan.alto || 900, deviceScaleFactor: 1, mobile: false });
const salida = {};
try {
  for (const paso of plan.pasos) {
    if (paso.ir) {
      await cdp("Page.navigate", { url: paso.ir });
      await dormir(400);
    } else if (paso.esperar) {
      const limite = Date.now() + (paso.limite || 20000);
      while (!(await js(paso.esperar).catch(() => false))) {
        if (Date.now() > limite) throw new Error("tiempo agotado esperando " + paso.esperar);
        await dormir(100);
      }
    } else if (paso.js) {
      const v = await js(paso.js);
      if (paso.guardar) salida[paso.guardar] = v;
    } else if (paso.clic) {
      await js(`document.querySelector(${JSON.stringify(paso.clic)}).click()`);
    } else if (paso.pausa) {
      await dormir(paso.pausa);
    } else if (paso.foto) {
      await foto(paso.foto, paso.calidad);
    } else if (paso.fotogramas) {
      for (let i = 0; i < paso.fotogramas; i++) {
        if (paso.antes) await js(paso.antes);
        const t0 = Date.now();
        await foto(paso.ruta.replace("%03d", String(i).padStart(3, "0")), paso.calidad || 80);
        await dormir(Math.max(0, paso.cada - (Date.now() - t0)));
      }
    }
  }
} finally {
  salida.errores = errores;
  console.log(JSON.stringify(salida));
  ws.close();
  chrome.kill();
}
