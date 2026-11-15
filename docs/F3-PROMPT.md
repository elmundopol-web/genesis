# GENESIS F3 — Encargo (texto del usuario, recuperado de la sesión)

Continúa GENESIS en:
`C:\Users\elmun\Desktop\Juego\genesis`
Implementa F3: las primeras comunidades, sobre la F2.5 actual, incluida su segunda pasada artística.
Quiero pasar de individuos que sobreviven y se ayudan ocasionalmente a personas capaces de mantener lugares, reservas y proyectos compartidos. La experiencia central sigue siendo observar el mundo, seguir vidas y descubrir por qué ocurrieron las cosas.
Trabaja sobre el proyecto existente y completa la implementación. No te detengas en un documento de diseño, estructuras de datos o edificios decorativos.
1. Punto de partida y dirección
F2 dispone de memoria, creencias, objetivos, planes, relaciones dirigidas e interacciones. F2.5 ha mejorado el mundo, los personajes, la interfaz y la fluidez.
La última entrega registra 259 pruebas Python y 9 JavaScript correctas. El año del modelo dura 40 días / 960 horas.
Lee `docs/F2.5-ESTADO.md` y examina las partes necesarias del motor, persistencia, sesión y visor. Haz un respaldo antes de modificar. No reabras una auditoría general de las fases anteriores: realiza la lectura y las comprobaciones focalizadas necesarias para desarrollar F3 con seguridad.
Conserva la dirección artística y las mejoras de rendimiento de la segunda pasada. La referencia está en `docs/F2.5-REFERENCIA.png` y las últimas capturas en `docs/f25/pasada2/`.
Mi visión futura incluye habitantes que interpretan experiencias, comparten explicaciones y desarrollan tradiciones, culturas e incluso religiones. F3 debe preparar ese camino con cooperación y aprendizaje colectivo que ya tengan consecuencias reales.
2. Objetivo observable
Quiero poder seguir esta secuencia dentro del juego:
Una necesidad lleva a proponer un proyecto → varias personas contribuyen → construyen algo útil → lo utilizan → recuerdan la experiencia → su cooperación posterior cambia.
Después quiero seleccionar ese lugar y descubrir:

* Quién lo inició y por qué.
* Quién contribuyó y qué aportó.
* Quién lo utiliza.
* Qué recursos mantiene.
* Qué personas forman una comunidad alrededor.
* Qué acuerdos siguen y qué tensiones han aparecido.
* Qué experiencias explican su situación actual.

La comunidad debe existir en las acciones y relaciones de sus integrantes, además de tener un nombre en la interfaz.
3. Primer hito completo: construir y utilizar un refugio
Empieza con un recorrido de extremo a extremo:

1. Una persona detecta una necesidad de protección y elige un emplazamiento válido.
2. Inicia un proyecto de refugio.
3. Otra persona conoce el proyecto y decide colaborar.
4. Obtienen madera real, la transportan y trabajan durante horas simuladas.
5. El refugio alcanza su estado utilizable.
6. Alguien lo utiliza y obtiene una mejora real y medible.
7. La contribución y el beneficio dejan recuerdos, relaciones y acontecimientos consultables.

Comprueba primero el recorrido con una escena controlada, incluida una comparación con y sin refugio bajo las mismas condiciones. Después intégralo en los 25 habitantes y observa mundos que evolucionen libremente.
Continúa desde ese hito hasta completar F3. No necesitas pedir aprobación después de cada hito para seguir dentro de este alcance.
4. Refugios con existencia física y utilidad
Implementa un catálogo pequeño y profundo. Basta inicialmente con un refugio y un depósito, separados o asociados a un mismo lugar.
Cada construcción necesita:

* Identificador persistente y posición válida.
* Estado de obra y de conservación.
* Materiales requeridos, entregados e incorporados.
* Trabajo realizado y trabajo pendiente.
* Capacidad de uso o almacenamiento.
* Historia de contribuciones, uso, mantenimiento y abandono.

El emplazamiento debe considerar información disponible para quien decide: terreno, acceso al agua, alimento conocido, distancias, exposición y experiencia previa.
Construir exige materiales y trabajo. La obra progresa por acciones válidas del motor, con proximidad y coste temporal. Una construcción inacabada solo ofrece los beneficios que hayas definido explícitamente para ese estado.
El refugio debe influir realmente en protección o descanso. Define capacidad, condiciones de acceso y resolución determinista cuando no quepan todos. Su utilidad no debe convertirse en inmunidad universal.
Añade mantenimiento y deterioro sencillos, con costes y efectos visibles. Una obra puede quedar suspendida, terminarse después o abandonarse; una estructura deteriorada puede perder utilidad.
Los costes son parámetros de juego configurables. Busca oportunidades razonables de construcción sin regalar materiales, eliminar necesidades ni hacer invulnerables a sus usuarios.
5. Materiales, transporte y conservación
La madera ya existe en el mundo, pero el inventario y varias comprobaciones actuales están centrados en alimentos. Amplíalos expresamente:

