# GENESIS F3 — Estado de desarrollo

Primeras comunidades: lugares, reservas y proyectos compartidos.
Se actualiza al cerrar cada hito para poder continuar si se interrumpe la sesión.

## Punto de partida

- F2.5 cerrada (segunda pasada artística). 259 pruebas Python y 9 JavaScript.
- Respaldo completo antes de tocar nada: `docs/respaldo/genesis-f25-antes-f3.tar.gz`.

## Diseño (fijado al empezar)

- **Reglas 3** (`ConfigHabitantes.reglas = 3`, ya son las actuales). Se activan al
  empezar una partida nueva, o en una copia ampliada desde la hora indicada en el
  campo nuevo `activacion_comunidad`. La activación anterior de F1 a F2
  (`activacion`) se conserva aparte: una copia F1→F2→F3 guarda ambas.
- Todo el estado nuevo se guarda solo con las reglas 3 activas: bajo
  `habitantes.comunidad` y en `Mente.f3`. La madera entra en los inventarios al
  activarse. F0, F1 y F2 conservan sus hashes (las huellas fijadas siguen pasando).
- Módulos nuevos: `motor/comunidad.py` (construcciones, obras, compromisos,
  refugio, depósitos, conocimiento de lugares, comunidades, acuerdos y
  contabilidad) y `motor/obras.py` (la parte de la política que decide).
- Configuración: `ConfigComunidad` en `ConfigMundo.comunidad` (costes, plazas,
  abrigo, desgaste, plazos).

## Hito 1 — Motor de construcción, refugio y reservas (TERMINADO)

Hecho:

- Madera como material: acción `talar` sobre las existencias reales del bosque;
  ocupa carga, no se come (todas las comprobaciones de comida usan ahora el
  alimento que se lleva, no la carga; sin madera es lo mismo que antes).
- Construcciones (refugio y depósito) con identificador, celda, estado (obra,
  suspendida, abandonada, lista, ruina), madera requerida, entregada e
  incorporada, trabajo hecho y pendiente, conservación, capacidad, existencias,
  ocupantes, aportaciones por persona e historia.
- Cada hora de trabajo incorpora su parte de madera: sin material no avanza.
- Compromisos con reserva de material (dos personas no traen la misma madera);
  se cumplen, caducan, se dejan por una urgencia anotada o por muerte, y quienes
  trabajan en la obra lo juzgan según ese contexto.
- Refugio: plazas (6), abrigo (+9 °C con frío, sin mojarse), descanso extra;
  desgaste diario (más con lluvia), media utilidad por debajo de 400 y ruina
  por debajo de 100; reparación con madera y trabajo.
- Depósito: capacidad 80, guardar y retirar atómicos; contabilidad de comida
  ampliada (llevado + comido + guardado = recogido) y libro de la madera
  (talada = llevada + en obra + incorporada + guardada + gastada en reparar).
- Conocimiento de lugares: se ven, se cuentan (`informar`) con origen,
  antigüedad y confianza, y se comprueban (`lugar.comprobado`).
- Comunidades alrededor de lugares terminados, con pertenencia decidida por cada
  persona según lo vivido; alejamiento, vuelta, salida y disolución.
- Acuerdos del catálogo (reserva mínima, prioridad para quien está en apuros,
  mantenimiento): se proponen, se aceptan o rechazan, y su incumplimiento lo
  juzga quien lo ve y conoce el acuerdo.
- Política (`obras.py`): dormir y resguardarse en refugios conocidos, retirar
  de la reserva común, guardar excedentes, sumarse a obras, empezar refugios y
  depósitos, reparar, informar y proponer acuerdos, con razones guardadas.

Comprobaciones: regresiones de F1/F2 (huellas incluidas) correctas;
supervivencia F3: 19 de 20 semillas abundantes con 23 o más vivos al año;
escasez con media de 23,9 (F2: 23,3). Revisión libre de 10 semillas: todas
construyen, usan y forman comunidades.

Problemas encontrados y corregidos: refugios llenos que dejaban gente al raso
en plena helada (ahora se replanifica al quedarse sin sitio y no se cruza el
raso con helada hacia un refugio lejano); la obra iba por delante de reponer
comida (ahora por detrás, y con más provisiones en otoño e invierno).

