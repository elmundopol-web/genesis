/* GENESIS · paleta común del mundo (F4.4).

   Unos treinta y dos colores base para personas, construcciones y naturaleza.
   Cada objeto se pinta con tres tonos derivados de su base (luz, base y sombra)
   y un contorno más oscuro de su propio color: `tonos()` y `contorno()` los
   calculan siempre igual. La luz llega de arriba a la izquierda; las sombras
   proyectadas caen abajo a la derecha con un mismo azul oscuro semitransparente.
   Verdes y tierras contenidos; la ropa, más saturada, para distinguir a cada
   habitante. */

export const PALETA = {
  // tierras
  tierra: [128, 98, 64], tierraClara: [176, 146, 100], barro: [92, 70, 48], arena: [206, 186, 140],
  // verdes
  hierba: [104, 146, 64], hierbaClara: [148, 178, 82], musgo: [70, 104, 52], bosque: [40, 78, 50], bosqueHondo: [24, 50, 40],
  // agua
  agua: [52, 112, 150], aguaClara: [96, 164, 190], espuma: [214, 236, 236],
  // madera y paja
  madera: [120, 82, 50], maderaClara: [168, 122, 76], paja: [196, 156, 82], pajaOscura: [138, 100, 52],
  piedra: [136, 134, 124],
  // piel
  piel1: [244, 212, 182], piel2: [226, 180, 140], piel3: [196, 138, 96], piel4: [154, 102, 68], piel5: [110, 72, 50],
  // pelo
  pelo1: [44, 34, 30], pelo2: [96, 60, 36], pelo3: [150, 92, 46], pelo4: [214, 170, 92], canas: [214, 212, 204],
  // ropa: saturada, ocho tonos bien separados
  rojo: [214, 70, 52], naranja: [236, 146, 44], amarillo: [240, 210, 76], verde: [92, 176, 82],
  turquesa: [44, 168, 166], azul: [64, 112, 214], violeta: [150, 84, 196], blanco: [236, 230, 214],
};

export const PIEL = [PALETA.piel1, PALETA.piel2, PALETA.piel3, PALETA.piel4, PALETA.piel5];
export const PELO = [PALETA.pelo1, PALETA.pelo2, PALETA.pelo3, PALETA.pelo4, PALETA.canas];
export const ROPA = [PALETA.rojo, PALETA.naranja, PALETA.amarillo, PALETA.verde, PALETA.turquesa, PALETA.azul,
                     PALETA.violeta, PALETA.blanco];

// Sombra proyectada común: azul oscuro semitransparente, hacia abajo a la derecha.
export const SOMBRA = [22, 30, 62];
export const SOMBRA_ALFA = 0.34;
export const SOMBRA_DIR = [0.55, 0.32]; // desplazamiento por unidad de altura del objeto

const lim = (v) => (v < 0 ? 0 : v > 255 ? 255 : Math.round(v));
/* Luz (tibia), base y sombra (fría) de un color: el trío con el que se pinta cada volumen. */
export function tonos(c) {
  return {
    luz: [lim(c[0] * 1.16 + 18), lim(c[1] * 1.14 + 14), lim(c[2] * 1.06 + 6)],
    base: c,
    sombra: [lim(c[0] * 0.66), lim(c[1] * 0.66 + 4), lim(c[2] * 0.74 + 12)],
  };
}
/* Contorno: el mismo color, mucho más oscuro y algo más frío. */
export function contorno(c) {
  return [lim(c[0] * 0.34), lim(c[1] * 0.34 + 2), lim(c[2] * 0.4 + 8)];
}
export const css = (c, a = 1) => (a >= 1 ? `rgb(${c[0]},${c[1]},${c[2]})` : `rgba(${c[0]},${c[1]},${c[2]},${a})`);