* Distingue recursos comestibles de materiales.
* La madera ocupa capacidad de transporte y no se puede comer.
* Recoger madera reduce las existencias reales de la celda.
* Transportar exige desplazamiento y tiempo.
* Depositar cambia de ubicación recursos existentes.
* Construir y reparar incorporan o consumen materiales de forma registrada.

No utilices la lista de alimentos como catálogo universal del inventario.
Mantén una contabilidad explícita: lo extraído debe encontrarse en inventarios, depósitos, materiales de obra, estructuras o consumos y pérdidas registradas. Evita contabilizar dos veces materiales reservados e incorporados.
Define qué ocurre con recursos de obras canceladas, almacenes abandonados y personas fallecidas. Nada debe desaparecer por borrar una entidad ni reaparecer por volver a iniciar un proyecto.
Prueba cantidades exactas, inventarios casi llenos, entregas simultáneas y recursos que se agotan durante una acción.
6. Reservas compartidas
Implementa depósitos con capacidad limitada y existencias por recurso.
Los habitantes deben poder:

* Llevar excedentes y depositarlos.
* Retirar cantidades que puedan transportar.
* Utilizar reservas para necesidades reales.
* Contribuir a materiales de construcción y mantenimiento.
* Revisar sus decisiones si el depósito se vacía o deja de resultar útil.

Las operaciones deben ser atómicas y deterministas. Dos personas no pueden retirar la misma última unidad.
El conocimiento de las reservas debe proceder de observar el depósito o recibir información válida. Una persona lejana no conoce instantáneamente sus existencias actuales.
Evita bucles de depositar y retirar la propia comida para obtener gratitud o simular cooperación. La decisión debe considerar necesidades, reservas personales, distancia, confianza y utilidad.
Si introduces deterioro de alimentos, define y registra sus pérdidas. No cambies silenciosamente el comportamiento de las partidas anteriores.
7. Proyectos compartidos y continuidad del trabajo
Añade proyectos de construcción, reparación y abastecimiento que varias personas puedan conocer y realizar.
Cada participante necesita saber qué pretende hacer y por qué. Puede comprometerse a reunir materiales, transportarlos o trabajar, según sus posibilidades.
Resuelve:

* Dos personas que intentan cubrir la misma necesidad de materiales.
* Materiales que dejan de estar disponibles.
* Participantes que se marchan, enferman o mueren.
* Obras que quedan sin trabajadores.
* Urgencias que interrumpen una contribución.
* Reanudación del trabajo cuando vuelve a ser posible.

Usa reservas de tareas o materiales cuando sean necesarias para evitar duplicaciones. Deben liberarse correctamente; no pueden dejar proyectos bloqueados para siempre.
Las urgencias personales siguen teniendo prioridad. Un habitante no debe morir de sed por cumplir una tarea de construcción.
Busca continuidad: completar un traslado o una parte útil del trabajo, reconsiderando por motivos concretos. Evita oscilaciones constantes entre transportar, recoger y abandonar.
Los papeles deben ser flexibles y surgir de actividad, capacidad y elección. No asignes profesiones permanentes ni grupos predeterminados.
8. Comunidades con pertenencia y consecuencias
Implementa agrupaciones persistentes alrededor del uso y mantenimiento de lugares compartidos.
La proximidad puede crear oportunidades, pero no basta por sí sola para convertir automáticamente a todos los vecinos en una comunidad.
La formación y continuidad deben apoyarse en experiencias como:

* Colaborar repetidamente.
* Utilizar el mismo refugio.
* Mantener una reserva común.
* Recibir ayuda o cumplir compromisos.
* Compartir un acuerdo práctico.

Representa integrantes, lugares asociados, historia y estado del grupo. Conserva los identificadores aunque cambien sus integrantes.
Permite acercarse, incorporarse, reducir la participación y marcharse. Las decisiones deben responder a utilidad, relaciones, necesidades y experiencia.
No fuerces conflictos para mostrar actividad. Si hay colaboración, desigualdad de aportaciones, decepción o abandono, deben proceder de hechos reales.
Una comunidad puede debilitarse o disolverse. Sus edificios, recursos e historia permanecen en el mundo según su estado físico; no desaparecen con la etiqueta del grupo.
9. Primeros acuerdos y aprendizaje colectivo
Incluye una primera capa funcional de normas y conocimientos prácticos compartidos.
Acuerdos sencillos
Implementa un catálogo pequeño de acuerdos relacionados con los sistemas de esta fase. Por ejemplo:

