# GENESIS F3 — Estado de la entrega

Primeras comunidades: lugares, reservas y proyectos compartidos.
Versión `0.3.0-f3`, reglas de conducta 3. Fecha de cierre: 13 de noviembre de 2026.

> **Corrección posterior: [F3.1](F3.1-ESTADO.md).** Los dos problemas de las
> cesiones de sitio descritos en §5 D y §8 (ida y vuelta en la misma hora y
> causa que no era el motivo) están corregidos en F3.1 para las partidas
> nuevas. Las partidas F3 anteriores conservan su criterio y se reproducen
> igual. Los resultados de este documento son los de F3 y se dejan tal cual.

El diario de desarrollo, hito a hito, está en
[F3-ESTADO_DESARROLLO.md](F3-ESTADO_DESARROLLO.md). Este documento resume lo
entregado, lo comprobado y lo que falla o falta.

**Estado:** F3 funciona de principio a fin con `iniciar.bat`: los habitantes
talan, transportan, construyen, usan, mantienen y abandonan refugios y
depósitos, se comprometen y fallan, se informan, forman comunidades y proponen
acuerdos, todo calculado por el motor y visible en el visor. Quedan límites
reales y un defecto conocido en la cesión de sitio (§8), que no impiden cerrar
la fase pero deben tenerse en cuenta al leer los resultados.

---

## 1. Funcionalidades terminadas

### Construcciones y materiales
- **Madera como material.** La acción `talar` extrae madera real de las
  existencias del bosque (el dibujo del bosque aclara al talar). Ocupa carga y
  no se come: todas las comprobaciones de alimento usan solo la comida llevada.
- **Libro de la madera**, comprobado cada día por el motor:
  talada = llevada + entregada en obra + incorporada + guardada + gastada en
  reparar. Y para la comida: recogida = llevada + comida + guardada en depósitos.
- **Destino de lo que queda a medias:** la madera entregada a una obra
  abandonada sigue en ella (otra persona puede reanudarla); lo ya entregado
  por quien muere sigue en su obra, y lo que llevaba encima queda con su
  cuerpo y sigue contado en el libro; su compromiso se libera; una comunidad
  disuelta deja sus lugares, existencias e historia intactos.
- **Construcciones** (`refugio`, `depósito`) con identificador, celda válida
  (pradera transitable, no en la orilla, separación mínima), estado (obra,
  suspendida, abandonada, lista, ruina), madera requerida, entregada e
  incorporada, trabajo hecho y pendiente, conservación, capacidad, ocupantes o
  existencias, aportaciones por persona e historia acotada.
- **Obra:** cada hora de trabajo necesita su parte de madera incorporada; sin
  material no avanza. Tras días sin avanzar se suspende y después se abandona;
  se puede reanudar.
- **Conservación:** desgaste diario (mayor con lluvia), media utilidad por
  debajo de 400, ruina por debajo de 100; reparación con madera y trabajo.

### Refugios
- 6 plazas, +9 °C de abrigo con frío, sin mojarse, descanso extra.
- Plazas respetadas de forma determinista; quien no cabe recibe
  `refugio.sin_sitio`, lo recuerda y busca otro abrigo.
- Con el acuerdo «prioridad para quien está en apuros» aceptado, un ocupante
  sano puede ceder su sitio (`refugio.cede_sitio`); véase el defecto de §8.

### Depósitos
- Capacidad 80; guardar y retirar son operaciones atómicas y deterministas.
- Se sabe lo que hay por haberlo visto o porque se lo han contado.
- Sin bucles de guardar y sacar: quien acaba de guardar no saca en 24 horas.
- El acuerdo «reserva mínima» frena las retiradas por debajo del mínimo salvo
  hambre grave, y quien lo ve y conoce el acuerdo lo juzga según el contexto.

### Proyectos y compromisos
- Compromisos con reserva de material (dos personas no traen la misma madera).
- Se cumplen, caducan, se dejan por una urgencia anotada, por no poder o por
  muerte; quienes trabajan en la obra lo juzgan según lo que vieron.
- Las urgencias tienen prioridad sobre la obra; la obra queda por detrás de
  reponer comida, con más provisiones en otoño e invierno.

