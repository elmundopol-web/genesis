# GENESIS — Siguiente versión: memoria, aprendizaje y sociedad inicial

Trabaja directamente sobre C:\Users\elmun\Desktop\Juego\genesis. Lee primero README.md y docs/F1-ESTADO.md, inspecciona el código y ejecuta las comprobaciones de partida. Conserva cualquier trabajo posterior que encuentres.

Quiero una evolución ambiciosa y sólida de GENESIS. Mi prioridad es observar individuos con experiencias propias, decisiones que cambian con lo vivido y relaciones que producen consecuencias reales. Aspira a la máxima calidad práctica: profundidad de comportamiento, claridad visual y coherencia del mundo.

## Base que debes conservar

F1 dispone de 25 habitantes, supervivencia, inventarios limitados, percepción local, rutas, envejecimiento, muertes permanentes, historia causal, SQLite, reproducción determinista, seguimiento y saltos temporales. Se han corregido los resúmenes extensos, el seguimiento y la paginación del historial; el visor reutiliza el dibujo del terreno al mover la cámara.

La base validada tiene 192 pruebas Python y 3 pruebas JavaScript. Comprueba estos números contra el estado actual. El año del modelo dura 40 días / 960 horas.

Conserva la dirección artística: mundo protagonista, personajes visibles y paneles flotantes. La información nueva debe ayudar a comprender vidas y acontecimientos.

## Objetivo observable de esta entrega

Quiero poder seguir a alguien y entender qué recuerda, qué cree, qué está intentando conseguir y cómo sus experiencias con otros influyen en su próxima decisión. Deben aparecer diferencias de comportamiento demostrables, ayuda o negativa a ayudar, reciprocidad y competencia por recursos limitados.

Implementa el sistema completo descrito a continuación. Organiza el trabajo en hitos comprobables y continúa después de cada uno hasta cerrar la entrega.

## Prioridad de calidad: vidas que apetezca seguir

El criterio de éxito incluye que el jugador pueda reconocer una experiencia, observar cómo cambia una decisión y descubrir una consecuencia posterior. La información de las fichas debe corresponder a diferencias visibles de conducta.

Empieza por un primer hito completo de extremo a extremo: experiencia real → recuerdo → cambio de creencia o relación → siguiente decisión distinta → consecuencia visible y consultable. Compruébalo con los actores necesarios y después intégralo en los 25 habitantes antes de ampliar el resto. Conserva este recorrido funcionando durante toda la entrega.

La entrega final mantiene todo el alcance de este prompt. Prioriza resolver cada recorrido completo frente a desarrollar todos los sistemas por separado y conectarlos únicamente al final.

## 1. Memoria episódica que influye en decisiones

Añade recuerdos personales de experiencias reales: hallar o agotar alimento, sufrir sed o frío, fracasar en un viaje y recibir o prestar ayuda.

Cada recuerdo debe incluir sujeto, momento, lugar, participantes, significado e identificadores de los acontecimientos que lo originaron. Distingue observación propia de información recibida de otro individuo.

Implementa importancia, recuperación de recuerdos pertinentes, consolidación y olvido determinista. Limita el estado activo por persona y mide su coste. El registro histórico de SQLite permanece íntegro aunque un habitante olvide algo.

La memoria debe modificar decisiones: preferir una fuente que resultó útil, desconfiar de información desactualizada, recordar una deuda de ayuda o evitar un lugar donde sufrió un peligro cuando exista una alternativa razonable.

## 2. Creencias locales y aprendizaje

Representa lo que cada individuo cree sobre lugares y personas, con antigüedad, fuente y confianza. Una creencia puede estar equivocada o haber quedado obsoleta.

Actualízala mediante observación y experiencias posteriores. Un habitante no conoce recursos, episodios o relaciones que no ha observado ni recibido por una interacción válida.

Diseña escenarios reproducibles que demuestren aprendizaje y corrección de errores. Compara decisiones antes y después de la experiencia manteniendo controladas las demás variables.

## 3. Objetivos y planes cortos ejecutables

Amplía la política de decisiones para elegir objetivos como mantener reservas, alcanzar agua, buscar refugio o ayudar a alguien conocido.

Los planes deben contener acciones válidas del motor, comprobar sus precondiciones y adaptarse si cambian el clima, las existencias o las necesidades. Las urgencias de supervivencia interrumpen los planes y las interacciones sociales.

Muestra el objetivo actual y una explicación breve apoyada en necesidades, recuerdos o creencias identificables. No inventes motivos retrospectivamente para justificar una decisión.

Mantén una interfaz de política sustituible para futuras fases.

Da continuidad a las actividades: los planes deben ayudar a terminar lo que alguien está intentando hacer y reconsiderarse por motivos identificables. Comprueba que no oscilan continuamente entre objetivos equivalentes. Los rasgos y las experiencias deben producir diferencias coherentes entre individuos, respetando sus posibilidades y necesidades reales.

## 4. Primeras interacciones y relaciones con consecuencias

Implementa un catálogo pequeño pero profundo de interacciones: pedir comida, ofrecer o compartir comida, aceptar o rechazar y comunicar un lugar conocido con alimento o agua.

Exige proximidad y un coste temporal razonable. Define resolución determinista cuando coincidan varias solicitudes. Las transferencias deben ser atómicas: salen del inventario de quien entrega y llegan al de quien recibe, respetando capacidad y conservación.

Construye relaciones dirigidas a partir de hechos observados: A puede confiar en B sin que B confíe igual en A. Registra ayuda, rechazos y fiabilidad de la información. La reputación no se transmite globalmente.