* Mantener una reserva mínima.
* Priorizar a quien está en apuros.
* Contribuir al mantenimiento.
* Organizar el uso de un refugio con capacidad limitada.

Una persona puede proponer un acuerdo, otra conocerlo y aceptarlo o rechazarlo. Cada una debe poder actuar según sus necesidades y experiencias.
Distingue:

* Lo que alguien propone.
* Lo que los demás han conocido y aceptado.
* Lo que ocurre realmente.
* Cómo juzga cada observador lo ocurrido.

Una norma social no debe convertirse automáticamente en una barrera física universal. El desacuerdo o incumplimiento solo modifica relaciones y decisiones de quienes conocen lo sucedido.
Los compromisos incumplidos deben considerar el contexto visible: una urgencia o la muerte de un participante no equivalen a una negativa deliberada.
Haz explícito qué opciones pertenecen al catálogo diseñado y qué elecciones o consecuencias han surgido durante la simulación.
Conocimientos compartidos
Extiende la memoria y las creencias para que experiencias de esta fase puedan transmitirse. Por ejemplo:

* Un refugio resultó útil durante el frío.
* Una reserva permitió afrontar la escasez.
* Un lugar dejó de ser conveniente.
* Una colaboración cumplió o defraudó lo esperado.

La información debe conservar origen, antigüedad, confianza y acontecimientos de apoyo. Puede estar desactualizada o interpretarse de forma distinta.
Comprueba un recorrido real:
Experiencia de A → información recibida por B → creencia de B → decisión distinta → resultado comprobable.
B no debe adquirir todos los recuerdos de A ni conocer el grupo entero por incorporarse.
Esta capa prepara la futura cultura. No añadas una religión automática al alcanzar cierta fecha, población o número de repeticiones. La aparición de interpretaciones simbólicas, doctrinas y transmisión generacional necesita una fase posterior con sus propias comprobaciones.
10. Memoria, relaciones y razones
Integra las experiencias nuevas en la mente existente:

* Contribuir a una obra y utilizarla después.
* Ayudar a mantener reservas.
* Cumplir o abandonar una tarea.
* Obtener ayuda del grupo.
* Recibir información sobre un lugar o acuerdo.
* Marcharse después de experiencias negativas.

Las relaciones siguen siendo dirigidas. Dos integrantes pueden valorar de forma diferente la misma situación.
Las razones de una decisión deben guardarse al tomarla: necesidad, experiencia, conocimiento, compromiso o relación que pesó. El visor las traduce después.
Mantén límites de memoria activa y costes acotados. El olvido no elimina la historia del mundo.
La política debe seguir siendo sustituible para futuras capas de deliberación. F3 debe funcionar autónomamente con su configuración normal; no necesita depender de llamadas a modelos de lenguaje para resolver cada hora.
11. Integración visual con F2.5
Representa los nuevos elementos con el lenguaje artístico de la segunda pasada:

* Refugios con volumen, materiales, sombras y estados de obra.
* Depósitos cuyo aspecto y ficha respondan a su estado real.
* Habitantes transportando o trabajando según acciones existentes.
* Deterioro, reparación y abandono legibles.
* Indicadores discretos de proyectos y lugares compartidos.

Conserva selección, profundidad, oclusión, precisión del clic, cámara y seguimiento. Los edificios no deben ocultar permanentemente a quienes los utilizan.
El observador no tiene que colocar edificios ni dirigir trabajadores para que F3 funcione. La simulación debe desarrollar los nuevos comportamientos de forma autónoma.
Añade fichas de construcción, proyecto y comunidad, con enlaces a participantes y acontecimientos.
Amplía las fichas individuales con pertenencia, contribuciones y compromisos. Muestra los acuerdos realmente conocidos por esa persona.
La crónica y los resúmenes temporales deben incluir obras, materiales, reservas, incorporaciones, salidas, deterioro y acontecimientos colectivos relevantes. Los totales abarcan todo el intervalo; los detalles rutinarios pueden agruparse.
12. Persistencia, reglas y compatibilidad
F2.5 es una fase visual y utiliza las reglas de F2. F3 cambia la simulación: introduce una versión de reglas explícita para las nuevas partidas.
Conserva la reproducción de F0, F1 y F2. Los sistemas y campos nuevos no deben alterar silenciosamente estados o hashes históricos.
Incluye:

* Nuevas partidas F3 desde la interfaz y la línea de comandos habituales.
* Guardado de construcciones, existencias, proyectos, participantes, comunidades, acuerdos, conocimientos y planes.
* Guardar, cargar y continuar equivalente a ejecutar sin interrupción.
* Activación de F3 en una copia de una partida compatible, conservando el original y registrando cuándo comienza.

