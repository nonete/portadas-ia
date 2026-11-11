/*
  Portadas IA · el poco JavaScript de la web estática.
  La página funciona sin él: solo añade dos comodidades.
    1. Las opiniones se ven por pestañas en vez de todas seguidas.
    2. "Próxima lectura" dice la hora exacta que toca.
*/

// Marca que hay JavaScript: el CSS usa la clase "js" para mostrar las pestañas.
document.documentElement.classList.add("js");

// --- 1. Pestañas de las opiniones --------------------------------------

const pestanas = Array.from(document.querySelectorAll('.pestanas [role="tab"]'));

function elegir(pestana, enfocar) {
  pestanas.forEach(function (otra) {
    const activa = otra === pestana;
    otra.setAttribute("aria-selected", activa ? "true" : "false");
    otra.tabIndex = activa ? 0 : -1;
    document.getElementById(otra.getAttribute("aria-controls")).hidden = !activa;
  });
  if (enfocar) pestana.focus();
}

pestanas.forEach(function (pestana, posicion) {
  pestana.addEventListener("click", function () { elegir(pestana, false); });
  // Con las flechas del teclado se pasa de un personaje a otro.
  pestana.addEventListener("keydown", function (evento) {
    let paso = 0;
    if (evento.key === "ArrowRight") paso = 1;
    if (evento.key === "ArrowLeft") paso = -1;
    if (paso === 0) return;
    evento.preventDefault();
    elegir(pestanas[(posicion + paso + pestanas.length) % pestanas.length], true);
  });
});

if (pestanas.length > 0) elegir(pestanas[0], false);

// --- 2. Próxima lectura de portadas ------------------------------------

const proxima = document.getElementById("proxima");
if (proxima && window.HORAS_LECTURA) {
  // La hora que es ahora mismo en Madrid, esté donde esté quien mira la web.
  const horaMadrid = Number(
    new Intl.DateTimeFormat("es-ES", { timeZone: "Europe/Madrid", hour: "numeric", hourCycle: "h23" })
      .format(new Date())
  );
  const siguiente = window.HORAS_LECTURA.find(function (hora) { return hora > horaMadrid; });
  proxima.textContent = siguiente
    ? "Hoy a las " + siguiente + ":00"
    : "Mañana a las " + window.HORAS_LECTURA[0] + ":00";
}
