# GENESIS F2 — Estado de desarrollo

Memoria, aprendizaje y sociedad inicial. **F2 cerrada**, versión 0.2.0-f2.
Estado de entrega, medidas y límites: [F2-ESTADO.md](F2-ESTADO.md).

## Punto de partida comprobado

- 192 pruebas Python y 3 JavaScript pasaban antes de tocar nada (F1, 0.1.0-f1).
- Huellas de F1 fijadas (año completo, semilla 4 abundante y semilla 7 con
  abundancia 0,3): están en `pruebas/test_sociedad.py::PruebasReglasDeF1`.
- Copia de F1 previa a los cambios: carpeta `respaldo-f1` del directorio temporal de la sesión.

## Hito 1 — Motor: experiencia → recuerdo → decisión distinta (TERMINADO)

Archivos nuevos: `genesis/motor/mente.py`, `sociedad.py`, `planes.py`,
`pruebas/test_sociedad.py`. Modificados: `config.py` (reglas, activación,
`ConfigMente`), `habitantes.py` (ganchos, percepción ampliada), `decisiones.py`
(acciones entre personas), `mundo.py`, `motor/__init__.py`.

- Reglas versionadas: `ConfigHabitantes.reglas` (1 = F1, 2 = F2). Con reglas 1 el
  motor es el de F1, bit a bit (huellas idénticas).
- Memoria episódica acotada (32), consolidación, olvido determinista, recuperación.
- Creencias: lugares vistos, indicaciones recibidas (fuente, antigüedad,
  confianza), lugares vistos vacíos; corrección al observar.
- Objetivos con planes (`planes.py`), prioridades, interrupción solo por algo
  más importante y realizable; razones guardadas al decidir (`porque`).
- Tratos: pedir, dar, negar, contar; entregas atómicas; relaciones dirigidas.
- Pruebas de comportamiento en `test_sociedad.py`, todas pasan, incluidas
  las últimas correcciones de continuidad con mal tiempo y memoria causal.

## Hito 2 — Persistencia y compatibilidad (TERMINADO)

- El estado de la mente va dentro de cada habitante solo con reglas 2.
- `almacen.ampliar_partida` + orden `ampliar`: copia una partida F1, deja el
  original intacto y activa las reglas 2 desde la hora de la copia
  (`sociedad.activada`). Comprobado: eventos previos idénticos y `verificar`
  exacto en original y copia.
- CLI: `nueva --reglas`, `ampliar`, nombres `-sociedad`, `listar` indica reglas.

## Hito 3 — Sesión y API (TERMINADO)

`genesis/sesion.py` y `genesis/visor/servidor.py`: ficha con recuerdos,
creencias, objetivo, conocidos y tratos; resumen sobre todo el salto;
historia de ambos participantes; módulo de mente y filtro social servidos.
Verificado en `pruebas/test_sociedad_en_sesion.py`.

## Hito 4 — Visor y experiencia de observación (TERMINADO)

`mente.js`, `habitantes.js`, `app.js`, `mapa.js`, `estilo.css` e `index.html`
integran los cuatro bloques de la mente, creencias sobre el mapa, indicadores
de tratos y rutinas agrupadas. Recuerdos y decisiones enlazan con episodios,
causas, consecuencias y participantes. Entregas etiquetadas con su cantidad
y hambre en porcentaje; ficha separada del zoom en escritorio compacto.

Revisadas fichas en abundancia y escasez, avance de hora y año, pausa,
seguimiento, resumen social y cancelación desde el visor. Capturas nuevas
en `docs/f2-trato.jpg` y `docs/f2-creencias.jpg`. Tamaños de prueba: 1280×720,
1440×900 y 1920×1080 (redondeo interno inferior a un píxel).

## Hito 5 — Pruebas, medidas y entrega (TERMINADO)

- **259 pruebas Python y 5 JavaScript pasan**. Python: 246,738 s; cero
  fallos o errores. Incluyen migración, conservación, determinismo, F1/F0,
  comportamiento y supervivencia; los umbrales permanecen iguales.
- Supervivencia F2: 20/20 semillas abundantes con ≥23 vivos; 8/10 a
  abundancia 0,3 y 1/10 a 0,12. Los datos definitivos sustituyen las medidas
  preliminares. Comparación detallada en `F2-ESTADO.md`.
- `herramientas/medir_f2.py`: cinco repeticiones comparables de F1/F2,
  memoria, seis años de simulación, archivos SQLite y latencias de sesión.
  Resultado en `f2-medidas.json`.
- `herramientas/revisar_f2.py`: traza de mundos libres, sin actores
  colocados ni acontecimientos añadidos. Ejemplos y distinción de pruebas
  controladas en `F2-CADENAS.md`.
- README actualizado y enlace de captura reparado. Las partidas originales
  se conservaron; la revisión usó bases nuevas fuera de `partidas/`.

## Continuación

No queda implementación pendiente del alcance de F2. Reciprocidad rara,
geografía conocida, coste adicional del motor y fluidez variable son límites
documentados. F3 requiere su propio alcance; no se han añadido lenguaje,
generaciones, grupos ni deliberación con modelos en este cierre.
