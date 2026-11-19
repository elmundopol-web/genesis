"""GENESIS: simulador experimental de civilizaciones.

Fase F3: mundo determinista con habitantes que recuerdan, se tratan entre sí y
levantan, usan y mantienen lugares compartidos (refugios y depósitos), alrededor
de los cuales se forman comunidades con acuerdos sencillos. Historia individual
y colectiva, guardado en SQLite y visor local con seguimiento y saltos.

Capas, de dentro hacia fuera (cada una solo conoce a las anteriores):

    genesis.motor     mundo determinista; no sabe nada de disco ni de interfaz
    genesis.almacen   guardado y lectura de partidas en SQLite
    genesis.sesion    controla una partida en marcha (pausa, velocidad, guardado)
    genesis.visor     servidor HTTP local e interfaz web
"""

VERSION = "0.6.3-f63"