Una copia F2 puede proceder de una ampliación anterior de F1. Conserva todas sus etapas de reglas y activaciones. No sobrescribas la activación anterior para introducir la nueva.
Al activar F3 no inventes edificios, comunidades, contribuciones ni un pasado colectivo. Los sistemas nuevos comienzan desde ese momento.
13. Pruebas de comportamiento
Mantén las regresiones existentes y añade pruebas que demuestren, como mínimo:

* Dos personas contribuyen a una misma obra y sus aportaciones suman exactamente.
* Una obra sin materiales suficientes no se completa.
* Recoger, transportar, depositar, construir y reparar conserva los recursos.
* La madera ocupa inventario y nunca se consume como alimento.
* Solicitudes simultáneas no duplican materiales ni existencias.
* Una urgencia interrumpe un trabajo y permite resolver o liberar su compromiso.
* La muerte o salida de un participante no bloquea el proyecto ni borra recursos.
* Un refugio utilizable cambia un resultado real frente a la misma escena sin refugio.
* Su capacidad limitada se respeta de forma determinista.
* Una persona usa información recibida sobre un lugar o proyecto y puede corregirla después.
* Una experiencia de cooperación o incumplimiento cambia una relación y una decisión posterior.
* Pertenecer a una comunidad no concede información global.
* Un acuerdo conocido influye en la conducta y el contexto modifica el juicio sobre su incumplimiento.
* El abandono de una comunidad conserva estructuras, existencias e historia.
* Guardado, carga, reproducción, saltos, cancelación y resúmenes incluyen los sistemas nuevos.
* Misma semilla, configuración y acciones producen el mismo estado y registro.

Conserva el criterio de supervivencia: al menos 23 de 25 vivos al año en como mínimo 18 de 20 semillas abundantes. Comprueba también escasez. No rebajes umbrales ni añadas recursos ocultos para compensar una política de construcción defectuosa.
14. Revisión de mundos libres
Además de las escenas controladas, deja evolucionar mundos desde su estado inicial normal.
Observa varias semillas abundantes y escasas durante periodos suficientes para ver construcción, uso, mantenimiento y posibles abandonos.
Una comunidad funcional, a efectos de la revisión, debe tener varios participantes recurrentes, al menos una instalación utilizable y actividad compartida que perdure. Un grupo recién creado sin acciones posteriores no basta.
Publica por semilla:

* Supervivientes.
* Obras iniciadas, terminadas y abandonadas.
* Instalaciones utilizadas y reparadas.
* Recursos almacenados y retirados.
* Comunidades formadas, tamaño y duración.
* Participantes que contribuyen y personas que reciben beneficios.
* Cambios de pertenencia y acuerdos observados.

La entrega debe mostrar comunidades funcionales en varias semillas libres, no depender de una única escena preparada. Si apenas construyen, no usan los depósitos o se dispersan enseguida, investiga las oportunidades y decisiones antes de dar la fase por cerrada.
No garantices de antemano conflictos, cooperación perfecta o resultados idénticos. Distingue siempre pruebas preparadas y aparición espontánea.
Incluye cadenas causales verificables con semilla, configuración, periodo e identificadores de acontecimientos.
15. Rendimiento y cierre
Mide simulación, tamaño de partidas, memoria, consultas y fluidez con los sistemas de F3. Compara con la base F2.5 en condiciones equivalentes.
Las decisiones no deben recorrer toda la historia ni todos los proyectos del mundo cada hora. Utiliza estado activo y consultas acotadas.
Comprueba escenas con varias construcciones y participantes, información extensa y saltos temporales. Conserva las mejoras de dibujo gradual, caché y cámara de F2.5.
Verifica el visor a 1280×720, 1440×900 y 1920×1080.
Mantén `docs/F3-ESTADO_DESARROLLO.md` actualizado por hitos: terminado, comprobaciones, archivos afectados, problemas y siguiente paso concreto.
Al cerrar entrega:

* F3 funcionando con el iniciador habitual.
* Instrucciones para nuevas partidas y copias ampliadas.
* Pruebas y medidas ejecutadas.
* Capturas reales y, si es posible, movimiento.
* Ejemplos de cooperación y aprendizaje colectivo con sus causas.
* Resultados de mundos libres, separados de pruebas controladas.
* Límites reales y estado final en `docs/F3-ESTADO.md`.

F3 estará lograda cuando podamos comprender cómo varias vidas han construido y sostenido algo juntas, y cómo esa experiencia cambia lo que harán después.
Implementa todos los recorridos necesarios y continúa hasta cerrar la entrega.