### Comunidades
- Nacen alrededor de un lugar terminado y usado por varias personas, no por
  mera proximidad. Cada persona decide unirse, alejarse, volver o irse según lo
  vivido allí (aportes, usos, compromisos incumplidos, confianza, ausencia).
- Se debilitan y se disuelven; sus construcciones permanecen.

### Acuerdos
- Catálogo cerrado: reserva mínima, prioridad para quien está en apuros,
  mantenimiento. Se proponen, cada persona los acepta o rechaza, y su
  cumplimiento lo juzga quien lo ve y los conoce. Se distingue propuesta,
  aceptación, conducta real y juicio.

### Conocimiento compartido
- Creencias sobre lugares con origen (visto o contado, y por quién),
  antigüedad y confianza, limitadas a 10 por persona.
- `informar` transmite lo que una persona sabe; quien lo oye lo comprueba al
  verlo (`lugar.comprobado`) y corrige lo falso. Unirse a una comunidad no da
  acceso a lo que saben los demás. No se genera religión ni norma alguna.

### Persistencia y compatibilidad
- Reglas 3 por defecto en partidas nuevas. El estado de F3 solo se guarda con
  las reglas 3 activas, así que F0, F1 y F2 conservan sus huellas.
- `ampliar` copia una partida F1 o F2 y activa en la copia las reglas 3,
  conservando la activación anterior de las reglas 2 (meta `etapas`).
- Guardar y cargar a mitad equivale a no interrumpir (probado).

### Interfaz
- Refugios y depósitos dibujados desde sus datos (estacas, palos por madera
  incorporada, cubierta por horas de trabajo, pila de madera entregada, huecos
  por desgaste, nieve, luz y humo solo con gente dentro, contenido visible del
  depósito). Personas con posturas de talar, construir y guardar y con haz de
  leña a la espalda.
- Fichas de construcción y de comunidad, pestaña «Comunidad» en la ficha
  personal, frases para todos los sucesos nuevos, filtro «Comunidades» en la
  crónica y resumen colectivo de los saltos sobre el intervalo completo.
- Quien está a cubierto no se dibuja (lo cuenta el refugio) salvo la persona
  elegida; el clic en cualquier parte del dibujo elige la construcción.

Parámetros en `ConfigComunidad` (`genesis/motor/config.py`).

---

## 2. Pruebas

| Conjunto | Resultado | Cómo se ha comprobado |
| --- | --- | --- |
| Python: `py -3 -m unittest discover -s pruebas -t .` | **282 pruebas, OK** (309,7 s) | Registro de la ejecución final: [f3/registro-suite-final.txt](f3/registro-suite-final.txt), escrito a las 12:11 del 13-11-2026. Ningún archivo de código ni de pruebas ha cambiado después de las 12:03 (comprobado por fecha de modificación; `planes.py`, el último, es de las 12:01). No se ha repetido. |
| JavaScript: `node --test pruebas/test_interfaz.mjs` | **12 pruebas, OK** | Repetido directamente al cerrar esta documentación. |
| Reproducción exacta (`ejecutar.py verificar`) | Correcta en partidas F2 y F3 creadas íntegramente con el código final | Repetido al cerrar: `r2` (F2, semilla 5, 1920 h, 4940 eventos), `r3` (F3, semilla 5, 1920 h, 9036 eventos), `aldea-inicio` (F3, semilla 3, 960 h, 3902 eventos). |

Pruebas específicas de F3 en `pruebas/test_comunidad.py` (20; son **escenas
controladas**, preparadas a propósito, no mundos libres):

- Materiales y obras: dos aportes suman exactamente; sin material la obra no
  se completa; la madera ocupa carga y no se come; recoger, transportar,
  guardar, construir y reparar conservan los recursos.
- Simultaneidad y compromisos: nadie se lleva la misma última unidad ni
  reserva la misma madera; una urgencia aparta el compromiso y se juzga por su
  contexto; la muerte de un participante no bloquea la obra ni borra su madera.
- Refugio: la misma noche fría con y sin refugio da un resultado distinto;
  plazas deterministas y cesión por acuerdo.
- Conocimiento: una información recibida lleva a usar un refugio y se
  comprueba; una información falsa se corrige; entrar en una comunidad no da
  acceso a lo que saben los demás.