Haz que sociabilidad, prudencia, curiosidad y audacia tengan efectos explícitos y comprobables, sin convertir un rasgo en una conducta obligatoria e invariable.

Permite que surjan reciprocidad, cooperación y competencia por recursos existentes. No fuerces amistades ni conflictos mediante guiones, grupos asignados o acontecimientos ficticios. No garantices de antemano resultados sociales emergentes.

Comprueba que las transferencias tienen un propósito: evita ciclos de regalarse la misma comida para aumentar artificialmente la confianza. El juicio sobre una negativa debe considerar el contexto que el individuo puede observar y conservar incertidumbre cuando desconoce las razones del otro. Una necesidad propia urgente debe poder justificar priorizar la supervivencia.

## 5. Experiencia de observación

Amplía la ficha con «Recuerdos relevantes», «Lo que cree», «Objetivo actual» y «Personas que conoce». Debe ser posible pasar de una decisión a su experiencia de origen y al individuo implicado.

Distingue claramente el estado real del mundo de lo que cree un habitante. Presenta desconocimiento e incertidumbre sin exponer información oculta como si fuera conocimiento del personaje.

Representa las interacciones con indicadores discretos sobre el mapa. Mantén selección, seguimiento, vista limpia, crónica, velocidad, progreso y cancelación. Los resúmenes temporales deben recoger las nuevas consecuencias sin truncar los totales.

Ayuda a descubrir acontecimientos relevantes sin saturar el mapa de avisos. Da prioridad a experiencias nuevas y consecuencias importantes; agrupa las repeticiones rutinarias y permite consultar su detalle cuando sea necesario. Comprueba que el jugador puede pasar de un acontecimiento a sus participantes y a sus consecuencias con pocas interacciones.

Utiliza textos descriptivos derivados del estado y de acontecimientos reales. La simulación de esta entrega debe funcionar de forma autónoma y reproducible con algoritmos convencionales; reserva la deliberación mediante LLM para una integración posterior medible.

## 6. Persistencia y compatibilidad

Guarda recuerdos activos, creencias, relaciones, objetivos y planes de forma determinista. Guardar, cargar y continuar debe equivaler a ejecutar sin interrupción.

Versiona las reglas y el estado. Una partida F1 debe conservar su reproducción con las reglas con las que fue creada. No cambies su historia silenciosamente. Si activas sistemas nuevos en una copia compatible, registra su activación desde ese momento; nunca inventes un pasado social.

Analiza primero la compatibilidad. Haz copia de seguridad antes de migrar y conserva las partidas originales. F0 debe seguir pudiendo abrirse sin habitantes.

## 7. Pruebas y rendimiento

Mantén las pruebas existentes y añade comprobaciones de comportamiento, no solo de estructuras de datos:

- Dos personas con experiencias distintas pueden elegir de forma distinta ante condiciones equivalentes.
- Observar una fuente agotada corrige una creencia previa.
- La información de otro individuo conserva su procedencia y puede verificarse después.
- Una transferencia conserva exactamente el recurso, incluso con solicitudes simultáneas o inventarios casi llenos.
- La ayuda o su rechazo modifica una relación y puede influir en una decisión posterior.
- Una urgencia interrumpe un plan social sin corromperlo.
- Los fallecidos no interactúan ni siguen tomando decisiones.
- El olvido limita la memoria activa sin borrar la historia verificable.
- Las historias largas, los saltos, el seguimiento y la cancelación siguen funcionando.
- Semilla, configuración y acciones iguales producen el mismo estado y registro, también tras guardar y cargar.

Conserva el criterio de supervivencia de F1: al menos 23 de 25 vivos al año en como mínimo 18 de 20 semillas abundantes. Comprueba además escenarios de escasez. No rebajes umbrales ni manipules recursos para ocultar fallos.

Mide tiempo de simulación, memoria, tamaño de partidas, latencia de consultas y fluidez real del visor. Compara con F1 en condiciones equivalentes. El crecimiento de la historia no debe obligar a recorrerla entera en cada decisión. Comprueba las resoluciones de escritorio y obtén capturas reales.

Realiza además una revisión jugable de observación. Sigue a varios individuos durante secuencias completas, con abundancia y escasez, y examina si sus decisiones se comprenden, si hay diferencias personales observables y si las interacciones producen consecuencias que perduran. Si apenas suceden interacciones o la conducta resulta repetitiva, identifica la causa y mejora las oportunidades y reglas antes de dar la entrega por cerrada. Conserva la contabilidad, las necesidades y los límites de información.

Incluye en la entrega ejemplos de cadenas causales obtenidas de ejecuciones reales, con semilla, configuración, periodo e identificadores de acontecimientos. Distingue las pruebas controladas de los mundos que evolucionaron libremente. No presentes un escenario preparado como emergencia espontánea ni inventes historias para completar esta revisión.

## 8. Continuidad del trabajo y entrega

Mantén docs/ESTADO_DESARROLLO.md actualizado después de cada hito: cambios terminados, pruebas ejecutadas, problemas abiertos, archivos afectados y siguiente paso concreto. Así se podrá continuar si la sesión pierde contexto o se agotan los tokens.

No te detengas en un plan ni declares completo un sistema solo porque sus clases existen. Implementa, ejecuta, observa y corrige hasta satisfacer los criterios.

Al cerrar, entrega qué funciona, pruebas y capturas, medidas comparables, límites reales, instrucciones de uso y punto de continuación si queda algo sin verificar.

La visión futura incluye generaciones, asentamientos, cultura y civilizaciones. Esta entrega debe aportar una base profunda y observable para llegar a ellas: individuos que aprenden de su vida y empiezan a transformar la de otros.

