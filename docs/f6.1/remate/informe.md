# F6.1 · Remate de la escena de Unai

[Escena final sin rótulos · 8,9 s](despues-sin-rotulos.mp4) · [Escena anterior sin rótulos · 10,8 s](antes-sin-rotulos.mp4)

Los dos vídeos son tomas continuas del visor en Chrome, sobre el mundo libre de la semilla 13 con 24 fundadores. La partida empieza en la hora 849. La cámara sigue a Unai (#25) a 44 píxeles por celda y una hora simulada por segundo. Grabé a 1440 × 900 y recorté los mismos márgenes para acercar la atención al encuentro. El tamaño de las figuras en píxeles se conserva. La captura anterior tiene menor cadencia de origen.

| Suceso real | Hora del motor | Primera hora de la respuesta visible antes | Primera hora de la respuesta visible después |
| --- | ---: | ---: | ---: |
| Kora entrega seis bayas | 852 | 852 | 852 |
| Hesk se niega | 856 | 857 | 856 |
| Gala entrega seis bayas | 857 | 860 | 857 |

En la primera toma, la entrega de Kora seguía ocupando la pantalla en la hora 854, cuando Unai ya debía ir hacia Hesk. Los tiempos del gesto ahora dejan que retome el camino. Al llegar, Hesk niega con la cabeza y se da la vuelta, y Unai baja la cabeza. Gala está llegando a la misma casilla. Unai gira en el sitio y le pide comida al quedar frente a ella.

## Cambios

- [Encuentros](../../../genesis/visor/estatico/encuentros.js) ajusta las duraciones y recalcula la espera si llega primero la siguiente petición del mismo lote.
- [Mapa](../../../genesis/visor/estatico/mapa.js) e [ilustraciones](../../../genesis/visor/estatico/sprites.js) coordinan gestos, orientación, giro y vuelo de la ración cuando la pareja ya está cerca. Cada señal acompaña a su encuentro.
- [Ficha](../../../genesis/visor/estatico/habitantes.js) y tarjeta de seguimiento usan el mismo encuentro para contar quién está hablando. En seguimiento, [la interfaz](../../../genesis/visor/estatico/app.js) evita duplicar entregas y negativas en el anuncio general cuando hay animación.

La pasada reutiliza las poses ilustradas disponibles y las acciones que la simulación ya registra. Las copas densas siguen restando contraste a los gestos, especialmente en el encuentro con Gala. La comparación mide esta escena y deja abierta la valoración de grupos más concurridos.

## Comprobación

- 45 pruebas de interfaz en Node 24, incluida una regresión para la petición que llega antes de la negativa. `node --test pruebas/test_interfaz.mjs pruebas/test_interfaz_f43.mjs pruebas/test_interfaz_f52.mjs pruebas/test_encuentros_f61.mjs`
- 18 pruebas de sesión, servidor y comandos en Python 3.14. `py -3 -B -m unittest pruebas.test_sesion_servidor`
- En Chrome, clics de ratón para cerrar la ficha, volver a abrirla desde Seguimiento y acceder a la crónica desde «Acaba de pasar». A 1280 × 720, 1440 × 900 y 1920 × 1080 la ficha queda dentro de la ventana y la consola queda limpia.
- Las pruebas del navegador usan partidas temporales con el modelo local desactivado. `py -3 -B herramientas/escena_f61.py --carpeta <carpeta nueva>` prepara la escena. Se abre con `py -3 -B ejecutar.py visor f61-encuentro --carpeta <esa carpeta> --sin-modelo`.