## Hito 2 — Persistencia, compatibilidad, pruebas y API (TERMINADO)

Hecho:

- `nueva` crea partidas F3 por defecto (`--reglas 1|2|3`). `ampliar` copia una
  partida F1 (memoria, vida social y comunidades empiezan a la vez) o F2 (se
  conserva su activación de las reglas 2, que puede venir de F1, y se añade la
  de las reglas 3). La meta `etapas` guarda la cadena completa. Al abrir una
  semilla que ya tiene partida F2 se crea aparte (`-comunidad`).
- Corregido al probar la cadena F1→F2→F3: el aviso `sociedad.activada` anotaba
  las reglas de la partida (2 entonces, 3 al repetir); ahora anota las que
  empiezan (2), y la repetición coincide.
- Sesión: resumen de saltos con lo colectivo (obras, madera, reparaciones,
  ruinas, estancias, sin sitio, guardado y retirado, compromisos, comunidades,
  uniones, salidas, acuerdos, informes), siempre sobre el intervalo entero.
  Consultas `/api/lugares`, `/api/lugar?id`, `/api/comunidad?id`; la ficha
  personal incluye `comunidad` (pertenencia, aportes, compromiso, acuerdos que
  conoce y lugares que cree conocer, con el dato real aparte); la vida de cada
  persona incluye sus acontecimientos colectivos; filtro de crónica `comunidad`.
- Pruebas nuevas en `pruebas/test_comunidad.py` (20) y supervivencia con reglas
  3 en `test_supervivencia.py`. Ajustadas 4 pruebas que daban por hecho que las
  reglas actuales eran las 2.

Comprobado: todas las pruebas de F3, de ampliación y de supervivencia con
reglas 3 pasan.

## Hito 3 — Visor (TERMINADO)

Hecho:

- `visor/estatico/construcciones.js`: refugios (choza de palos y paja) y
  depósitos (cesto de mimbre sobre pies con tapa de paja) dibujados desde sus
  datos: estacas al empezar, un palo por cada parte de madera incorporada,
  cubierta que crece con las horas de trabajo, pila de troncos con la madera
  entregada sin usar, huecos y tonos apagados con la conservación perdida, obra
  parada o abandonada desvaída y torcida, ruina como montón de palos; nieve en
  invierno; el depósito muestra en su boca lo que guarda y en qué proporción.
  De noche, fuego en la puerta y humo solo si hay alguien dentro, y una marca
  por ocupante. Luz del oeste y contorno oscuro como el resto del mapa.
- Mapa: las construcciones se dibujan intercaladas con las personas por
  profundidad, bajo las copas; quien queda detrás de una se redibuja atenuado;
  quien está a cubierto no se dibuja (lo cuenta el refugio), salvo la persona
  elegida, que aparece en la puerta. El clic y el paso del ratón sobre
  cualquier parte del dibujo eligen la construcción, aunque sobresalga de su
  celda; las personas tienen preferencia.
- Figuras: posturas de talar (hacha de piedra), construir (encajar un palo) y
  guardar (cesto), y haz de leña a la espalda cuando se lleva madera.
- `visor/estatico/lugares.js`: frases de todos los acontecimientos nuevos;
  ficha de construcción en el panel de inspección (estado con medidas reales,
  quién la empezó y por qué, quién aportó y qué, quién la usa, comunidad,
  acuerdos, tensiones, historia), ficha de comunidad (lugares, miembros con sus
  aportes, antiguos miembros y por qué se fueron, acuerdos, tensiones,
  historia), pestaña «Comunidad» en la ficha personal (pertenencia,
  compromiso, aportes, acuerdos que conoce, lugares que cree conocer con el
  dato real aparte) y párrafo colectivo en el resumen de los saltos. Filtro
  «Comunidades» en la crónica. Todo enlazado entre sí.
- La insignia de fase sale de las reglas de la partida abierta (F1, F2 o F3).
- Corregido al revisar: las tensiones de un lugar se buscaban solo entre sus
  80 últimos eventos y desaparecían con el uso; ahora tienen su propia consulta
  (por tipo, con índice).

Comprobado con capturas reales (`docs/f3/`): 1280×720, 1440×900 y 1920×1080,
de día, de noche y en obra (`movimiento-obra.gif`). Pruebas JS: 12 (3 nuevas).

