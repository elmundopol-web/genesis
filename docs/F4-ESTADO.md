# GENESIS 0.4 · Vidas, generaciones y presencia

## Abrir el mundo y seguir una historia

Abre **iniciar.bat**. Las partidas nuevas empiezan con 25 fundadores. Para continuar una anterior con F4, ejecuta `py -3 ejecutar.py ampliar NOMBRE` y abre `iniciar.bat NOMBRE-f4`. La ampliación se escribe en una copia. Se conservaron los cinco archivos originales de `partidas/` y se compararon sus bytes con el [respaldo anterior a F4](../../genesis-antes-f4-20261114.tar.gz).

1. Elige un habitante en el mapa. En **Familia y vínculos** puedes marcarlo como favorito, abrir la ficha de un familiar y consultar qué experiencia cambió un vínculo. Los favoritos se guardan en esa partida.
2. Para probar el descubrimiento, deja que unos habitantes recorran un bosque. Pulsa **Intervenir**, elige **Abrir un agujero** y señala una celda libre cerca de su camino. El visor muestra la posición y el efecto antes de **Confirmar**. **Cancelar** o **Esc** descartan el objetivo.
3. Avanza por horas. En **Historias**, abre el último cambio y elige un hecho para consultar su causa en la crónica. La orden del jugador, el testimonio de cada persona y su interpretación tienen entradas distintas. Para revisar creencias de un favorito, abre su ficha desde **Historias**.
4. Puedes cerrar el agujero o dejar una ofrenda de 1 a 12 bayas. Hasta 32 intervenciones pueden estar activas. El agujero bloquea una celda y los pasos diagonales que cortarían su esquina. El motor rechaza agua, construcciones, posiciones ocupadas y cortes del único camino. Las bayas quedan en el suelo hasta que alguien las recoge desde el lugar o desde al lado.

## Tres escenas preparadas

Estas escenas controlan posición, experiencias o prioridades para aislar las causas. La prueba de crianza adelanta el calendario e induce la pérdida de los cuidadores. Cada escena tiene su propia numeración. [Eventos completos](f4/escenas.json) · [Generador](../herramientas/escenas_f4.py)

- **El cambio en el bosque.** La orden 23 abrió el agujero. Sima reconoció el cambio (24), lo consideró inexplicado (25) y lo inspeccionó (26). Rudo recordó el mismo lugar, interpretó una posible advertencia (28) y se apartó (29). Tobo vio el hueco sin reconocer un cambio previo (30). Lejos del bosque, Fedra recibió el relato de Sima (33) y se apartó por lo aprendido (35). Al verlo personalmente formuló su propio juicio (38–40). Tras el cierre (41), los testigos que volvieron a mirar revisaron sus creencias (43, 44 y 46). Un relato conserva el origen y los apoyos de la versión transmitida.
- **La palabra de Sima.** Sima prometió a Rudo dos unidades de alimento (19). Con mayor prioridad por cumplir, le entregó la ración (20). Al priorizar la protección, entregó esas mismas unidades a Tobo, que pasaba hambre. Rudo interpretó la entrega como una ruptura (21), tomó distancia (22) y aceptó una restitución posterior (24). Al hacer visible hambre grave en Tobo, Rudo juzgó justificada la decisión y siguió cerca de Sima. Las tres variantes registran el destino real de la comida y el motivo. Una restitución aceptada recupera parte de la confianza.
- **Lo que Fedra Sima conservó.** Nació con padres conocidos e inventario y memoria personal vacíos (19). Sima le enseñó una orilla (20). Tras las muertes de Sima y Rudo (21–22), Tobo pasó a cuidarla (23). Con sed, Fedra Sima caminó hacia el agua (24). La causa de ese desplazamiento sigue siendo la lección 20 de Sima. El cambio de cuidador conservó a ambos progenitores.

## Mundos libres

**Supervivencia al primer año.** En 18 de 20 semillas abundantes sobrevivieron los 25 fundadores. Las semillas 4 y 15 terminaron con 19 y 22. Se alcanzó el criterio de al menos 23 fundadores en 18 semillas. En conjunto sobrevivieron **491 de 500 fundadores**. Hubo **134 nacimientos**, **128 descendientes vivos** y **6 muertes infantiles**. La población final agregada fue **619**. El 95,5 % de los nacidos seguía vivo al corte anual; cada menor llevaba un tiempo distinto de exposición. F3.1 había superado el criterio en 19 semillas. [Resultados por semilla](f4/cohorte.json)