- Cooperación y acuerdos: haber construido juntos cambia la relación y lo que
  se decide después; un acuerdo aceptado frena una retirada y el contexto
  cambia el juicio; disolver una comunidad conserva lugares, existencias e
  historia.
- Recorrido completo: una necesidad lleva a un refugio que otros ayudan a
  levantar y luego usan, con la política normal.
- Partida: misma semilla, mismo estado; guardar y cargar a mitad; ampliar una
  F2 que venía de F1 conserva las dos activaciones; saltos y fichas.

Además, `pruebas/test_supervivencia.py` incluye la supervivencia con reglas 3
(20 semillas abundantes, 10 escasas y 10 muy escasas), que forma parte de las
282.

---

## 3. Supervivencia

**Criterio exigido:** al menos 23 de 25 vivos tras un año en al menos 18 de 20
semillas abundantes.

| 20 semillas abundantes, 1 año | Semillas con ≥ 23 vivos | Media de vivos |
| --- | --- | --- |
| F2 (reglas 2) | 20 de 20 | 24,85 |
| **F3 (reglas 3)** | **19 de 20** — cumple | 24,85 |

En F3 la única semilla por debajo es la 4, con 22 vivos (en F2 tiene 24).
Fuente: [f3/supervivencia-20-semillas.json](f3/supervivencia-20-semillas.json).

Comparación a dos años, mismas 10 semillas, vivos al final del año 1 y del año 2
(sumas sobre 250):

| Configuración | F2 | F3 |
| --- | --- | --- |
| Abundante (1,0) | 249 / 244 | 247 / 238 |
| Escasa (0,3) | 233 / 200 | 239 / 196 |

Por semilla (F2 → F3, año 1 / año 2):

| Semilla | Abundante | Escasa |
| --- | --- | --- |
| 1 | 25/25 → 25/25 | 25/25 → 25/25 |
| 2 | 25/25 → 25/25 | 25/16 → 25/15 |
| 3 | 25/25 → 25/25 | 25/18 → 25/15 |
| 4 | 24/24 → 22/22 | 12/12 → 20/15 |
| 5 | 25/25 → 25/25 | 25/25 → 25/25 |
| 6 | 25/25 → 25/25 | 25/25 → 25/25 |
| 7 | 25/25 → 25/25 | 25/20 → 25/24 |
| 8 | 25/25 → 25/25 | 25/23 → 25/19 |
| 9 | 25/20 → 25/16 | 21/12 → 19/8 |
| 10 | 25/25 → 25/25 | 25/24 → 25/25 |

Fuentes: [f3/comparacion-abundante.json](f3/comparacion-abundante.json) y
[f3/comparacion-escasa.json](f3/comparacion-escasa.json).

Lectura honesta: F3 no mejora la supervivencia en conjunto. En escasez ayuda
el primer año (semilla 4: de 12 a 20 vivos) y empeora algo el segundo; la
semilla 9 tiene un segundo invierno extremo que también mata en F2. El
análisis de esas muertes está en §8.

Corregido durante la revisión (antes de las cifras de arriba): con hambre ≥ 700
y sin comida, «resguardarse» se daba por cumplido al momento y el refugio se
volvía a proponer cada hora antes que comer; la persona quedaba quieta al raso
junto a un refugio con sitio libre (semilla 4, abundante, tiempos 888–938). Y
quien pasaba frío peligroso dentro del bosque no usaba un refugio a pocas
celdas. Ambos están corregidos en `genesis/motor/planes.py`.

---

## 4. Revisión de mundos libres

**Condiciones.** `herramientas/revisar_f3.py`: cada semilla se crea con su
configuración normal (25 habitantes, reglas 3, recursos × abundancia), sin
preparar nada, y se simula 2 años (1920 horas). Todo sale del registro de
sucesos y del estado final. Código final; ejecución del 13-11-2026 a las 12:03.

**Comunidad funcional**, tal como la mide la herramienta: una comunidad que
(a) tiene al menos 3 participantes recurrentes (personas que suman 3 o más
entre madera, horas de trabajo, reparaciones, depósitos y usos en sus lugares),
(b) tiene algún lugar todavía utilizable al final, (c) duró al menos 20 días
(hasta su disolución, si se disolvió) y (d) suma al menos 10 usos y
reparaciones en sus lugares. Mide si llegó a funcionar, no si sigue activa:
3 de las 7 disueltas en abundancia y 5 de las 8 disueltas en escasez cuentan
como funcionales.

