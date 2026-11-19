# ESTADO.md — Memoria de continuidad de GENESIS

Actualizado el 19 de noviembre de 2026. Entrada operativa en [AGENTS.md](AGENTS.md).
Memoria compartida para Claude, GPT-6.1 Sol, Terra, Astra u otros modelos.
Al retomar, contrasta este documento con Git; no necesitas conversaciones anteriores.

## Estado y fase activa

- Versión declarada: `0.6.3-f63`, en [genesis/__init__.py](genesis/__init__.py).
- Las nuevas partidas con reglas actuales incluyen los planes familiares F6.0, la percepción familiar F6.0.1, los tratos entre familias F6.2 y el carácter y los conflictos F6.3 sobre la conducta F4.3. Las anteriores pueden activar F6.0 con `ampliar --familias`, F6.0.1 con `ampliar --percepcion-familiar`, F6.2 con `ampliar --tratos-familia` o F6.3 con `ampliar --conflictos` en una copia.
  F5.0 solo si se pide con `--mente ID` (nueva o `ampliar`).
- **F6.3, personalidad, conflictos y peleas, entregada el 19/11/2026.** Esta actualización de `main` recoge las fases desarrolladas desde F4.4 hasta F6.3.
  Regla versionada `conflictos` (1 en partidas nuevas, 0 al cargar las anteriores) sobre los tratos F6.2, sin Ollama.
  Ocho dimensiones de carácter derivadas de los rasgos existentes (sin rasgo nuevo) cruzadas con los intereses del
  momento y la historia con cada persona: avisar o no, prórroga real del plazo, mantenerlo, pedir el adelanto de vuelta
  (comida real), buscar a otra persona, cumplir tarde; reclamar cara a cara con escalada reconocible y salidas en cada
  paso (explicar, disculparse, defenderse, marcharse, calmarse, apartarse, un tercero que calma o defiende), forcejeo
  breve con daño leve real; después distancia, disculpas aceptadas o no, rectificar, y decisiones distintas en el
  siguiente trato. Testigos con versión propia y fuente. Visor: escenas paso a paso en el mapa (poses nuevas
  `increpa` y `forcejea`), frases en Seguimiento, Historias enlazadas y carácter en la ficha.
  Libre: pelea en semilla 32 (horas 659–662) y disculpa que no basta en semilla 34 (876 y 896). Cadenas libres completas en semillas 34 (disculpa rechazada y, un otoño después, trato rechazado por el agravio) y 59 («ya van dos»).
  [Informe](docs/F6.3-ESTADO.md) · [Demo y clips](docs/f6.3/comparar.html).
