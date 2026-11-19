# GENESIS · Estado del proyecto

Resumen de todo el proyecto en un solo sitio: qué es, qué hay hecho, por dónde vamos y qué falta.
Cada fase tiene además su informe detallado en esta carpeta, enlazado abajo.
Última actualización el 18/11/2026.

## Qué es

GENESIS es un simulador experimental de civilizaciones. Los habitantes tienen memoria, creencias, objetivos y relaciones, y el jugador observa e interviene como experimentador.

Principios fijados desde el inicio:
- El motor decide todo lo que pasa: nada se inventa para decorar, y cada hecho tiene una causa registrada.
- Las partidas son reproducibles: la misma semilla da la misma historia.
- Cada fase conserva las reglas de las anteriores: una partida vieja se reproduce igual y `ejecutar.py ampliar` crea una copia con las reglas nuevas.
- No se finge conciencia ni exactitud científica.

**Dónde está:** `C:\Users\elmun\Desktop\Juego\genesis\`
- Para abrir el juego, `iniciar.bat`. Para las pruebas, `probar.bat`. La guía de uso está en el [README](../README.md).
- `genesis\motor\` (simulación), `genesis\almacen\` (partidas en SQLite), `genesis\sesion.py` y `genesis\visor\` (visor web en el navegador).
- `assets\`: el arte ilustrado que aporta el usuario. `partidas\`: las partidas guardadas, que nunca se tocan en las pruebas.
- Python solo con la biblioteca estándar. Las herramientas de `herramientas\` usan además PIL y numpy, y las capturas usan Chrome sin ventana con `cdp.mjs`.

**Versión actual:** `0.5.2-f52`: reglas F4.3, visor de F4.4 y F5 opcional (`--mente ID`). El cierre de F4.4 verifica 30 pruebas de interfaz y 18 de sesión, servidor y comandos.

## Fases terminadas

| Fase | Qué añadió | Informe |
|---|---|---|
| **F0** | Mundo determinista de 64 × 64 celdas: terreno, río, bosque, clima, estaciones y recursos que crecen y se agotan. | [README](../README.md) |
| **F1** | 25 habitantes con hambre, sed, energía y salud. Exploran, recogen, comen, beben, descansan, envejecen y mueren. Visor con mapa, crónica y fichas. | [F1-ESTADO.md](F1-ESTADO.md) |
| **F2** | Memoria episódica, creencias que se corrigen, objetivos con planes y tratos entre personas (pedir, dar, negar, indicar lugares) con relaciones dirigidas. | [F2-ESTADO.md](F2-ESTADO.md) |
| **F2.5** | Salto visual por código: mapa pintado, personas con poses, retratos e interfaz oscura sobre el mapa. | [F2.5-ESTADO.md](F2.5-ESTADO.md) |
| **F3** | Comunidades: talar madera, construir y reparar refugios y depósitos, compromisos, acuerdos, unirse y marcharse. | [F3-ESTADO.md](F3-ESTADO.md) |
| **F3.1** | Corrige las cesiones de sitio en los refugios (con razón real y causa fiel). | [F3.1-ESTADO.md](F3.1-ESTADO.md) |
| **F4** | Vidas y generaciones: parejas, nacimientos, familia, duelo, promesas y favoritos. «Intervenir» abre agujeros y deja ofrendas. «Historias» reúne las consecuencias. | [F4-ESTADO.md](F4-ESTADO.md) |
| **F4.1** | Crianza estable: un referente para cada menor, encargos de cuidado, relevos y vida cotidiana. | [F4.1-ESTADO.md](F4.1-ESTADO.md) |
| **F4.2** | Crecer y mantener una familia: aprendices, lecciones que pasan de padres a hijos, provisiones antes del nacimiento. Llegan adultos y nietos. | [F4.2-ESTADO.md](F4.2-ESTADO.md) |
| **F4.2.1** | Auditoría de 20 mundos. Los conflictos ocurren pero casi no cambian decisiones, y en el mapa no se ven. | [F4.2.1-AUDITORIA.md](F4.2.1-AUDITORIA.md) |
| **F4.3** | Relaciones coherentes: una entrega a quien la esperaba cumple la promesa, el juicio sale de la perspectiva de cada persona, los antecedentes pesan y el perdón tiene tres desenlaces. En el visor: el receptor real, poses nuevas, señales breves y senderos. | [F4.3-ESTADO.md](F4.3-ESTADO.md) |
| **F4.4** | Visor ilustrado con habitantes orientados al caminar y beber, construcciones pintadas, claros y bosques más variados, río con corriente y bajíos, y sombras integradas con el terreno. | [F4.4-ESTADO.md](F4.4-ESTADO.md) |
| **F5.0** | Un habitante decide con un modelo local (Qwen vía Ollama) qué hacer ante un agujero. La ficha muestra qué vio, qué recuerdo influyó, qué hizo y qué pasó después; la partida se repite sin el modelo. Cerrada en F5.1. | [F5.0-ESTADO.md](F5.0-ESTADO.md) |
| **F5.1** | Lo que uno cuenta cambia lo que otro hace: Unai se lo cuenta a Brisa y ella decide por ese relato. La consulta al modelo no detiene el mundo.  | [F5.1-ESTADO.md](F5.1-ESTADO.md) |
| **F5.2** | La voz divina: «Hablar a un habitante». Solo esa persona lo oye y lo interpreta según lo que sabe; si toca un agujero que reconoce, decide con el modelo. Pendiente de que el usuario la pruebe. | [F5.2-ESTADO.md](F5.2-ESTADO.md) |

## Base visual aprobada

El 18/11/2026 el usuario dio por bueno el acabado de **F4.4** para seguir con el desarrollo. Esta entrega corresponde al visor. [Informe de F4.4](F4.4-ESTADO.md).

- Escena fija: semilla 14, día 98 a las 10 h, cámara en (39,5; 26,5), a 40 px por celda.
- Integrado el arte ilustrado de `assets/`, preparado por `herramientas/preparar_arte.py` en `genesis/visor/estatico/arte/` y colocado por `sprites.js`:
  - **Habitantes.** Marcha frontal, de perfil y de espaldas, con los colores de cada persona. En la ribera giran, se agachan, beben de rodillas y se incorporan. [Clip de Nura](f4.4/habitantes/nura-en-el-rio.mp4).
  - **Construcciones:** dos chozas y el depósito, lleno o vacío.
  - **Naturaleza.** Cinco siluetas de árbol, claros con suelo visible, hierbas agrupadas y transiciones de tierra húmeda en la ribera. [Comparar a dos escalas y en invierno](f4.4/paisaje/comparar.html).
- Corrección posterior, a petición del usuario:
  - Ya no hay cuadrados alrededor de los árboles.
  - Cada estación tiene un color vivo y nunca gris; en invierno hay nieve real.
  - El bosque es más ligero, la orilla es una curva continua con su franja húmeda y el río se hiela cuando el motor lo dice.
  - Los habitantes llevan un contorno fino.
- Rendimiento final en la máquina de prueba (RTX 5070, 1440 × 900): 88,9 fps en el claro a escala habitual y 81,1 fps en la vista general.
- Capturas: [cuatro momentos del año](f4.4/estaciones/cuatro-momentos.jpg) y [todas las de F4.4](f4.4/).

**Última pasada visual.** El cauce muestra bajíos y pinceladas de corriente. Los senderos llegan hasta los umbrales y las chozas proyectan una sombra suave sobre el prado. [Comparar las cuatro vistas](f4.4/acabado/comparar.html) · [Recorrer el prado, el río y el bosque](f4.4/acabado/despues/prado-ribera-bosque.mp4).

**Mejoras visuales para futuras pasadas.** Poses específicas para recoger, pescar, construir, cuidar y hablar. Acabado ilustrado de obras, ruinas y edificios abandonados. Variantes de edad y ajustes de la vegetación por estación.

## Siguiente fase

**F5.2, la voz divina, está entregada y pendiente de que la pruebes.**
- Le hablas a Brisa y ves cómo lo interpreta y qué hace.
- Demostración: `py -3 herramientas/demo_f52.py` y después `iniciar.bat f52-demo --carpeta partidas/f52`.
- Resultados: [F5.2-ESTADO.md](F5.2-ESTADO.md).

La pasada de observación permite seguir la reacción en el mapa y abrir la historia desde el encuentro. [Antes y después](f5.2/observar/comparar.html) · [Recorrido de Brisa](f5.2/observar/brisa-y-unai.mp4).

## Copias de seguridad

Todas en `C:\Users\elmun\Desktop\Juego\`:
- `genesis-antes-f4-20261114.tar.gz` y `genesis-antes-f41-20261114-215838.tar.gz`: antes de F4 y de F4.1.
- `genesis-antes-f43-20261115.tar.gz`: antes de F4.3.
- `genesis-f44-etapa1-20261115.tar.gz`: el estilo dibujado por código, antes del arte ilustrado.
- `genesis\docs\f4.4\antes-arte\codigo\`: copia local del visor anterior a la integración del arte ilustrado.

## Diarios de desarrollo por fase

Para retomar el trabajo hito a hito:
- [F2-ESTADO_DESARROLLO.md](F2-ESTADO_DESARROLLO.md)
- [F2.5-ESTADO_DESARROLLO.md](F2.5-ESTADO_DESARROLLO.md)
- [F3-ESTADO_DESARROLLO.md](F3-ESTADO_DESARROLLO.md)
- [F3.1-ESTADO_DESARROLLO.md](F3.1-ESTADO_DESARROLLO.md)
- [F4-ESTADO_DESARROLLO.md](F4-ESTADO_DESARROLLO.md)
- [F4.1-ESTADO_DESARROLLO.md](F4.1-ESTADO_DESARROLLO.md)