### Abundante (1,0), 10 semillas

| Semilla | Vivos a1/a2 | Obras inic./term./aband. | Usadas | Reparadas | Estancias | Guardado / retirado | Comunidades (funcionales) | Uniones / salidas | Propuestas (acept./rech.) | Aportan / se benefician |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 25/25 | 12/11/0 | 11 | 10 | 714 | 178 / 12 | 7 (5) | 23 / 3 | 1 (40/10) | 24 / 25 |
| 2 | 25/25 | 11/10/0 | 10 | 10 | 1061 | 139 / 5 | 6 (6) | 22 / 2 | 2 (29/7) | 23 / 25 |
| 3 | 25/25 | 10/8/2 | 8 | 8 | 821 | 126 / 110 | 4 (4) | 22 / 1 | 1 (10/0) | 21 / 25 |
| 4 | 22/22 | 16/14/0 | 14 | 11 | 862 | 252 / 125 | 7 (6) | 17 / 5 | 2 (2/0) | 24 / 25 |
| 5 | 25/25 | 15/15/0 | 15 | 14 | 1119 | 174 / 0 | 9 (8) | 25 / 13 | 1 (10/0) | 25 / 25 |
| 6 | 25/25 | 14/12/1 | 12 | 9 | 849 | 140 / 58 | 7 (5) | 22 / 2 | 1 (1/1) | 21 / 25 |
| 7 | 25/25 | 17/17/0 | 17 | 12 | 740 | 276 / 52 | 7 (7) | 16 / 0 | 1 (4/0) | 23 / 25 |
| 8 | 25/25 | 12/12/0 | 12 | 9 | 1121 | 118 / 0 | 7 (4) | 23 / 8 | 4 (62/11) | 21 / 25 |
| 9 | 25/16 | 14/13/0 | 13 | 3 | 623 | 142 / 86 | 7 (6) | 12 / 15 | 0 | 23 / 25 |
| 10 | 25/25 | 12/12/0 | 12 | 11 | 1022 | 301 / 75 | 6 (6) | 23 / 1 | 2 (28/8) | 25 / 25 |

Totales: 133 obras empezadas, 124 terminadas, 3 abandonadas; 67 comunidades,
57 funcionales; tamaño medio de las no disueltas, 5,7 personas.

### Escasa (0,3), 10 semillas

| Semilla | Vivos a1/a2 | Obras inic./term./aband. | Usadas | Reparadas | Estancias | Guardado / retirado | Comunidades (funcionales) | Uniones / salidas | Propuestas (acept./rech.) | Aportan / se benefician |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 25/25 | 10/10/0 | 9 | 7 | 669 | 94 / 14 | 4 (2) | 15 / 1 | 1 (11/3) | 20 / 25 |
| 2 | 25/15 | 9/9/1 | 8 | 7 | 452 | 105 / 29 | 4 (4) | 11 / 8 | 0 | 16 / 22 |
| 3 | 25/15 | 13/11/3 | 11 | 3 | 471 | 138 / 127 | 5 (4) | 11 / 10 | 1 (0/1) | 18 / 22 |
| 4 | 20/15 | 17/15/2 | 15 | 1 | 361 | 143 / 80 | 7 (6) | 2 / 3 | 0 | 19 / 15 |
| 5 | 25/25 | 16/16/0 | 16 | 13 | 922 | 284 / 131 | 7 (7) | 11 / 4 | 1 (2/0) | 25 / 25 |
| 6 | 25/25 | 13/13/1 | 13 | 8 | 768 | 165 / 112 | 4 (4) | 20 / 2 | 3 (15/3) | 22 / 25 |
| 7 | 25/24 | 12/10/2 | 10 | 6 | 606 | 136 / 136 | 5 (5) | 11 / 1 | 1 (2/0) | 23 / 25 |
| 8 | 25/19 | 10/10/0 | 9 | 9 | 899 | 319 / 248 | 6 (4) | 15 / 13 | 4 (13/2) | 24 / 25 |
| 9 | 19/8 | 9/8/1 | 8 | 2 | 392 | 71 / 71 | 3 (2) | 6 / 10 | 0 | 12 / 18 |
| 10 | 25/25 | 15/13/0 | 13 | 8 | 932 | 294 / 159 | 7 (6) | 32 / 2 | 4 (15/0) | 23 / 25 |

