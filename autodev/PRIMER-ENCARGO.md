# GENESIS AUTODEV · Primer encargo completado

Estado: completado y comprobado, con Ollama real y el modelo local `qwen2.5-coder:7b`.

## Encargo

Añadir a Calendario una propiedad `ticks_por_semana` que devuelva siete veces
`ticks_por_dia`, conservando el comportamiento existente, y crear dos pruebas
para el calendario normal (168) y un día de 10 horas (70).

## Resultado

- El agente leyó el calendario, realizó la edición, creó dos pruebas y las ejecutó.
- El agente utilizó 7 pasos. No se editó a mano el código que generó.
- Se reanudó tras un error del registro de la consola de prueba en Windows (Unicode); se repitió la validación para comprobar también el cierre y el commit.
- Duración de esa ejecución: 994 segundos, incluyendo la validación completa.
- Python: 370 pruebas ejecutadas en 518.663 segundos, sin fallos; una omitida por permisos de symlinks en Windows.
- JavaScript: la batería de 23 pruebas pasó en la validación final.
- La revisión independiente probó días de 1, 8, 10, 24 y 36 horas.
- Se comprobó que el código anterior conserva su estructura al excluir la propiedad añadida.
- Las pruebas nuevas detectaron un resultado fijo incorrecto y un multiplicador erróneo, mediante cambios solo en memoria.

## Qué se ha cambiado en AUTODEV

La rama `feature/genesis-autodev-v01` conserva el agente original y añade:
compatibilidad de pruebas con Windows, lectura obligatoria antes de editar,
acciones estructuradas, generación de código separada de esas acciones,
rechazo de Python con sintaxis incorrecta, validación rápida de pruebas nuevas,
conservación del encargo al compactar el historial y freno de errores repetidos.

## Dónde está el resultado

Rama de ejemplo: `autodev/20261115-235305-85ff9b`.

Commit del encargo: `8db79f0a23eebf185bfc3eb13e41cc3ef2133f23`.

Código del agente evaluado: `e418863`.

Solo se modificaron `genesis/motor/calendario.py` y
`pruebas/test_autodev_calendario.py` en esa rama de ejemplo.
La modificación del calendario no se integró en `main` ni en la rama de desarrollo de AUTODEV.
El parche completo está en `primer-encargo.patch`.

## Límites observados

Este resultado demuestra una tarea pequeña. No demuestra autonomía durante horas
ni capacidad para desarrollar una fase completa de Génesis.
Los ensayos previos de pruebas del azar no cumplieron todos los requisitos y no
se aceptaron como entregas. La elección de formato, herramientas y tamaño del
encargo influyó mucho en el resultado. Las tareas siguientes siguen requiriendo revisión.

## Informe del propio agente

Se ha añadido la propiedad ticks_por_semana a la clase Calendario y se han creado pruebas para comprobar su funcionamiento. Las pruebas han pasado exitosamente.
