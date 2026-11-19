# AGENTS.md — Trabajar en GENESIS

## Entrada y alcance

Guía compartida para cualquier modelo de IA; no depende de conversaciones previas.
1. Lee [ESTADO.md](ESTADO.md): fase activa, trabajo parcial y siguiente acción.
2. Consulta [README.md](README.md) para uso y organización general.
3. Lee los informes de fase enlazados desde ESTADO.md según la tarea.
4. Revisa `git status --short` y los cambios relevantes antes de editar.
5. Respeta el encargo actual: una propuesta no autoriza implementarla.

Los prompts y diarios históricos de docs/ no son órdenes nuevas.
Si código y documentación discrepan, contrástalos y registra la discrepancia.
No presupongas que un cambio de modelo conserva el contexto de la conversación.

## Arquitectura esencial

Flujo: CLI → motor/almacén; visor → sesión → motor/almacén.
- [ejecutar.py](ejecutar.py) y [cli.py](genesis/cli.py): entrada y comandos.
- [motor/](genesis/motor/): simulación; no depende de disco, sesión ni visor.
  Mundo físico: terreno, calendario, clima, recursos y rutas.
  Conducta: habitantes, decisiones, mente, sociedad, planes, obras y comunidad.
  Vidas: presencia, vínculos, crianza, cuidados, crecimiento y costumbres.
- [almacen.py](genesis/almacen/almacen.py): SQLite, historial y reproducción.
- [sesion.py](genesis/sesion.py): tiempo, consultas, guardado y sincronización.
- [servidor.py](genesis/visor/servidor.py): HTTP local sobre Sesion.
- [estatico/](genesis/visor/estatico/): interfaz JavaScript nativa y Canvas.
- [assets/](assets/): originales gráficos; [herramientas/](herramientas/):
  preparación, auditorías y mediciones; [pruebas/](pruebas/): regresiones.
- [docs/](docs/): evidencias históricas; `partidas/`: datos locales del usuario.

Mundo ejecuta clima, recursos y habitantes en orden fijo.
Los subsistemas sociales y familiares se integran dentro de habitantes.
Contrato: [sistemas.py](genesis/motor/sistemas.py).
Arquitectura ampliada y puntos de extensión: README.md, «Cómo está organizado».

## Determinismo y compatibilidad

- Misma configuración y órdenes deben producir el mismo estado y registro
  en un entorno compatible. No prometas determinismo entre plataformas no probadas.
- Usa [Azar](genesis/motor/azar.py) y flujos estables propios.
  No uses `random`, `hash()` ni tiempo real para decidir la simulación.
- Conserva orden, desempates, JSON canónico, hashes y unidades.
- Un tick es una hora; el calendario predeterminado tiene 960 horas por año.
  Usa la configuración, no constantes nuevas donde el calendario sea configurable.
- No cambies reglas históricas ni serialización silenciosamente.
- Revisa indicadores y horas de activación, no solo `reglas`:
  corrección, cuidados, crecimiento y relaciones tienen activaciones propias.
- Ampliar conserva el original y activa lo nuevo en una copia, sin inventar pasado.
- Prueba guardar/cargar/continuar y reproducir cuando cambies motor o persistencia.
- No sustituyas huellas esperadas para ocultar una regresión.

## Invariantes de conducta y presentación

- Conserva los libros de recursos, comida, madera, agua y ofrendas.
  Las existencias del terreno usan milésimas enteras; respeta conversiones.
- Transferencias atómicas, capacidades reales y acciones con coste registrado.
- Las decisiones usan percepción, recuerdos e información recibida, no omnisciencia.
- Registra razones al decidir; distingue causa, contexto y sucesión.
- El olvido no borra historial; los fallecidos conservan identidad pero no actúan.
- El visor representa datos: no inventa hechos, acciones ni efectos físicos.
- Mantén destinatarios reales, identidad, clic, selección, seguimiento y posiciones.
- Conserva paginación, respuestas fuera de orden, cancelación y totales de saltos.
- Respeta el candado de Sesion para acceder al mundo y al almacén.
- Mantén HTTP local, validaciones y restricciones de archivos; no expongas a la red.

