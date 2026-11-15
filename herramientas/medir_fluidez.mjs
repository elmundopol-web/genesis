// GENESIS F2.5 · mide la fluidez real del visor en Chrome sin ventana (protocolo de depuración).
// Uso, con un visor ya abierto sobre una partida de prueba (nunca una de partidas/):
//   node herramientas/medir_fluidez.mjs "http://127.0.0.1:8765/#sinvelo&habitante=17" 1440 900
// Pone el tiempo en marcha a varias velocidades y anota intervalos entre cuadros y coste de dibujo.
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const [url, ancho = "1440", alto = "900"] = process.argv.slice(2);
const puerto = 9333 + Math.floor(Math.random() * 300);
const perfil = mkdtempSync(join(tmpdir(), "gen-med-"));
const chrome = spawn("C:/Program Files/Google/Chrome/Application/chrome.exe", [
  "--headless=new", `--remote-debugging-port=${puerto}`, `--user-data-dir=${perfil}`, `--window-size=${ancho},${alto}`,
  "--use-angle=d3d11", "--ignore-gpu-blocklist", "--enable-gpu-rasterization", "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
const espera = (ms) => new Promise((r) => setTimeout(r, ms));
let objetivo;
for (let i = 0; i < 50 && !objetivo; i++) {
  await espera(200);
  try { objetivo = (await (await fetch(`http://127.0.0.1:${puerto}/json`)).json()).find((t) => t.type === "page"); } catch {}
}
const ws = new WebSocket(objetivo.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let n = 0;
const pendientes = new Map();
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pendientes.has(d.id)) { pendientes.get(d.id)(d); pendientes.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const id = ++n; pendientes.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const evalua = async (expr) => { const r = await cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails)); return r.result.result.value; };
await cdp("Page.enable");
await cdp("Page.navigate", { url });
for (let i = 0; i < 150; i++) { await espera(200); try { if (await evalua("!!(window.genesis && window.genesis.mundo && window.genesis.mundo.listo)")) break; } catch {} }
await espera(1500);
const gpu = await evalua(`(() => { const c = document.createElement("canvas").getContext("webgl"); const e = c && c.getExtension("WEBGL_debug_renderer_info"); return e ? c.getParameter(e.UNMASKED_RENDERER_WEBGL) : "?"; })()`);
const medir = `async (velocidad, segundos, vista) => {
  const m = window.genesis.mundo;
  if (vista) { Object.assign(m.meta, { x: vista[0], y: vista[1], z: vista[2] * m.dpr }); m.libre = false; } else m.encajar(true);
  const ctl = (o) => fetch("/api/control", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(o) });
  if (velocidad) await ctl({ accion: "velocidad", velocidad });
  await new Promise((r) => setTimeout(r, 900));
  const orig = Object.getPrototypeOf(m)._cuadro;
  const costes = [];
  m._cuadro = function (t) { const a = performance.now(); orig.call(this, t); costes.push(performance.now() - a); };
  const largas = [];
  const obs = new PerformanceObserver((l) => { for (const e of l.getEntries()) largas.push(e.duration); });
  try { obs.observe({ entryTypes: ["longtask"] }); } catch (e) {}
  if (velocidad) await ctl({ accion: "reanudar" });
  const tick0 = (await (await fetch("/api/estado")).json()).tick;
  const intervalos = [];
  let previo = performance.now();
  const fin = previo + segundos * 1000;
  await new Promise((res) => { const f = (t) => { intervalos.push(t - previo); previo = t; if (t < fin) requestAnimationFrame(f); else res(); }; requestAnimationFrame(f); });
  if (velocidad) await ctl({ accion: "pausar" });
  const tick1 = (await (await fetch("/api/estado")).json()).tick;
  obs.disconnect();
  delete m._cuadro;
  intervalos.shift();
  const s = [...intervalos].sort((a, b) => a - b);
  const c = [...costes].sort((a, b) => a - b);
  const q = (a, p) => a.length ? +a[Math.min(a.length - 1, Math.floor(a.length * p))].toFixed(1) : 0;
  return { horas: tick1 - tick0, fps: +(intervalos.length / segundos).toFixed(1),
    intervalo: { p50: q(s, 0.5), p95: q(s, 0.95), p99: q(s, 0.99), max: q(s, 1) }, mas20ms: s.filter((x) => x > 20).length, mas34ms: s.filter((x) => x > 34).length, mas50ms: s.filter((x) => x > 50).length,
    dibujo: { p50: q(c, 0.5), p95: q(c, 0.95), max: q(c, 1) }, tareasLargas: largas.length, tareaMax: largas.length ? +Math.max(...largas).toFixed(0) : 0 };
}`;
const casos = JSON.parse(process.env.CASOS || '[["parado",0,[22.5,7,62]],["cerca",24,[22.5,7,62]],["medio",24,[24,10,26]],["mundo",24,null],["mundo-rapido",480,null],["cerca-rapido",480,[22.5,7,62]]]');
const salida = { url, ventana: `${ancho}x${alto}`, gpu };
if (process.env.EXTRA) salida.extra = await evalua(process.env.EXTRA);
for (const [nombre, vel, vista] of casos) salida[nombre] = await evalua(`(${medir})(${vel}, ${process.env.SEG || 10}, ${JSON.stringify(vista)})`);
console.log(JSON.stringify(salida, null, 1));
ws.close();
chrome.kill();
process.exit(0);
