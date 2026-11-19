# F2: experiencias y consecuencias comprobables

Estos ejemplos proceden del motor real con reglas 2, 25 habitantes, mapa
64×64 y año de 960 horas. No se han colocado personajes ni añadido recursos,
relaciones o acontecimientos para obtenerlos.

Para repetir la observación desde la carpeta del proyecto:

```bat
py -3 -X utf8 -B herramientas/revisar_f2.py 9 0.3 1
```

La herramienta sigue los objetivos mientras se ejecutan y conserva sus razones
tal como estaban al decidir. Los números siguientes son identificadores del
registro de esa ejecución: semilla 9, abundancia 0,3, primer año completo.

## Ayuda recordada que se devuelve

1. Hora 511, evento **3125**: Elai pasa un hambre grave.
2. Hora 542, evento **3267**: Zael entrega 5 de comida a Elai sin que se la
   pida. Su causa es 3125.
3. Hora 639, evento **3756**: Elai entrega 3 de comida a Zael. El motor guarda
   `corresponde=true`, `recuerda=3267` y **causa 3267**. El objetivo de Elai
   cita el recuerdo n.º 40 de la ayuda recibida.

Son 97 horas entre ambas entregas. Aquí sí existe un vínculo causal explícito,
además de la sucesión temporal. En el visor, el recuerdo abre la primera entrega;
«Qué provocó» lleva a la devolución. Los botones de participantes abren las dos vidas.

[Elai recuerda la ayuda al dar comida a Zael](https://github.com/elmundopol-web/genesis/blob/cbff73da3b4b63d451320d4e6426f4be3d3faf3c/docs/f2-trato.jpg)

## Ayuda recordada que se corresponde con información

- Hora 332, evento **2079**: Zael da comida a Odei.
- Hora 558, evento **3359**: Odei indica a Zael un lugar conocido. No responde
  a una petición: guarda el recuerdo 2079 como causa y `corresponde=true`.

La reciprocidad no exige devolver el mismo recurso. Este es otro vínculo
causal registrado por el motor, surgido en el mismo mundo libre.

## Una experiencia cambia el destino elegido

- Hora 10, evento **187**: Quila encuentra que alguien se le ha adelantado
  al alimento. Conserva el recuerdo n.º 3, de tipo `adelantado`.
- Hora 11: al decidir cómo reunir reservas, el objetivo guarda que elige
  **(43, 58) en lugar de (44, 57)** y cita ese recuerdo y el evento 187.

El cambio de destino sale de la razón almacenada al decidir; no se infiere
del dibujo de la ruta. La prueba controlada
`test_un_mal_recuerdo_cambia_la_eleccion_y_queda_dicho_por_que`, en
`pruebas/test_sociedad.py`, compara además la decisión con y sin experiencia.

## Información que se comprueba y trato posterior

- Hora 329, evento **2057**: Sima indica a Elai bayas en (14, 0).
- Hora 345, evento **2177**: Elai comprueba que es cierto; la causa es la
  indicación y su confianza en Sima pasa a 36.
- Hora 392, evento **2469**: Elai vuelve a pedir comida a Sima.

La indicación y su comprobación tienen enlace causal. La petición posterior
es una secuencia observada entre las mismas personas; por sí sola no demuestra
que la indicación haya sido la única causa de elegir a Sima.

## Qué demuestran las pruebas controladas

Las escenas de `pruebas/test_sociedad.py` mantienen controladas distancias,
inventarios y necesidades para comprobar efectos concretos:

- `test_tras_la_negativa_pide_a_otra_persona`: sin experiencia pide a B;
  tras una negativa injustificada de B, dos días después pide a C ante la
  misma disposición. La confianza de A en B queda en −15; la inversa no cambia.
- `test_quien_debe_una_ayuda_corresponde_aunque_sea_poco_sociable`: el recuerdo
  de una ayuda modifica la respuesta y queda enlazado con la nueva entrega.
- `test_la_noticia_se_comprueba_despues_y_cambia_la_confianza` y la prueba de
  noticia reciente falsa frente a vieja: comprueban aprendizaje e incertidumbre.

Estas escenas son pruebas preparadas, no emergencia espontánea. La cadena
completa negativa → relación peor → nueva decisión social no apareció en el
mundo libre anterior. No se han cambiado las reglas para forzarla.

## Balance de la observación libre

Al año quedan **21/25 vivos**, con **4932 eventos**: 134 peticiones, 41 entregas,
74 negativas, 41 indicaciones, 21 comprobaciones, 58 viajes fallidos, 28 fuentes
agotadas de trayecto corto y 1 ofrecimiento rehusado. La traza recoge 388
objetivos nuevos o rehechos en los que aparece una experiencia pertinente o un
destino alternativo; no son 388 decisiones sociales ni 388 episodios distintos.

Nilo da 16 veces, Sima 11 y Olin 5. Elai pide 32 veces, Arek 31 y Edur 28.
Son diferencias observadas en una semilla, no una demostración estadística del
efecto aislado de cada rasgo; para eso están las comparaciones controladas.

En la abundancia hay pocas entregas porque pocas personas necesitan comida.
En escasez crecen las oportunidades, pero una persona que sigue pasando hambre
rara vez tiene excedente para corresponder. La reciprocidad existe y deja
rastro; todavía no es una sociedad compleja.