Totales: 124 obras empezadas, 115 terminadas, 10 abandonadas; 52 comunidades,
44 funcionales; tamaño medio de las no disueltas, 5,1 personas.

«Propuestas» es el número de acuerdos propuestos; entre paréntesis, las
aceptaciones y los rechazos individuales (cada miembro responde por su cuenta).
En escasez se saca casi tanto como se guarda; en abundancia, mucho menos
(semillas 5 y 8: nada), como era de esperar.

Fuentes: [f3/revision-abundante.txt](f3/revision-abundante.txt) /
[.json](f3/revision-abundante.json) y
[f3/revision-escasa.txt](f3/revision-escasa.txt) /
[.json](f3/revision-escasa.json).

---

## 5. Cadenas causales

Cada suceso guarda, si la hay, su **causa registrada**: el identificador del
suceso que la decisión tuvo en cuenta al tomarse. Eso es distinto de la mera
**sucesión temporal** (que una cosa pase después de otra). Abajo solo se
presenta como causa lo que el registro enlaza; lo demás se marca como
sucesión. Todos los ejemplos son de **mundos libres** (sin preparar nada),
repetidos desde su semilla al cerrar este documento con
`herramientas/revisar_f3.py` y un script de consulta; los identificadores son
los del registro. Las escenas controladas de §2 son otra cosa: allí la
situación se prepara a propósito para comparar con y sin refugio, con y sin
información, etc.

### A. Lo que uno vivió llega a otro y cambia lo que hace
Semilla 10, abundancia 1,0.

1. `701` — año 1, primavera día 7, 07:00 — `obra.iniciada`: **Kiro** empieza el
   Refugio del Robledal. Razones guardadas: buscaba abrigo, 5 noches al raso.
   (Las noches son un recuento de su memoria, no un suceso: no hay causa
   registrada aquí.)
2. `792` — primavera día 8, 06:00 — `lugar.informa`: Kiro le cuenta a
   **Oren** la obra. Causa registrada: `701`.
3. `1485` — verano día 5, 03:00 — `refugio.estancia`: Oren pasa 4 horas en el
   refugio (fuera, 21,1 °C). Causa registrada: `792` (lo supo por Kiro).

Matiz: el registro muestra que el conocimiento de Oren procede de Kiro; no
demuestra qué habría hecho sin esa información. Esa comparación está en la
escena controlada `test_una_informacion_recibida_lleva_a_usar_un_refugio...`.

### B. Una mala experiencia lleva a construir
Semilla 3, abundancia 0,3.

1. `5713` — año 1, invierno día 8, 06:00 — `habitante.intemperie`: **Maku** sufre
   frío peligroso (−7,4 °C).
2. `6698` — año 2, primavera día 6, 08:00 — `obra.iniciada`: Maku empieza el
   Refugio del Prado. Razones: buscaba abrigo, 14 noches al raso. Causa
   registrada: `5713`.

Semilla 10, abundancia 1,0: `275` (año 1, primavera día 1, 15:00,
`habitante.fuente_agotada`: **Mira** va a por bayas y Elmo se le adelanta) →
`1525` (verano día 5, 13:00, `obra.iniciada`: Mira empieza el Depósito del
Prado para una reserva común; causa registrada `275`).

Semilla 8, abundancia 0,3: `3135` (verano día 5, `habitante.viaje_fallido`:
**Cira** no encuentra bayas) → `3698` (verano día 7, `obra.iniciada`: Cira
empieza el Depósito de la Loma; causa registrada `3135`).

### C. Quedarse sin sitio lleva a proponer un acuerdo
Semilla 8, abundancia 0,3.

1. `3464` — `obra.terminada`: el Refugio de los Juncos queda en pie.
2. `3784` — verano día 8, 02:00 — `refugio.sin_sitio`: **Dumo** no cabe (6 de 6).
3. `4987` — otoño día 3, 15:00 — `acuerdo.propuesto`: Dumo propone a **Cira**
   «prioridad para quien está en apuros». Causa registrada: `3784`.