## Hito 4 — Revisión, medidas y documentación (TERMINADO)

Hecho:

- Política corregida tras revisar muertes en mundos libres (`planes.py`):
  (1) el paso «resguardarse» se saltaba con hambre ≥ 700 y, como «refugio»
  (prio 80) se reproponía cada hora antes que «comer» (70), la persona quedaba
  quieta «por ocio» al raso junto a un refugio con sitio; ahora solo sale con
  sed ≥ 600 o hambre ≥ 900 sin comida encima (y entonces no se le repropone el
  refugio). (2) Con frío peligroso dentro del bosque va a un refugio conocido a
  ≤ 3 celdas; dormido al raso sin bosque cerca, despierta si conoce uno.
- Supervivencia F2/F3, 10 semillas × 2 años (`docs/f3/comparacion-*.json`):
  abundancia 249/244 (F2) frente a 247/238 (F3); escasez 233/200 frente a
  239/196. Lo que queda: invierno extremo de la semilla 9 (ni el refugio basta;
  salir a beber al río cruzando el raso helado).
- Fluidez (RTX 5070, 1440×900): reglas 2 y 3 iguales (~170 cuadros/s, p95
  5,7–11 ms, sin tareas largas); aldea con 16 construcciones a la vista igual.
- Simulación: 591 h/s (F3) frente a 842 h/s (F2); ~1,15 MB y ~4500 eventos por
  año (F2: ~0,6 MB, ~2500). A los 5 años el coste por hora sube ~20 %.
  Consultas a los 5 años: ≤ 15 ms (ficha de comunidad la más cara).
- Reproducción exacta de partidas F2 y F3 creadas con el código actual (una
  partida que mezcla historia de dos versiones de la política no se reproduce,
  como es de esperar).
- README actualizado a F3.

Cierre (documentación, sin cambios de código):

- Resultados de la tanda final leídos: revisión de mundos libres
  (`docs/f3/revision-*.{txt,json}`), supervivencia de 20 semillas (19 de 20
  con ≥ 23 vivos; la semilla 4 queda en 22; criterio exigido 18 de 20) y
  comparaciones F2/F3 a dos años. Coinciden entre sí (mismas semillas, mismas
  cifras en revisión y comparación).
- Suite Python final: 282 OK, según su registro (`docs/f3/registro-suite-final.txt`,
  12:11), posterior al último cambio de código (12:01). JavaScript: 12 OK,
  repetido al cerrar.
- Reproducción repetida al cerrar en partidas creadas enteras con el código
  final (F2 `r2`, F3 `r3` y `aldea-inicio`): exacta.
- La partida de desarrollo «aldea» mezcla historia de políticas anteriores y no
  se reproduce con el código final. Se conserva tal cual en
  `docs/f3/partidas-desarrollo/original/` (copia exacta) y se documenta así.
- Velocidad y tamaño vueltos a medir: F3 ~535 h/s frente a ~756 h/s en F2
  (−29 %), 2,31 MB frente a 1,16 MB por dos años. Medidas de fluidez copiadas a
  `docs/f3/medidas/`. Coste a los 5 años y tiempos de consulta: solo en el
  registro de la sesión anterior.
- Auditoría de cadenas causales (`docs/f3/auditoria-cadenas.json`): las
  estancias por información apuntan siempre a un `lugar.informa`; las obras
  apuntan a su vivencia cuando la hay (17 de 133 y 44 de 124); las cesiones de
  sitio **no** apuntan al acuerdo (su causa es el último suceso del refugio).
- Encontrado al revisar y **no corregido** (se pedía no tocar el código):
  cesiones de sitio de ida y vuelta en la misma hora (semilla 8 escasa, sucesos
  7590 y 7592), porque cuenta como «en apuros» cualquiera expuesto al frío y
  cede cualquier ocupante sano que acepte el acuerdo. Documentado en
  `F3-ESTADO.md` §8.
- Escrito `docs/F3-ESTADO.md`.

## Estado

F3 cerrada. Pendientes conocidos para una fase siguiente o una corrección
puntual: la cesión de ida y vuelta y su enlace causal con el acuerdo; refugios
sin agua cerca (muertes al salir a beber con frío extremo); acuerdos poco
frecuentes; fragmentación en comunidades pequeñas; coste creciente con la
historia.