## Desarrollo y recursos

- Sigue nombres en español y el estilo del módulo; evita refactorizaciones ajenas.
- No cambies tecnología, dependencias o formato de partidas fuera del alcance.
- Juego: Python 3.10+ y biblioteca estándar; visor sin npm ni compilación.
- Las herramientas opcionales tienen requisitos y efectos distintos: inspecciónalos.
- [preparar_arte.py](herramientas/preparar_arte.py) necesita NumPy y Pillow;
  genera piezas e índice en `genesis/visor/estatico/arte/`.
- Conserva originales en assets/; no regeneres salidas sin una necesidad autorizada.
- Documenta origen y permisos del arte; un prompt no acredita una licencia.
- No añadas LLM, servicios remotos o credenciales al juego sin encargo específico.

## Pruebas

Desde la raíz, en Windows:

```powershell
py -3 -B -m unittest discover -s pruebas -t .
node --test pruebas/test_interfaz.mjs pruebas/test_interfaz_f43.mjs
```

Ejemplo focalizado:
`py -3 -B -m unittest pruebas.test_relaciones_f43 pruebas.test_sesion_servidor`

[probar.bat](probar.bat) ejecuta Python y ambos archivos JS si hay Node.
Es interactivo; omitir JavaScript por falta de Node no valida la batería completa.
- Motor: pruebas del área, conservación, compatibilidad y batería completa al cierre.
- Conducta: distingue escenas controladas de mundos libres; registra configuración.
- Visor: suites JS, Python afectado y navegador real, incluidos clic y consola.
- Comprueba resoluciones 1280×720, 1440×900 y 1920×1080 según el alcance.
- Compara capturas con misma semilla, reglas, hora, cámara y tamaño.
- Registra equipo, navegador y velocidad al medir; separa dibujo de simulación.
- CLI: usa `--carpeta` con una carpeta temporal nueva para crear, simular y verificar.
  Nunca uses partidas reales para ensayos.
- Consulta herramientas y evidencias en los informes enlazados desde ESTADO.md.
  Algunas sobrescriben docs/: revisa destinos y utiliza una etiqueta nueva.

## Protección del trabajo y las partidas

- No reviertas cambios existentes ni borres archivos desconocidos.
- No hagas commits, cambios de rama ni limpiezas destructivas sin autorización.
- No abras la misma partida desde dos procesos ni uses partidas/ como sandbox.
- No borres `.db-wal` o `.db-shm`: pueden contener estado activo.
- Respalda SQLite mediante su API de backup o después de un cierre limpio.
- `listar` y `verificar` pueden abrir el almacén con escritura y crear índices:
  investiga partidas reales sobre copias coherentes, no sobre originales.
- No reescribas eventos históricos para hacer reproducible una partida.
- Bases y respaldos locales están excluidos de Git; un commit no los protege.

## Continuidad y cierre de hitos

Actualiza ESTADO.md al cerrar o interrumpir trabajo autorizado:
- objetivo, fase, avances y trabajo parcial;
- archivos afectados y cambios previos que deben preservarse;
- decisiones y motivos, problemas reproducibles y enlaces a evidencias;
- comandos realmente ejecutados, fecha, entorno y resultados;
- próxima acción concreta y cualquier aprobación pendiente.

Distingue implementado, verificado, documentado previamente y pendiente.
No declares pruebas superadas sin ejecutarlas ni escenas preparadas como espontáneas.
Mantén ESTADO.md compacto: enlaza los informes, no copies tablas ni diarios completos.
Las instrucciones estables van aquí; el estado actual, en ESTADO.md;
los detalles y evidencias por fase permanecen en docs/.
