# GENESIS AUTODEV v0.1 · Piloto local

Un agente experimental de programación que usa **Ollama en tu PC**, sin API ni
suscripción. Diseñado para tareas **pequeñas y comprobables** sobre GENESIS.
No tiene la capacidad de Claude Code: un modelo local 7B puede equivocarse,
ignorar herramientas o no resolver una tarea.

## Antes de empezar (Windows 10/11)

1. Instala [Git para Windows](https://git-scm.com/downloads/win), si no lo tienes.
2. Instala [Ollama](https://ollama.com/download/windows) y descarga un modelo:

   ```powershell
   ollama pull qwen2.5-coder:7b
   ```

   Comando usado **solo una vez** para descargarlo. También puedes probar
   `qwen2.5-coder:14b`, más exigente con tus 12 GB de VRAM.
3. Usa una **copia Git actualizada** de GENESIS. Si la carpeta actual no es un
   clon Git, puedes clonar el repositorio con GitHub Desktop. No basta con un
   ZIP sin metadatos de Git.
4. Haz doble clic en **`iniciar-autodev.bat`**. Se abre la interfaz gráfica.
   Si no aparece, ejecuta `py -3 -m autodev.ui` en la carpeta del proyecto para
   ver el error. No necesitas dejar ninguna consola abierta durante el uso normal.
5. Pulsa **Comprobar Ollama**, escribe una tarea pequeña y pulsa **Iniciar**.

## Qué hace de verdad

- Crea una **rama Git y un worktree** nuevos, en una carpeta hermana llamada
  `<repositorio>-autodev/<id>`. Nunca edita directamente `main` ni la carpeta
  original de GENESIS.
- Expone al modelo herramientas para listar, leer, buscar, sustituir fragmentos,
  crear archivos y ejecutar pruebas. **No ofrece una terminal arbitraria**.
- Ollama elige **una acción estructurada por turno**. `edit_file` separa esa
  decisión de la generación del código: el mismo modelo local recibe el archivo
  y las referencias leídas, y devuelve el código sin tener que incluirlo en un
  JSON largo. Se conserva la compatibilidad con historiales de llamadas JSON.
- Debe leer antes de editar. Las reescrituras se limitan a archivos pequeños
  leídos completos; se rechazan si cambiaron desde la lectura. Python con
  sintaxis incorrecta no se guarda.
- Comprueba primero los módulos de pruebas nuevos o modificados para devolver
  rápidamente sus errores. Después ejecuta todas las pruebas Python (y JavaScript si hay Node.js) antes de dar por
  válido el resultado y hacer commit en esa rama local.
- Guarda `state.json` y el historial en
  `<repositorio>-autodev-sessions/<id>/state.json`. Usa **Reanudar sesión** para
  continuar después de cerrar la aplicación, de alcanzar un límite o de un fallo.
- **Detener** se aplica cuando responda Ollama; una petición del modelo puede
  tardar varios minutos.

## Límites y precauciones

- **Es un prototipo, no una aplicación con aislamiento de seguridad**. Las
  pruebas ejecutan código del worktree con los permisos de tu usuario. No
  cargues tareas de desconocidos ni repositorios de origen dudoso.
- Las pruebas y el código pueden fallar; ningún resultado se integra en `main`
  automáticamente. Revisa los cambios y sus pruebas antes de integrarlos.
- El modelo tiene 8192 tokens de contexto configurados por defecto; el agente
  limita el historial por tamaño, conserva el encargo y la revisión más reciente,
  y agrupa cada llamada con su resultado. Esto limita su capacidad para cambios enormes.
- Solo puede modificar archivos de código de texto (Python, JS, HTML, CSS, JSON,
  Markdown). No puede editar secretos, partidas, archivos ocultos ni `autodev/`.
- Para evitar bucles, se detiene tras un máximo de 120 turnos, 4 acciones
  idénticas seguidas, 3 errores en la misma acción aunque alterne otras herramientas,
  o el tiempo configurado (de 5 a 480 minutos).
- En Windows sin privilegio para crear symlinks, esa prueba específica se omite.
  Otra prueba crea una junction real sin elevar permisos y comprueba el bloqueo
  de rutas que salen del proyecto.
- No realiza auditorías de simulación largas ni toma decisiones de diseño por
  sí solo. Úsalo primero para errores menores o funciones bien delimitadas.
- Si Node.js no está instalado, las pruebas de interfaz no se ejecutarán; eso
  debe constar al revisar una rama con cambios JavaScript.
- Sin internet, el modelo ya descargado puede seguir funcionando mediante
  Ollama; no hay cuotas de mensajes, pero sí límites de hardware y consumo.

## Cómo comprobar una tarea

Elige una modificación con un criterio objetivo, por ejemplo:

> Añade una prueba de regresión para [comportamiento concreto]. No cambies
> las reglas F4.4. Ejecuta las pruebas y documenta el resultado.

La primera meta es **conseguir una tarea correcta de principio a fin**.
Solo después conviene aumentar su autonomía o dejarlo trabajar sin supervisión.