En esas 20 semillas hubo 38 promesas, 9 juicios tras incumplimientos, 6 intentos de reparación y una devolución de ayuda motivada por gratitud. La conducta de tomar distancia tras una ruptura solo se confirmó en la escena preparada dentro de esta muestra. No se asigna un conflicto obligatorio a ninguna pareja.

**Comparación pareada.** Semilla 3, 25 fundadores y dos años por mundo. Dentro de cada par cambia únicamente una orden externa a la hora 24. La ubicación se elige junto al recorrido de un habitante, que difiere entre abundancias. [Órdenes, recuentos y huellas finales](f4/pares.json)

| Recursos | Intervención | Fundadores vivos | Nacimientos | Menores vivos | Población final | Observaciones / inspecciones / relatos |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 100 % | Ninguna | 24 | 9 | 5 | 29 | 0 / 0 / 0 |
| 100 % | Agujero en (36, 29) | 21 | 10 | 5 | 26 | 12 / 8 / 13 |
| 30 % | Ninguna | 14 | 5 | 1 | 15 | 0 / 0 / 0 |
| 30 % | Agujero en (27, 24) | 15 | 6 | 0 | 15 | 13 / 8 / 11 |

En abundancia, 12 de los 13 relatos transmitieron «hendidura estable» y uno «posible advertencia». En escasez predominó «posible advertencia» (9 de 11). Las dos versiones dieron lugar a investigación, evitación y peticiones de compañía. La última consecuencia registrada del agujero llegó 1.400 horas después de la orden abundante y 1.613 después de la escasa. Son intervalos entre hechos vinculados; una persona no dedicó todas esas horas al agujero. Se comprobó el abandono de una hipótesis tras cerrar el hueco en la escena preparada. Las diferencias demográficas de estos dos pares corresponden a una sola semilla.

**Continuidad generacional.** En la semilla 3 abundante, sin intervenciones, el primer nieto apareció en el recuento del año 14. Al año 29 habían nacido 31 descendientes, incluidos cinco nietos o descendientes posteriores con un progenitor nacido en la partida. Quedaban vivos cinco fundadores y dos descendientes, uno de ellos adulto y uno perteneciente a esas generaciones posteriores. La población total era siete. Se registraron 23 muertes antes de los cuatro años, 31 enseñanzas de orilla, 30 enseñanzas de recolección, 42 promesas y 3 reparaciones. La cadena de una promesa llegó a abarcar 71 horas. En otro mundo de 40 fundadores, con un agujero, ocho nacimientos llevaron la población al límite de 48; todos estaban vivos al segundo año. [Medidas anuales de ambas poblaciones](f4/generaciones.json)

## Reglas, memoria y límites

- **Motivaciones y trato.** Pertenencia, independencia, protección y palabra parten de los rasgos de cada persona. La convivencia, la ayuda, la crianza y el cumplimiento cambian vínculos dirigidos. Afecto y confianza pueden divergir. Una promesa especifica emisor, beneficiario, testigos, dos unidades de comida y un plazo de 12 horas. Los recursos y el contacto se comprueban al ejecutar. La simulación guarda lo que vio el beneficiario y su juicio. El catálogo de compromisos personales de F4 se centra en comida; los compromisos de obra siguen las reglas de F3.
- **Reflexión.** El mundo mantiene terreno, recursos y hechos. Cada persona conserva visitas, origen y hora de las observaciones, relatos, confianza y apoyos. Una función local sustituible elige entre cambio inexplicado, hueco natural, peligro, advertencia, posible regalo y otras revisiones acotadas. La gratitud y el temor expresan una atribución tentativa. El motor ejecuta acciones permitidas y la interfaz lee el registro. El juego funciona sin modelos de lenguaje, red ni servicios de pago.
- **Familias.** La jornada normal tiene 24 horas y el año 40 días. Dos adultos elegibles pueden iniciar una crianza con contacto local al mediodía, salud suficiente, tres días de encuentros, afecto y comida de reserva junto al agua. Se comprueba la población viva más los nacimientos pendientes. La espera dura una estación y se resuelve al cierre del día. Entre nacimientos de un mismo adulto deben pasar tres años. Los identificadores crecen con los nacimientos. El límite predeterminado de 48 se configura al crear el mundo, por ejemplo con `py -3 ejecutar.py nueva --semilla 7 --nombre valle --limite-poblacion 64`.
- **Cuidados.** El menor empieza con paso 1, carga 3, vista 2 y destreza 1. A los 4 años pasa a aprendiz y a los 12 adquiere capacidades adultas. Son etapas de juego. Alimentar consume comida y un turno del cuidador. Un cuenco transporta una ración de agua, se llena en la orilla y se entrega junto al menor. El libro de agua comprueba llenados, entregas y raciones transportadas. Acompañar consume desplazamiento y proteger da abrigo temporal. La lección de recolección requiere alimento accesible y contacto con el alumno despierto.
- **Límites observados.** La ausencia de cuidadores puede producir muchos relevos: hubo 872 en 29 años. El relevo local permitió continuidad familiar, pero 23 de 31 descendientes murieron en la infancia en ese mundo. Las hipótesis son un catálogo diseñado y cada habitante conserva una versión activa por fenómeno. La memoria de F4 limita las visitas recientes a 32 posiciones, las teorías a 16 y los vínculos activos a 24 por persona. La bitácora conserva los eventos históricos. Los fallecidos conservan ficha e identidad, de modo que el tamaño de la partida y algunos recorridos de población siguen creciendo.

