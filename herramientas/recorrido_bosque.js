// Expresión para capturas_f44.py. Solo mueve la cámara del visor abierto por la prueba.
(async () => {
  const g = genesis.mundo;
  const cuadro = document.createElement("canvas");
  cuadro.width = 960;
  cuadro.height = 600;
  const ctx = cuadro.getContext("2d");
  const flujo = cuadro.captureStream(30);
  const video = new MediaRecorder(flujo, { mimeType: "video/webm;codecs=vp9", videoBitsPerSecond: 5500000 });
  const partes = [];
  video.ondataavailable = e => partes.push(e.data);
  const fin = new Promise(ok => video.onstop = ok);
  const inicio = performance.now();
  const origen = [g.cam.x, g.cam.y];
  const tickInicial = genesis.estado.estado.tick;
  const cuadros = [];
  video.start();
  document.querySelector("#marcha").click();
  await new Promise(ok => {
    function avanzar(t) {
      cuadros.push(t);
      const k = Math.max(0, Math.min(1, (t - inicio - 700) / 7400));
      const s = k * k * (3 - 2 * k);
      g.meta.x = origen[0] + (29.5 - origen[0]) * s;
      g.meta.y = origen[1] + (21 - origen[1]) * s + Math.sin(Math.PI * s) * 1.4;
      ctx.drawImage(g.lienzo, (g.lienzo.width - 960) / 2, (g.lienzo.height - 600) / 2,
                    960, 600, 0, 0, 960, 600);
      if (t - inicio < 8900) requestAnimationFrame(avanzar);
      else ok();
    }
    requestAnimationFrame(avanzar);
  });
  document.querySelector("#marcha").click();
  video.stop();
  await fin;
  flujo.getTracks().forEach(p => p.stop());
  window.clipBosque = new Blob(partes);
  const lapsos = cuadros.slice(1).map((t,i)=>t-cuadros[i]).sort((a,b)=>a-b);
  const gl = document.createElement("canvas").getContext("webgl");
  const ext = gl && gl.getExtension("WEBGL_debug_renderer_info");
  return { origen, destino: [g.cam.x, g.cam.y], tickInicial, tickFinal: genesis.estado.estado.tick,
    zoom: g.cam.z / g.dpr, navegador:navigator.userAgent, ventana:[innerWidth, innerHeight],
    gpu: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null,
    fpsConGrabacion: +(lapsos.length*1000/(cuadros.at(-1)-cuadros[0])).toFixed(1),
    p95_ms: +lapsos[Math.floor(lapsos.length*.95)].toFixed(1) };
})()
