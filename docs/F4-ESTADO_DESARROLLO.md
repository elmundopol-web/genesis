# F4 · Desarrollo y comprobaciones

## Base y respaldo

Se leyó el cierre de F3.1. Antes de editar se archivó la carpeta completa, incluidas las partidas, sus archivos WAL y los materiales anteriores, en `../genesis-antes-f4-20261114.tar.gz`. Se comprobó la lectura del índice de 228 entradas. Las simulaciones, pruebas y capturas utilizan mundos en memoria o bases temporales.

## 1. El bosque

Se añadieron las órdenes, el obstáculo físico, las rutas recalculadas, el cuaderno de visitas, las hipótesis y el relato presencial en `motor/presencia.py`, `vidas.py`, `habitantes.py` y `rutas.py`. La escena preparada pasó antes de desarrollar la crianza. Sima inspeccionó, Rudo evitó y Fedra quedó sin conocimiento hasta el contacto. El siguiente hito fue integrar las decisiones personales y comprobar la difusión en mundos libres.

## 2. La palabra y la familia

`vinculos.py` integra convivencia, ayuda, plazos, entrega real, juicio y restitución. `crianza.py` conecta convivencia con nacimientos, capacidades por etapa, agua transportada, protección, lecciones y sustitución de cuidadores. Los ensayos de tres adultos mostraron que, desde la misma celda, dar un paso bastaba para apartarse; se corrigió el criterio de alejamiento. En la primera corrida de 17 años se observaron pérdidas infantiles altas. Se incorporaron el regreso al último lugar donde se vio al menor y la enseñanza directa de recolección. Las cifras de aquella versión se descartaron para el cierre. Se verificó también que una lección conserva la identidad de la maestra después de su muerte.

## 3. Partidas y visor

`almacen/almacen.py`, `cli.py`, `sesion.py` y `visor/` incorporaron activación en copia, reproducción de órdenes intercaladas con extracciones, favoritos, historias, perspectivas, dibujo de intervenciones y tamaños infantiles. Las expectativas de las regresiones que identificaban F3 como fase actual se actualizaron; la prueba de ampliación histórica F1→F2→F3 sigue ejecutando explícitamente ese recorrido. Se cerró la conexión de lectura que esa prueba dejaba abierta.

La comprobación de navegador recorrió cancelación, confirmación, cronología, selección de persona y favoritos. La revisión visual detectó que los controles nuevos tapaban parte de la fecha en pantallas medianas. Se corrigió su colocación y se repitieron las capturas.

## 4. Verificación final

Las escenas se pueden repetir con `herramientas/escenas_f4.py`. Las simulaciones libres, cohortes y medidas se generan con `revisar_f4.py` y `coste_f4.py`. La prueba de navegador es `capturas_f4.py`. Los resultados finales, las instrucciones de juego y los límites están en [F4-ESTADO.md](F4-ESTADO.md).