4. `4988` — misma hora — `acuerdo.aceptado`: Cira lo acepta. Causa: `4987`.

Semilla 10, abundancia 1,0, misma estructura: `7115` (año 2, otoño día 10,
`refugio.sin_sitio` de Uma, en apuros) → `7139` (Elai propone el acuerdo a
Nilo; causa `7115`) → `7140` (Nilo acepta; causa `7139`).

### D. Cesiones de sitio: solo sucesión, no causa registrada
`refugio.cede_sitio` lleva en sus datos el identificador del acuerdo
(`acuerdo`), pero su campo causa apunta al último suceso del refugio (su
terminación o una reparación), no a la aceptación del acuerdo. Ejemplo: semilla
10, abundante, `8001` y `8003` (año 2, invierno día 9, 07:00) tienen como causa
`7359`, una reparación. Que el acuerdo influyó es cierto por construcción (solo
cede quien lo ha aceptado), pero **el registro no lo enlaza como causa**. La
herramienta de revisión etiqueta estos casos como «acuerdo→cede»; esa etiqueta
debe leerse como sucesión. Auditoría completa:
[f3/auditoria-cadenas.json](f3/auditoria-cadenas.json).

### Recuento en las 20 ejecuciones de la revisión
De la auditoría (repetidas al cerrar este documento):

- Estancias en refugio cuyo origen es una información: 3516 en abundancia y
  2322 en escasez; **todas** tienen como causa registrada un `lugar.informa`.
  Ojo: el origen se conserva en estancias posteriores, así que indica de dónde
  vino el conocimiento, no que cada estancia se decidiera por él. 35 % y 41 %
  de ellas fueron con frío fuera.
- Obras con una vivencia concreta como causa registrada: 17 de 133 en
  abundancia y 44 de 124 en escasez (fuentes agotadas, viajes fallidos, frío,
  hambre grave). Las demás se deciden por recuentos de memoria sin un suceso
  único enlazado.
- Cesiones de sitio: 10 por configuración; ninguna con el acuerdo como causa.

---

## 6. Rendimiento

Equipo: i5-14400F, RTX 5070, 16 GB, Windows 11, Python 3.14.

| Medida | Resultado | Condiciones | Fuente |
| --- | --- | --- | --- |
| Velocidad de simulación | F2: 2,54 s por 1920 h (~756 h/s). **F3: 3,59 s (~535 h/s), un 29 % más lento** | `ejecutar.py simular`, semilla 5, 25 habitantes, 2 tandas de 40 días, con guardado | Medido al cerrar este documento |
| Tamaño de partida | F2: 1,16 MB y 4940 sucesos en 2 años. **F3: 2,31 MB y 9036 sucesos** | Mismas partidas, tras consolidar el WAL | Medido al cerrar |
| Coste por hora con mucha historia | ~+20 % a los 5 años (1,79 s frente a 1,49 s por año) | Partida «aldea» (semilla 3) frente a una nueva de la misma semilla | **Solo en el registro de la sesión anterior**; además «aldea» mezcla políticas (§7) |
| Consultas | ≤ 15 ms (ficha de comunidad la más cara; ficha de lugar ~3 ms; lista de lugares ~2 ms) | API local, partida «aldea» a ~5 años | **Solo en el registro de la sesión anterior** |
| Fluidez, escena de referencia de F2.5 | Reglas 2 y 3 iguales: 153–180 cuadros/s, p95 5,7–11,2 ms, ninguna tarea larga | 1440×900, Chrome sin ventana con la GPU, semilla 9 escasa, mismos casos que la medida de F2.5 | [f3/medidas/medida-f3-r2.json](f3/medidas/medida-f3-r2.json), [medida-f3-r3.json](f3/medidas/medida-f3-r3.json); referencia: [f25/pasada2/medida-pasada2.json](f25/pasada2/medida-pasada2.json) |
| Fluidez con muchas construcciones | 168–180 cuadros/s, p95 5,7 ms, sin tareas largas | 1440×900, «aldea» con 16 construcciones, vistas cerca, medio y a 480 h/s | [f3/medidas/medida-aldea.json](f3/medidas/medida-aldea.json) |