## Guardado, regresiones y rendimiento

La configuración conserva las horas de activación de sociedad, comunidad, corrección F3.1 y vidas. `ampliar` lee el origen y crea una copia SQLite coherente. La reproducción intercala extracciones externas e intervenciones por hora e identificador del evento. El recorrido del navegador se reprodujo hasta la hora 812 con 3.726 eventos y una orden externa. Coincidieron mapa, integridad de la bitácora, eventos y estado final. Las pruebas cubren también recarga con hijos y maestros, tres órdenes de intervención alternadas con una extracción y rechazo de terrenos inválidos antes de registrar la orden. [Verificación del visor](f4/visor.json)

**311 pruebas Python** y **16 pruebas JavaScript** pasaron. Incluyen las huellas históricas, la activación en copia, avanzar y cancelar un salto, los tres desenlaces personales preparados, la atribución con procedencia y la selección de fichas con respuestas fuera de orden. [Regresión Python](f4/regresion-final.txt) · [Regresión JavaScript](f4/javascript.txt)

El ensayo de coste usa la semilla 5. Se midieron ventanas de 120, 840 y 120 horas. Estos valores corresponden a la última ventana, al alcanzar la hora 1.080. La lectura incluye la lista de historias y un detalle. El caudal mide solo simulación. [Resultados completos y órdenes de intervención](f4/coste.json)

| Fundadores / agujeros | Vivos | Vínculos | Eventos | Horas simuladas/s | Guardado | Lectura |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 / 0 | 11 | 22 | 1.931 | 1.338 | 9,6 ms | 0,12 ms |
| 25 / 0 | 34 | 200 | 7.369 | 296 | 43,7 ms | 1,21 ms |
| 25 / 8 | 33 | 247 | 7.711 | 266 | 47,6 ms | 2,03 ms |
| 40 / 8 | 48 | 478 | 12.419 | 182 | 65,4 ms | 1,44 ms |

En Chrome local, una muestra corta con el visor en pausa dio 5,6 ms de mediana y 10,2 ms de percentil 95 entre cuadros. El GIF muestra el juego en marcha. Los tiempos dependen del equipo y de la escena.

### Repetir las comprobaciones

Desde la carpeta de GENESIS:

```bat
probar.bat
py -3 herramientas/escenas_f4.py
py -3 herramientas/revisar_f4.py --modo cohorte
py -3 herramientas/revisar_f4.py --modo pares
py -3 herramientas/revisar_f4.py --modo generaciones
py -3 herramientas/coste_f4.py
py -3 ejecutar.py verificar NOMBRE
```

La comprobación gráfica opcional `py -3 herramientas/capturas_f4.py` usa Chrome, Playwright y Pillow en una partida temporal. Verifica cancelar y confirmar en el mapa, navegar una historia y conservar un favorito. El juego y la simulación Python utilizan la biblioteca estándar.

### Capturas reales

- [1280 × 720 · Previsualización del cierre de un agujero](f4/1280x720-intervencion.jpg)
- [1440 × 900 · Descubrimiento de Nilo en la crónica](f4/1440x900-historia.jpg)
- [1920 × 1080 · Familia de Mira Suni y su maestra](f4/1920x1080-familia.jpg)
- [Muestra de movimiento · GIF](f4/movimiento.gif)

