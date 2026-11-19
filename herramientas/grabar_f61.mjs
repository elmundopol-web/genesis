// F6.1 · Graba el visor en vídeo con Chrome sin ventana, sin dependencias (Node 22+ y ffmpeg).
// Uso: node herramientas/grabar_f61.mjs plan.json
// Pasos del plan, como en cdp.mjs: {ir}, {esperar: expr}, {js: expr, guardar?}, {clic: selector},
// {pausa: ms}, {foto: ruta}; y además {grabar: ruta.mp4, hasta: expr | ms: n, fotos?: [[ms, ruta]]}:
// guarda los fotogramas que pinta Chrome (Page.startScreencast) con su hora real y los monta
// a 30 imágenes por segundo, de modo que el vídeo dura lo mismo que lo que se vio.
import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const plan = JSON.parse(readFileSync(process.argv[2], "utf8"));
const CHROME = plan.chrome || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const ANCHO = plan.ancho || 1440, ALTO = plan.alto || 900;
const puerto = 9300 + Math.floor(Math.random() * 500);
const perfil = mkdtempSync(join(tmpdir(), "genesis-grabar-"));
const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${puerto}`, `--user-data-dir=${perfil}`,
  `--window-size=${ANCHO},${ALTO}`, "--hide-scrollbars", "--mute-audio",
  "--enable-gpu-rasterization", "--ignore-gpu-blocklist", "about:blank",
], { stdio: "ignore" });

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
let destino;
for (let i = 0; i < 80 && !destino; i++) {
  await dormir(150);
  try {
    destino = (await (await fetch(`http://127.0.0.1:${puerto}/json`)).json()).find((t) => t.type === "page");
  } catch {}
}
if (!destino) throw new Error("Chrome no respondió");
const ws = new WebSocket(destino.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let n = 0;
const pendientes = new Map();
const errores = [];
let alFotograma = null;
ws.addEventListener("message", (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pendientes.has(d.id)) {
    pendientes.get(d.id)(d);
    pendientes.delete(d.id);
  } else if (d.method === "Page.screencastFrame") {
    if (alFotograma) alFotograma(d.params);
  } else if (d.method === "Runtime.exceptionThrown") {
    errores.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
  } else if (d.method === "Runtime.consoleAPICalled" && (d.params.type === "error" || d.params.type === "warning")) {
    errores.push(d.params.type + ": " + d.params.args.map((a) => a.value ?? a.description).join(" "));
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
const foto = async (ruta, calidad = 90) => {
  const r = await cdp("Page.captureScreenshot", { format: ruta.endsWith(".png") ? "png" : "jpeg", quality: calidad });
  writeFileSync(ruta, Buffer.from(r.data, "base64"));
};

async function grabar(paso) {
  const carpeta = mkdtempSync(join(tmpdir(), "genesis-video-"));
  const cuadros = [];
  const fotos = (paso.fotos || []).slice().sort((a, b) => a[0] - b[0]);
  let t0 = null;
  alFotograma = (p) => {
    const t = p.metadata.timestamp * 1000;
    if (t0 == null) t0 = t;
    const ruta = join(carpeta, `f${String(cuadros.length).padStart(5, "0")}.jpg`);
    writeFileSync(ruta, Buffer.from(p.data, "base64"));
    cuadros.push([t - t0, ruta]);
    cdp("Page.screencastFrameAck", { sessionId: p.sessionId }).catch(() => {});
  };
  // Por defecto, capturas seguidas: el screencast de Chrome sin ventana puede dejar de entregar
  // fotogramas a mitad de grabación. Con {"screencast": true} se usa igualmente.
  if (paso.screencast) await cdp("Page.startScreencast", { format: "jpeg", quality: 88, maxWidth: ANCHO, maxHeight: ALTO, everyNthFrame: 1 });
  const inicio = Date.now();
  const limite = inicio + (paso.maximo || 120000);
  let porFotos = !paso.screencast;
  if (porFotos) t0 = Date.now();
  for (;;) {
    const ms = Date.now() - inicio;
    if (!porFotos && ms > 1500 && !cuadros.length) {
      porFotos = true; // sin ventana, algunas versiones no emiten el screencast: capturas seguidas
      await cdp("Page.stopScreencast");
      alFotograma = null;
      t0 = Date.now();
    }
    if (porFotos) {
      const r = await cdp("Page.captureScreenshot", { format: "jpeg", quality: 85 });
      const ruta = join(carpeta, `f${String(cuadros.length).padStart(5, "0")}.jpg`);
      writeFileSync(ruta, Buffer.from(r.data, "base64"));
      cuadros.push([Date.now() - t0, ruta]);
    }
    while (fotos.length && ms >= fotos[0][0]) await foto(fotos.shift()[1]);
    if (paso.ms && ms >= paso.ms) break;
    if (paso.hasta && (await js(paso.hasta).catch(() => false))) break;
    if (Date.now() > limite) break;
    if (!porFotos) await dormir(50);
  }
  if (paso.cola && !porFotos) await dormir(paso.cola);
  if (paso.cola && porFotos) {
    const fin = Date.now() + paso.cola;
    while (Date.now() < fin) {
      const r = await cdp("Page.captureScreenshot", { format: "jpeg", quality: 85 });
      const ruta = join(carpeta, `f${String(cuadros.length).padStart(5, "0")}.jpg`);
      writeFileSync(ruta, Buffer.from(r.data, "base64"));
      cuadros.push([Date.now() - t0, ruta]);
    }
  }
  if (!porFotos) await cdp("Page.stopScreencast");
  alFotograma = null;
  // concat de ffmpeg con la duración real de cada fotograma
  const lista = ["ffconcat version 1.0"];
  cuadros.sort((a, b) => a[0] - b[0]);
  for (let i = 0; i < cuadros.length; i++) {
    let dur = i + 1 < cuadros.length ? (cuadros[i + 1][0] - cuadros[i][0]) / 1000 : 1 / 30;
    if (!Number.isFinite(dur) || dur < 0.001) dur = 0.001;
    lista.push(`file '${cuadros[i][1].replaceAll("\\", "/")}'`, `duration ${dur.toFixed(4)}`);
  }
  if (cuadros.length) lista.push(`file '${cuadros.at(-1)[1].replaceAll("\\", "/")}'`);
  writeFileSync(join(carpeta, "lista.txt"), lista.join("\n"));
  const r = spawnSync(plan.ffmpeg || "ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", join(carpeta, "lista.txt"),
    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", String(paso.crf || 20), "-preset", "medium", "-movflags", "+faststart", paso.grabar],
    { encoding: "utf8" });
  if (r.status !== 0) throw new Error(`ffmpeg (${cuadros.length} fotogramas, ${carpeta}): ` + r.stderr);
  const total = cuadros.length ? cuadros.at(-1)[0] / 1000 : 0;
  rmSync(carpeta, { recursive: true, force: true });
  return { fotogramas: cuadros.length, segundos: Number(total.toFixed(2)), fps: Number((cuadros.length / Math.max(total, 0.001)).toFixed(1)) };
}

await cdp("Page.enable");
await cdp("Runtime.enable");
await cdp("Emulation.setDeviceMetricsOverride", { width: ANCHO, height: ALTO, deviceScaleFactor: plan.escala || 1, mobile: false });
const salida = {};
try {
  for (const paso of plan.pasos) {
    if (paso.ir) {
      await cdp("Page.navigate", { url: paso.ir });
      await dormir(400);
    } else if (paso.esperar) {
      const limite = Date.now() + (paso.limite || 30000);
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
    } else if (paso.grabar) {
      salida[paso.grabar] = await grabar(paso);
    }
  }
} finally {
  salida.errores = errores;
  console.log(JSON.stringify(salida, null, 1));
  ws.close();
  chrome.kill();
}