El estado de cada construcción y comunidad tiene historias acotadas
(`_HISTORIA_MAX`); las memorias, 10 lugares por persona. Lo que crece sin
límite es el número de construcciones (las ruinas permanecen) y el registro
de sucesos en disco, que es lo que explica el aumento de coste con los años.

---

## 7. Capturas, uso, compatibilidad y archivos

### Capturas reales (`docs/f3/`)
- [r1280-ficha-refugio.jpg](https://github.com/elmundopol-web/genesis/blob/cbff73da3b4b63d451320d4e6426f4be3d3faf3c/docs/f3/r1280-ficha-refugio.jpg),
  [r1440-ficha-refugio.jpg](https://github.com/elmundopol-web/genesis/blob/cbff73da3b4b63d451320d4e6426f4be3d3faf3c/docs/f3/r1440-ficha-refugio.jpg),
  [r1920-ficha-refugio.jpg](https://github.com/elmundopol-web/genesis/blob/cbff73da3b4b63d451320d4e6426f4be3d3faf3c/docs/f3/r1920-ficha-refugio.jpg): la ficha del Refugio
  del Prado a tres resoluciones (semilla 3, invierno del año 1).
- [cerca-dia.jpg](https://github.com/elmundopol-web/genesis/blob/cbff73da3b4b63d451320d4e6426f4be3d3faf3c/docs/f3/cerca-dia.jpg): chozas y depósitos de cerca, con nieve.
- [noche-refugios.jpg](https://github.com/elmundopol-web/genesis/blob/cbff73da3b4b63d451320d4e6426f4be3d3faf3c/docs/f3/noche-refugios.jpg): de noche, luz solo en los
  refugios ocupados y una marca por persona.
- [movimiento-obra.gif](https://github.com/elmundopol-web/genesis/blob/cbff73da3b4b63d451320d4e6426f4be3d3faf3c/docs/f3/movimiento-obra.gif): 98 cuadros (560×352) de una
  obra que crece mientras la gente trabaja (semilla 3, otoño del año 1).

Estas capturas se tomaron antes de un último cambio menor: muestran «F2.5» en
la insignia de fase. Ahora la insignia muestra la fase de las reglas de la
partida abierta (F3 en una partida nueva).

### Uso
- **Doble clic en `iniciar.bat`**: abre la partida más reciente con reglas 3
  o crea `semilla-1`. Si `semilla-1` ya existe con reglas 2, la nueva se llama
  `semilla-1-comunidad` (con reglas 1, `-sociedad`; F0, `-habitado`). Las
  partidas anteriores no se tocan. Comprobado en una carpeta temporal.
- **Partida nueva:** `py -3 ejecutar.py nueva --semilla 7 --nombre valle`
  (reglas 3 por defecto; `--reglas 2` o `--reglas 1` para las anteriores;
  `--abundancia 0.3` para un mundo escaso).
- **Ampliar una partida anterior:** `py -3 ejecutar.py ampliar semilla-1`
  crea `semilla-1-comunidad`; la original queda intacta.
- **Revisar mundos libres:**
  `py -3 herramientas/revisar_f3.py --semillas 1-10 --anios 2 --abundancia 1 --json salida.json`.
- En el visor: clic en un refugio o depósito para su ficha; desde ella, la
  ficha de la comunidad; en la ficha de una persona, la pestaña «Comunidad».

### Compatibilidad
| Partida | Reglas | Comportamiento |
| --- | --- | --- |
| F0 | — | Igual que siempre, sin habitantes. |
| F1 | 1 | Reglas de F1; reproducción exacta (huellas fijadas en las pruebas). |
| F2 | 2 | Reglas de F2; reproducción exacta. |
| F3 | 3 | Todo lo anterior más F3. |
| Ampliada | 1→3 o 2→3 (o 1→2→3) | Cada tramo con sus reglas; la meta `etapas` guarda la cadena. |

### La partida de desarrollo «aldea»
Se usó para las capturas, la grabación y algunas medidas. Su historia se
simuló en parte con versiones anteriores de la política (antes de las
correcciones de §3), así que **no se reproduce con el código final**:
`verificar` confirma que sus sucesos guardados no han sido alterados, pero la
repetición diverge. Se conserva tal cual, sin retocar su historia, en
`docs/f3/partidas-desarrollo/original/` (copia exacta, mismo SHA-256 que la de
la carpeta temporal donde se creó). La verificación se hizo sobre otra copia
(`.../verificar/`). Las comprobaciones de reproducción válidas son las de §2,
sobre partidas creadas enteras con el código final.

### Archivos principales
- `genesis/motor/comunidad.py` — construcciones, obras, compromisos, refugio,
  depósitos, conocimiento de lugares, comunidades, acuerdos y contabilidad.
- `genesis/motor/obras.py` — la parte de la política que decide obras,
  resguardo, reservas, informes y acuerdos.
- `genesis/motor/planes.py`, `habitantes.py`, `mente.py`, `config.py` —
  integración con la política, el cuerpo, la memoria y la configuración.
- `genesis/almacen/almacen.py`, `genesis/cli.py`, `genesis/sesion.py` —
  persistencia, ampliación, órdenes y consultas.
- `genesis/visor/estatico/construcciones.js`, `lugares.js` y cambios en
  `mapa.js`, `figuras.js`, `app.js`, `habitantes.js`.
- `pruebas/test_comunidad.py`, `pruebas/test_supervivencia.py`,
  `pruebas/test_interfaz.mjs`.
- `herramientas/revisar_f3.py`.

---

## 8. Límites reales

- **Los refugios no tienen agua, y salir a beber con frío extremo mata.** En
  el segundo invierno de la semilla 9 ni el refugio basta (dentro también se
  pierde salud), y el ciclo letal es salir con sed, cruzar 4–5 horas de raso
  helado hasta el río y quedarse sin abrigo. La mayoría de las muertes que
  quedan en esa semilla ocurren caminando. El emplazamiento del refugio no
  tiene en cuenta la distancia al agua.
- **Cesión de sitio de ida y vuelta (defecto conocido; corregido en
  [F3.1](F3.1-ESTADO.md) para partidas nuevas).** Cuenta como «en
  apuros» cualquiera expuesto al frío, y cede cualquier ocupante con salud ≥ 700
  que acepte el acuerdo. Quien acaba de entrar puede devolver el sitio en la
  misma hora: semilla 8 escasa, `7590` (Juna cede a Hebe) y `7592` (Hebe cede a
  Juna), año 2, primavera día 1, 01:00. En cada configuración (10 semillas,
  2 años) hay 10 cesiones; 3 las hace alguien que acababa de recibir sitio en
  esa misma hora, y 2 de esas 3 forman un par de ida y vuelta.
  No rompe la contabilidad (las plazas se respetan), pero produce sucesos sin
  efecto y una lectura engañosa. No se ha corregido en esta entrega.
- **La cesión no enlaza el acuerdo como causa** en el registro (§5 D);
  corregido en [F3.1](F3.1-ESTADO.md) para cesiones nuevas.
- **Acuerdos poco frecuentes:** 0–4 propuestas por mundo en 2 años; en 4 de
  20 ejecuciones, ninguna. Casi todas son de «prioridad para quien está en
  apuros», nacidas de quedarse sin sitio.
- **Fragmentación en comunidades pequeñas:** 4–9 comunidades por mundo de 25
  personas, de unas 5 personas de media; parte de ellas se disuelven. La
  pertenencia limita a cada persona, pero no se fusionan comunidades vecinas.
- **El coste crece con la historia:** más sucesos en disco (casi el doble que
  en F2) y construcciones que no desaparecen; ~+20 % por hora a los 5 años
  (dato del registro anterior, sobre una partida de política mezclada).
- **F3 no mejora la supervivencia en conjunto** frente a F2 (§3): ayuda en el
  primer año de escasez y empeora algo el segundo.
- **Estancias templadas:** muchas estancias son para descansar con buen
  tiempo (65 % de las informadas en abundancia sin frío fuera); el refugio
  sirve también de dormitorio, no solo de abrigo.
- **Lo que no hay:** otras construcciones, fuego, herramientas duraderas,
  agricultura, propiedad, líderes, normas inventadas ni religión.
