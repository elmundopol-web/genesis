# GENESIS F1 — Estado de entrega

Documento histórico de F1. La entrega actual está en [F2-ESTADO.md](F2-ESTADO.md).

Versión: 0.1.0-f1. Cierre funcional del 11/11/2026.

## Cambios realizados

- Resúmenes de saltos calculados sobre el intervalo completo con agregación SQLite; todas las muertes incluidas. Los destacados quedan acotados al intervalo, incluso después de reanudar la simulación.
- Selección de otro habitante durante el seguimiento actualiza persona, cámara, etiqueta y botones. Elegir a un fallecido detiene el seguimiento.
- Ficha con páginas de 200 acontecimientos y «Ver anteriores», incluidos sucesos pendientes de guardado. Las respuestas antiguas no se mezclan al cambiar de individuo.
- La crónica reinicia su ventana cuando llega una página nueva llena después de un salto, para poder recorrer el intervalo omitido con «Ver anteriores».
- El visor reutiliza una escena con margen y transforma su posición durante el movimiento de cámara; no cambia el motor, las posiciones ni los recursos.
- Ajuste del espacio de paneles a 1440 px, mensajes de salto y documentación, versión F1 y captura actualizada.
- probar.bat ejecuta Python y, si Node está disponible, las regresiones JavaScript.

## Validación

- 192 pruebas Python pasan, 0 fallos/errores, 161,217 s. Incluyen 20 años con más de 500 sucesos y todas las muertes, paginación, API, F0, persistencia y supervivencia.
- 3 pruebas JavaScript pasan: seguimiento, páginas/cambio de persona y alineación geométrica de la escena reutilizada.
- La suite conserva el criterio de supervivencia en las 20 semillas. El cálculo detallado de la auditoría anterior dio 19/20 semillas con al menos 23 supervivientes.
- Comprobados en navegador: cambio de seguido, muerte natural de Lida durante un año, cancelación con el botón, zoom, arrastre que detiene seguimiento, vista limpia, varias velocidades y una historia natural de 213 sucesos en un mundo de prueba con clima más exigente.
- Resoluciones solicitadas 1280×720, 1440×900 y 1920×1080, en un marco de prueba que verifica el tamaño interno real. Medidas: 1280×719, 1440×900 y 1919×1080 por redondeo del navegador. Ficha y muelle no se solapan.
- Año normal, semilla 4: 0,58 s en CLI; reproducción exacta de 960 horas y 2544 eventos en 0,82 s.
- Muestras de dibujo a 1440×900 con seguimiento: alrededor de 51 redibujados/s a 6 horas/s y 36 a 24 horas/s tras reutilizar la escena. Son muestras de este equipo; el clima, la zona visible y el avance de cámara afectan al coste. Persisten picos de latencia al acelerar. No es un ensayo controlado de rendimiento entre versiones.

## Conservación

El motor de habitantes, decisiones, rutas, clima y recursos no se ha modificado. No se ha cambiado el formato de las partidas ni el equilibrio de supervivencia. Pruebas y comprobaciones usaron mundos temporales fuera de partidas/. Se hizo un respaldo antes de editar.

## Límites reales

F1 usa reglas y recuerdos sencillos de lugares. No hay memoria episódica, aprendizaje social, reproducción ni deliberación con LLM. Los habitantes fallecidos no se reemplazan. No se ha validado móvil ni determinismo entre otros sistemas operativos/versiones de Python. La fluidez acelerada tiene margen de mejora; no se promete una tasa fija de FPS.

## Siguiente trabajo

El encargo preparado está en F2-PROMPT.md: memoria causal limitada, creencias locales, aprendizaje, planes interrumpibles, ayuda/negativa a ayudar e información compartida con relaciones dirigidas. F2 está preparada como prompt, todavía no implementada.