- **F6.2, los primeros tratos entre familias, entregada y cerrada el 19/11/2026 sin commit (detenida aquí).**
  Dos hogares pueden pactar comida hoy (preferentemente peces) a cambio de ayuda para reparar un refugio mañana,
  solo con las reglas del motor y con Ollama apagado (`tratos_familia=1` en partidas nuevas; `0` por defecto en
  partidas guardadas anteriores para conservar su reproducción exacta). Transferencia atómica de comida una sola
  vez y reparación real con madera del mundo una sola vez. Tres desenlaces comprobados (cumplido, falta con
  cambio de plan del hogar y rechazo sin mover comida), separación epistémica sin omnisciencia (sin ver ni oír el
  motivo solo consta que la ayuda no llegó; ausencia, rechazo y engaño deliberado son hechos distintos) y segunda
  decisión cambiada por la historia con causa real (aceptar por confianza, pedir garantía o rechazar y buscar a
  otra persona). Visor: reutiliza gestos F6.1, añade línea breve de promesa en Seguimiento y enlaza toda la
  cadena en Historias. Escena espontánea en mundo libre grabada en semilla 5 (Leva #7 y Hesk #3, horas 654, 681 y 846).
  [Informe y evidencias de F6.2](docs/F6.2-ESTADO.md).
- **F4.4, salto visual**, aceptada el 18 de noviembre de 2026.
- Base visual guardada en GitHub en el commit `1debb55` de `main`.
- F5.0 cerrada dentro de F5.1: consulta asíncrona, comilla de `cli.py` y demo probada en el visor.
- F5.1 entregada el 18/11/2026 ([F5.1-ESTADO.md](docs/F5.1-ESTADO.md)).
- **F6.0.1, corrección de enterarse de los contratiempos, entregada el 18/11/2026 sin commit y detenida aquí.**
  Los hogares ya no leen el hambre, la sed o la salud oculta del menor: solo cambian de tarea
  cuando alguien lo ve o recibe un aviso real de otra persona del hogar. El que no se ha enterado
  conserva lo que sabía; la retomada exige haber visto o saber que el menor está atendido.
  Los avisos y observaciones quedan en `vidas.familia_nota` y `vidas.familia_aviso`, dentro de la
  historia del objetivo. Criterio nuevo en partidas nuevas y en copias con `ampliar PARTIDA --percepcion-familiar`;
  las partidas F6.0 guardadas conservan su reproducción con el criterio anterior.
- **F6.1, un encuentro que se entiende mirando el mapa, entregada el 18/11/2026 sin commit y detenida aquí.**
  Quien pide comida va hacia alguien concreto (rastro de pasos y anillo bajo esa persona), frena, se vuelve,
  tiende las manos; el otro escucha y ofrece la ración, que pasa de mano en mano, o niega con la cabeza y se
  da la vuelta mientras quien pidió baja la cabeza. Todo sale de `habitante.pide/da/niega/cuenta/rehusa` y de
  un campo nuevo de la lista de habitantes, `busca` (a quién se dirige el paso en curso del plan); el motor no
  cambia. El visor ordena los gestos y aplaza unos segundos lo siguiente que ya decidió el motor (como mucho
  4 celdas de desfase). Interfaz: panel de datos del mundo plegado por defecto, tarjeta de la persona seguida
  con su intención, muelle simplificado («Avanzar»), ficha con retrato, «Ahora», «Con quién», «Acaba de pasar»
  y secciones desplegables, y 1 h/s automática en los encuentros de quien se sigue (interruptor en la tarjeta).
  [Comparar antes y después](docs/f6.1/comparar.html).
  Remate visual entregado. Al seguir a Unai, los tres desenlaces se ven en sus horas (852, 856 y 857),
  y gira hacia Gala mientras se acerca a su misma casilla. Ficha y tarjeta acompañan el gesto en curso.
  [Vídeo continuo sin rótulos](docs/f6.1/remate/despues-sin-rotulos.mp4) · [Comparación y comprobaciones](docs/f6.1/remate/informe.md).
- **F5.2, la voz divina, entregada el 18/11/2026, sin commit, pendiente de que el usuario la pruebe.**
  La pasada de observación está entregada. [Comparar el visor](docs/f5.2/observar/comparar.html) · [Informe](docs/F5.2-ESTADO.md).

## Entorno de IA — Segunda etapa

- Configuración local V2: [.opencode/opencode.jsonc](.opencode/opencode.jsonc).
  Mantiene Build incorporado y GPT-6.1 Sol (`openai/gpt-6.1-sol`).
  No cambia permisos globales ni añade otro desarrollador.
- [arquitecto](.opencode/agents/arquitecto.md):
  `openai/gpt-6-astra#high`; diseño y criterios de aceptación.
- [auditor](.opencode/agents/auditor.md):
  `anthropic/claude-opus-5-5#high`; hallazgos y regresiones.
- Ambos son subagentes: solo `read`, `glob` y `grep`; denegación por defecto.
  Sin escritura, shell, delegación, MCP, red ni acceso fuera del proyecto.
  No pueden ejecutar pruebas ni obtener diffs mediante Git:
  Build debe aportar diff y resultados cuando sean necesarios.
- Identificadores y variantes consultados en el catálogo disponible.
  Anthropic ofrece Opus; `ANTHROPIC_API_KEY` está presente en este entorno.
  No se comprobó su validez, saldo, prioridad frente a cuentas guardadas
  ni autorización efectiva para Opus. No se leyó ni mostró su valor.
- Opus puede facturar por API. Catálogo consultado: USD por millón de tokens,
  entrada 4, salida 20, lectura de caché 0,20 y escritura de caché 5.
  Son tarifas de catálogo, no una garantía del contrato o saldo del usuario.
- No se ejecutó ningún agente ni llamada de prueba a modelos.
  Configuración preparada para revisión; acceso a Opus pendiente de verificar.
- Fuentes oficiales V2: [agentes](https://opencode.ai/docs/agents),
  [permisos](https://opencode.ai/docs/permissions),
  [proveedores](https://opencode.ai/docs/cli/providers).
- Invocación futura desde Build: «Usa el subagente arquitecto para…» o
  «Usa el subagente auditor para…». Invocar consume uso del modelo;
  no hacerlo antes de aprobar la configuración y los posibles costes.
- OpenCode recarga las definiciones al guardarlas; si no aparecen, `/reload`.
  El ejecutable `opencode` no está en el PATH de esta terminal:
  no se verificó la carga efectiva ni los permisos en ejecución.

## Funcionalidades implementadas

| Área | Referencia de detalle |
|---|---|
| Mundo determinista, recursos, conservación, SQLite y reproducción | [README](README.md) |
| Memoria, creencias, planes y relaciones dirigidas | [F2](docs/F2-ESTADO.md) |
| Obras, refugios, depósitos, comunidades y acuerdos | [F3](docs/F3-ESTADO.md) y [F3.1](docs/F3.1-ESTADO.md) |
| Familias, generaciones, intervenciones e historias | [F4](docs/F4-ESTADO.md) |
| Cuidados, rutinas y apoyo durante el crecimiento | [F4.1](docs/F4.1-ESTADO.md) y [F4.2](docs/F4.2-ESTADO.md) |
| Promesas coherentes, antecedentes y destinatarios reales de gestos | [F4.3](docs/F4.3-ESTADO.md) |

Estos informes documentan sus fases; no equivalen a verificaciones nuevas del árbol local.

## F5.0 · Una decisión con modelo local

- Un habitante (`mente_de`) decide con Qwen 2.5 7B vía Ollama qué hacer ante un agujero.
- El motor ofrece las opciones, valida la elección y la ejecuta con acciones de F4.
  Si el modelo falla, se aplica la regla habitual.
- Cada decisión queda en `vidas.decide`; `verificar` la repite sin llamar al modelo.
- Código: [deliberacion.py](genesis/motor/deliberacion.py) y [mente_local.py](genesis/mente_local.py).
- Visor: pestaña «Decisiones» de la ficha.
- Herramientas: [escena_f50.py](herramientas/escena_f50.py), [demo_f50.py](herramientas/demo_f50.py)
  e [informe_f50.py](herramientas/informe_f50.py).
- Demo jugable: `partidas/f50/f50-demo`, creada por `demo_f50.py`.
- Observado: en la escena de Unai el recuerdo cambia la acción (se acerca; sin él, rodea).
  Con un modelo de 7B el efecto no es consistente entre habitantes: en 2 de 4 cambia, y
  en uno de ellos al revés.

## F5.2 · La voz divina

- «Intervenir → Hablar a un habitante»: genera la orden `presencia.voz` y la recepción `vidas.oye`, a la hora en que la oye despierta.
- Interpretación por reglas en [voz.py](genesis/motor/voz.py): advertencia, consejo o señal incierta, y qué agujero reconoce.
- Una voz sobre un agujero conocido reabre la decisión (consulta en segundo plano).
- La voz es causa solo si el modelo la cita; si no, es contexto.
- Los relatos ya no copian lo privado: lo oído, lo decidido y lo vivido.
- Observado con Qwen: advertida después del relato de Unai, Brisa le pide compañía y va a verlo (10/10).
  Advertida antes de conocer el agujero, la voz no cambia lo que hace.
- Demo: `partidas/f52/f52-demo`. Herramientas: escena, demo e informe `_f52`.

## F5.1 · Una conversación con consecuencias

- Unai (#4, reglas de F4) inspecciona el agujero y se lo cuenta a Brisa (`vidas.relata`).
- Brisa (#3, `mente_de`) guarda lo oído (`oido`) y, al ver el lugar, decide con Qwen.
- La consulta es asíncrona: `vidas.consulta`, un plazo de 3 horas y `vidas.decide`, que registra
  `abierta` y `aplicada`. La sesión baja a 1 h/s mientras hay una consulta abierta.
- Observado: con el relato, Brisa se acerca 10 de 10 veces; sin él, evita el agujero 10 de 10.
- Herramientas: [escena_f51.py](herramientas/escena_f51.py), [demo_f51.py](herramientas/demo_f51.py)
  e [informe_f51.py](herramientas/informe_f51.py).
- Demo jugable: `partidas/f51/f51-demo`.

## Cierre visual de F4.4

F4.4 integra figuras ilustradas y animación de marcha y bebida, claros y bosques renovados,
río con corriente y bajíos, senderos y sombras de contacto. Las piezas y poses adicionales
quedan como mejoras futuras.
Detalle y capturas: [F4.4-ESTADO.md](docs/F4.4-ESTADO.md).
Ese informe contiene iteraciones sustituidas: empieza por su sección más reciente.

## Archivos y cambios que deben preservarse

Archivos del visor y la documentación incorporados en el cierre:
- [docs/F4.4-ESTADO.md](docs/F4.4-ESTADO.md)
- [app.js](genesis/visor/estatico/app.js)
- [construcciones.js](genesis/visor/estatico/construcciones.js)
- [mapa.js](genesis/visor/estatico/mapa.js)
- [servidor.py](genesis/visor/servidor.py)
- [capturas_f44.py](herramientas/capturas_f44.py)

Recursos incorporados:
- [sprites.js](genesis/visor/estatico/sprites.js), [arte preparado](genesis/visor/estatico/arte/)
  y [preparar_arte.py](herramientas/preparar_arte.py).
- Imágenes y prompts nuevos de personajes, agua y nieve en [assets/](assets/).
- [antes-arte/](docs/f4.4/antes-arte/), [arte/](docs/f4.4/arte/),
  [estaciones/](docs/f4.4/estaciones/) y comparaciones `comparacion-arte-*.jpg`
  en [docs/f4.4/](docs/f4.4/).

Corrección F6.0.1 (conservar): `genesis/motor/familias.py`, `genesis/motor/vidas.py`,
`genesis/motor/config.py`, `genesis/almacen/almacen.py`, `genesis/cli.py`,
`genesis/sesion.py`, `genesis/visor/estatico/vidas.js` y `pruebas/test_familias_f60.py`.
No reescribir las partidas F6.0 guardadas ni la demo.

F6.1 (conservar): `genesis/visor/estatico/encuentros.js` (nuevo), `mapa.js`, `sprites.js`, `habitantes.js`,
`app.js`, `index.html`, `estilo.css`, `arte/indice.json` y las piezas `arte/persona-{pide,recibe,ofrece,niega,cabizbajo}`
(con máscara), derivadas de `persona-perfil` con [poses_f61.py](herramientas/poses_f61.py); si se vuelve a
ejecutar `preparar_arte.py`, que reescribe el índice, hay que ejecutar después `poses_f61.py`. También
`genesis/sesion.py` (campo `busca` y tratos en `observaciones`), `genesis/visor/servidor.py` (sirve
`encuentros.js`), `probar.bat`, [escena_f61.py](herramientas/escena_f61.py),
[grabar_f61.mjs](herramientas/grabar_f61.mjs), `pruebas/test_encuentros_f61.mjs` y [docs/f6.1/](docs/f6.1/).

F6.3 (conservar): `genesis/motor/conflictos.py` (nuevo), `genesis/motor/{tratos_familia,vidas,config}.py`,
`genesis/{cli,sesion,__init__}.py`, `genesis/almacen/almacen.py`,
`genesis/visor/estatico/{encuentros,mapa,sprites,habitantes,vidas,app}.js`, `arte/indice.json` y las piezas
`arte/persona-{increpa,forcejea}` (con máscara) derivadas con [poses_f63.py](herramientas/poses_f63.py) (tras
`preparar_arte.py`, ejecutar `poses_f61.py` y luego `poses_f63.py`), `probar.bat`,
[escena_f63.py](herramientas/escena_f63.py), [buscar_conflictos_f63.py](herramientas/buscar_conflictos_f63.py),
`pruebas/escena_conflictos_f63.py`, `pruebas/test_conflictos_f63.py`, `pruebas/test_conflictos_f63.mjs`, los ajustes
`conflictos=False` en `pruebas/test_tratos_f62.py` y `herramientas/escena_f62.py`, [docs/F6.3-ESTADO.md](docs/F6.3-ESTADO.md)
y [docs/f6.3/](docs/f6.3/).

F6.2 (conservar): `genesis/motor/tratos_familia.py` (nuevo), `genesis/motor/config.py`, `genesis/motor/vidas.py`,
`genesis/motor/familias.py`, `genesis/motor/habitantes.py`, `genesis/almacen/almacen.py`, `genesis/cli.py`,
`genesis/sesion.py`, `genesis/__init__.py`, `genesis/visor/estatico/{encuentros.js,mapa.js,habitantes.js,vidas.js,app.js,index.html,estilo.css}`,
`probar.bat`, [escena_f62.py](herramientas/escena_f62.py), `pruebas/test_tratos_f62.py`,
`pruebas/test_tratos_f62.mjs`, [docs/F6.2-ESTADO.md](docs/F6.2-ESTADO.md) y [docs/f6.2/](docs/f6.2/).

Consulta `git status --short` para el inventario vigente.
Las partidas, las copias locales y la configuración de herramientas se conservan aparte.

## Problemas pendientes

**Mejoras visuales futuras:** variantes estacionales y poses para más acciones.

**Documentación y entrega:**
- README niega en apartados antiguos parentesco, nacimientos, generaciones e
  intervenciones ya implementados. Algunas ayudas/docstrings también están atrasadas.
- El estado global está en [docs/ESTADO_DESARROLLO.md](docs/ESTADO_DESARROLLO.md).
  El diario histórico de F2 está en [F2-ESTADO_DESARROLLO.md](docs/F2-ESTADO_DESARROLLO.md).
- Falta formalizar dependencias de herramientas opcionales y aclarar permisos del
  arte para distribución; no se localizó una licencia general.
- Revisar recursos sin seguimiento antes de preparar una entrega reproducible.

**Investigación, no tareas autorizadas:** F4.3 documenta 21 muertes adicionales
en su comparación de 20 mundos, sin causa investigada, y mecánicas sociales raras
o solo comprobadas en escenas preparadas. Persisten límites de continuidad familiar
en escasez, separación, coste con la historia y determinismo entre plataformas.
Véanse F4.2, F4.3 y la [auditoría previa F4.2.1](docs/F4.2.1-AUDITORIA.md);
esta auditoría no describe íntegramente las reglas actuales.

Excepción histórica: la partida «aldea» mezcla políticas de desarrollo.
Se conserva sin reescribirla; no usarla como referencia de reproducción exacta.
Explicación: [F3, §7](docs/F3-ESTADO.md).

## Últimas verificaciones

- F6.3 (2026-11-19, Windows 11, Python 3.14.4, Node 24.14.1, Chrome sin ventana, Ollama apagado):
  `py -3 -B -m unittest discover -s pruebas -t .` **412 correctas** (12 nuevas en `pruebas/test_conflictos_f63.py`; tras el último ajuste de rótulo, 152 de las suites afectadas otra vez correctas); `node --test` de los seis archivos de `probar.bat`, **56 correctas** (6 nuevas en `pruebas/test_conflictos_f63.mjs`).
  Escenas preparadas (misma situación, solo cambia el carácter) en `pruebas/escena_conflictos_f63.py`; recorrido libre de
  60 semillas × 1920 h con `herramientas/buscar_conflictos_f63.py` (`docs/f6.3/libres.txt`). Clips continuos a tamaño
  normal (44 px/celda, 1440×900, 1 h/s, ficha cerrada) con `grabar_f61.mjs` sobre copias en el scratchpad, consola sin
  errores; capturas de ficha e Historias. Guardar y cargar en mitad de una discusión y reproducción exacta comprobados.

- F6.2 (2026-11-19, Windows 11, Python 3.14.4, Node 24.14.1, Chrome sin ventana, Ollama apagado):
  `py -3 -B -m unittest discover -s pruebas -t .` **400 correctas** (10 nuevas en `pruebas/test_tratos_f62.py`);
  `node --test pruebas/test_interfaz.mjs pruebas/test_interfaz_f43.mjs pruebas/test_interfaz_f52.mjs pruebas/test_encuentros_f61.mjs pruebas/test_tratos_f62.mjs` **50 correctas** (5 nuevas en `pruebas/test_tratos_f62.mjs`).
  CLI verificada en carpeta temporal (`nueva`, `simular --dias 28`, `verificar` con reproducción exacta de 672 h / 4844 eventos, `listar`) y copia ampliada (`ampliar_partida(..., tratos_familia=True)`) conservando el original byte a byte.
  Escena libre verificada y grabada en el visor real (`--sin-modelo`): semilla 5, guardada en hora 652, siguiendo a Hesk (#3) con ficha cerrada a 1 h/s (`docs/f6.2/trato-libre-entrega.mp4` y `docs/f6.2/trato-libre-reparacion.mp4`); capturas y consola limpia (`errores: []`) a 1280×720, 1440×900 y 1920×1080 en [docs/f6.2/](docs/f6.2/).

- Remate de F6.1 (2026-11-18, Chrome en Windows, sin modelo): 45 pruebas JS y 18 Python de sesión, servidor y comandos.
  Apertura de ficha y crónica con clics a 1280 × 720, 1440 × 900 y 1920 × 1080, consola limpia.
  [Detalle de la misma partida antes y después](docs/f6.1/remate/informe.md).

- F6.1 (2026-11-18, Windows 11, Python 3.14.4, Node 24.14.1, Chrome 157 sin ventana, modelo local desactivado):
  `py -3 -B -m unittest discover -s pruebas -t .` 390 correctas; `node --test` de los cuatro archivos de
  `probar.bat`, 43 correctas (9 nuevas en `test_encuentros_f61.mjs`). Escena: `py -3 herramientas/escena_f61.py
  --carpeta <temporal>` (semilla 13, reglas actuales con planes familiares, guardada en la hora 849; los desenlaces
  son espontáneos), vista con `ejecutar.py visor ... --sin-modelo` desde copias en el scratchpad, nunca en `partidas/`.
  Clips del antes y el después grabados con `grabar_f61.mjs` a 1 h/s, siguiendo a Unai, ficha cerrada, 44 px/celda,
  1440×900. En el navegador: clic real que elige a Unai, seguimiento de cámara, fila de «Acaba de pasar» que abre
  el suceso en la crónica, panel «Historias», cámara lenta 24→1→24 h/s, capturas a 1280×720 y 1920×1080 y consola
  sin errores. Fluidez en la misma escena sin grabar (Chrome sin ventana, sin tope de refresco): mediana ~177 fps en
  las dos versiones; el cuadro cuesta 1,85 ms frente a 1,50 ms. Se corrigió que una señal viva repintara el paisaje
  entero en cada cuadro (`_acontecimientos`).

- F6.0.1 (2026-11-18, Windows 11, Python 3.14.4, Node 24.14.1, sin Ollama): batería Python de 390 pruebas y 34 JS correctas. Foco: 19 pruebas de `pruebas/test_familias_f60.py` y 94 de almacén, determinismo y sesión. Reproducción exacta comprobada en partida F6.0 antigua, partida nueva y copia con percepción; la original queda byte a byte igual. CLI probada en carpeta temporal con `ampliar --familias` y `ampliar --percepcion-familiar`.
- F5.2 (2026-11-18, Windows 11, Python 3.14, Node 24, Ollama con qwen2.5:7b): 371 pruebas Python y 32 JS
  (`test_interfaz.mjs`, `_f43` y `_f52`) correctas. En el navegador, con clics: «Hablar», «Cancelar»
  (no registra nada) y «Confirmar» (llega a Brisa, decide y actúa). Medidas en
  [f5.2/resultados.json](docs/f5.2/resultados.json).

- F5.1 (2026-11-18, Windows 11, Python 3.14, Node 24, Ollama con qwen2.5:7b): batería Python
  con 361 pruebas correctas y JS con 30. Las dos demos se probaron en el visor con clics de
  intervención y avance. Medidas en [f5.1/resultados.json](docs/f5.1/resultados.json).

- F5.0 (2026-11-18, Windows 11, Python 3.14, Node 24, Ollama con qwen2.5:7b):
  `py -3 -B -m unittest discover -s pruebas -t .` y
  `node --test pruebas/test_interfaz.mjs pruebas/test_interfaz_f43.mjs`: 351 pruebas
  Python y 30 JS correctas. Detalle en [F5.0-ESTADO.md](docs/F5.0-ESTADO.md). Se probó en el visor real con capturas por CDP.
  Las mediciones con el modelo están en [resultados.json](docs/f5.0/resultados.json).

- Cierre F4.4 (2026-11-18, Windows): `node --test pruebas/test_interfaz.mjs pruebas/test_interfaz_f43.mjs` pasó 30 pruebas.
  `py -3 -B -m unittest pruebas.test_sesion_servidor` pasó 18.
- Revisión documental y estática del 2026-11-16:
  Python 3.14.4, Node.js 24.14.1, Windows.
  Se contaron 338 métodos de prueba Python y 23 casos JS; **no se ejecutaron**.
- Evidencia anterior: F4.3 informa 338 pruebas Python y 23 JS correctas.
  F4.4 informa comprobaciones parciales y medidas de sus iteraciones.
  No presentarlas como regresión nueva de este árbol.
- La primera etapa creó únicamente AGENTS.md y ESTADO.md; no ejecutó suites,
  simulaciones ni generadores. La validación es documental:
  referencias locales y conservación de archivos existentes.
- Comprobación documental: 45 enlaces locales válidos; la huella conjunta de rutas
  y contenidos de los 514 archivos preexistentes (fuera de `.git/`) no cambió.
- Comandos canónicos y precauciones: AGENTS.md.
  Al verificar después, registrar fecha, comando, entorno, resultado y evidencias.
- Segunda etapa: JSONC y frontmatter/reglas comprobados estáticamente;
  48 referencias locales existentes. Huellas de los otros 515 archivos
  preexistentes idénticas. No se validó la carga mediante el ejecutable de OpenCode.

## Próximo paso concreto

Ritmo de observación propuesto, pendiente de implementar: a ×1, diez minutos reales por jornada completa,
cinco de luz y cinco de noche, con opción de probar un ritmo más pausado. Controles manuales ×2, ×3 y ×4.

F6.3 entregada y detenida aquí, pendiente de valoración del usuario. Para verla: abrir
[docs/f6.3/comparar.html](docs/f6.3/comparar.html), o `py -3 herramientas/escena_f63.py --carpeta <carpeta nueva>` y
`py -3 ejecutar.py visor f63-pelea --carpeta <esa carpeta> --sin-modelo` siguiendo a Orel (#8) a 1 h/s (pelea en las
horas 659–662), o `f63-disculpa` siguiendo a Dorin (#13) (horas 876 y 896). Pendientes en el informe de F6.3.

F6.2 cerrada y detenida aquí, pendiente de valoración del usuario. Para ver la escena libre en el visor:
`py -3 herramientas/escena_f62.py --carpeta <carpeta nueva>` y abrir
`py -3 ejecutar.py visor f62-tratos --carpeta <esa carpeta> --sin-modelo`, siguiendo a Hesk (#3) o Leva (#7) a 1 h/s con la ficha cerrada (trato en hora 654, reparación en hora 681, segundo trato por confianza en hora 846). [Informe de F6.2](docs/F6.2-ESTADO.md).

F6.1 entregada y detenida tras este encuentro. Para verla: `py -3 herramientas/escena_f61.py --carpeta <carpeta nueva>`
y abrir `ejecutar.py visor f61-encuentro --carpeta <esa carpeta> --sin-modelo` siguiendo a Unai (#25) a 1 h/s.
Pendiente de valoración del usuario. El remate se comprobó con Kora, Hesk y Gala. En grupos muy concurridos
el visor puede omitir gestos de terceros si crece la espera. Con el arte de código se usan las poses equivalentes.

F6.0.1 entregada y detenida aquí: **no se han empezado los tratos entre familias**; esa fase tiene su propio encargo. Para ver la corrección, crear una partida nueva o copiar una F6.0 con `ejecutar.py ampliar PARTIDA --percepcion-familiar --carpeta ...`; la partida original no se toca. La demo antigua (`iniciar.bat f60-demo --carpeta partidas/f60`) conserva su criterio y su reproducción. [Resultados de F6.0](docs/F6.0-ESTADO.md).

F6.0 está implementada y verificada sin modelo. Para observar los dos hogares, abrir `iniciar.bat f60-demo --carpeta partidas/f60`. La demo empieza en la hora 483 del primer otoño.

Para el entorno de IA, revisar las configuraciones de arquitecto y auditor sin ejecutarlos.
Comprobar su aparición, modelos y permisos en OpenCode; para Build, mantener Sol
seleccionado también en la sesión existente. Antes de usar Opus, confirmar cuenta
y facturación en `/connect` y autorizar su ejecución. No hay trabajo de código
de GENESIS autorizado por esta tarea.
La última pasada integra río, prado y refugios. El [comparador](docs/f4.4/acabado/comparar.html)
conserva los cuatro encuadres y el [informe de fase](docs/F4.4-ESTADO.md) recoge el recorrido y la fluidez.
Antes de cerrar una futura entrega, ejecutar regresiones y revisar el visor sobre
partidas aisladas. Corregir README y ayudas solo mediante una tarea autorizada aparte.

## Registro breve de traspaso

2026-11-19 — F6.3: carácter, contratiempos, conflictos y peleas alrededor de los tratos F6.2, regla versionada
`conflictos`, sin Ollama. Dos poses derivadas. Evidencias en docs/f6.3/. Configuraciones de prueba añadidas a
`../.claude/launch.json` retiradas al cerrar. Fase detenida aquí.

2026-11-19 — F6.2: tratos entre familias (comida hoy a cambio de ayuda para reparar mañana), sin Ollama,
regla versionada `tratos_familia`, gestos F6.1 reutilizados, línea de promesa en Seguimiento e Historias
enlazadas. 400 pruebas Python y 50 JS correctas; escena libre semilla 5 grabada en `docs/f6.2/`. Fase cerrada.

2026-11-18 — F6.1: encuentros de pedir comida legibles en el mapa y acabado del visor. Sin cambios en reglas,
serialización ni partidas. Evidencias en docs/f6.1/. Configuraciones de prueba añadidas a `../.claude/launch.json` retiradas al cerrar.

2026-11-16 — Segunda etapa: añadidas dos definiciones de subagentes y configuración
local de Build. Actualizado este estado; sin ejecutar agentes ni cambiar permisos
globales. Verificación estática, no prueba funcional de acceso a los proveedores.

2026-11-16 — Creados AGENTS.md y ESTADO.md por autorización del usuario.
Decisión: instrucciones estables aquí enlazadas; estado vivo en este archivo;
informes y evidencias históricos permanecen en docs/, sin duplicarlos.
No se cambian reglas, código, recursos, partidas, historial Git ni documentación previa.
En próximos hitos, actualizar avances, parciales, decisiones, pruebas reales y siguiente
acción; conservar los detalles extensos en el informe de fase correspondiente.
