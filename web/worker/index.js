/*
  Portadas IA · la página de configuración (con clave)
  ----------------------------------------------------
  El resto de la web son archivos estáticos. Esto es lo único que "se ejecuta":
  un pequeño programa (un Worker de Cloudflare) que atiende:

    /configuracion        → la página (pagina.html), solo con la clave
    GET  /api/config      → los prompts: originales y cambiados
    PUT  /api/config      → guarda los prompts cambiados en GitHub
    GET  /api/estado      → cómo va la última actualización
    POST /api/actualizar  → lanza "Actualizar portadas" en GitHub

  Usa dos secretos, que se guardan en GitHub y publicar-web.yml copia a
  Cloudflare:
    CLAVE_CONFIGURACION   → la clave para entrar (solo si PEDIR_CLAVE es "si")
    GITHUB_TOKEN_CONFIG   → un token de GitHub para guardar los prompts y
                            lanzar la actualización. Sin él la página se ve,
                            pero no puede guardar ni actualizar.

  Los prompts cambiados se guardan en config/prompts.json del repositorio,
  así queda un historial de cada cambio.
*/

import PAGINA from "./pagina.html";
import ORIGINALES from "../../config/prompts_originales.json";

const ARCHIVO = "config/prompts.json";
const WORKFLOW = "actualizar.yml";

// Cabeceras de todas las respuestas: que ningún buscador la guarde ni la indexe.
const PRIVADO = {
  "X-Robots-Tag": "noindex, nofollow, noarchive",
  "Cache-Control": "no-store",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const ruta = url.pathname.replace(/\/+$/, "");

    // Cualquier otra dirección es de la web estática.
    if (ruta !== "/configuracion" && !ruta.startsWith("/api/")) {
      return env.ASSETS.fetch(request);
    }

    try {
      return await atender(request, env, url, ruta);
    } catch (error) {
      return json({ error: "Error inesperado: " + error.message }, 500);
    }
  },
};

async function atender(request, env, url, ruta) {
  // 1. ¿Hay que pedir clave? Se decide con PEDIR_CLAVE en web/wrangler.jsonc.
  //    Con "no", cualquiera que conozca la dirección puede entrar.
  const pedirClave = env.PEDIR_CLAVE !== "no";
  if (pedirClave && !env.CLAVE_CONFIGURACION) {
    return texto("La página de configuración pide clave, pero falta el secreto CLAVE_CONFIGURACION.", 503);
  }

  // 2. ¿Trae la clave correcta?
  if (pedirClave && !(await claveCorrecta(request, env))) {
    await esperar(700); // frena a quien pruebe claves una tras otra
    return new Response("Hace falta la clave.", {
      status: 401,
      headers: { ...PRIVADO, "WWW-Authenticate": 'Basic realm="Portadas IA", charset="UTF-8"' },
    });
  }

  // 3. Las acciones que cambian algo solo se aceptan desde la propia página
  //    (así otra web no puede provocarlas a escondidas).
  if (request.method !== "GET" && request.headers.get("Origin") !== url.origin) {
    return json({ error: "Petición no permitida." }, 403);
  }

  if (ruta === "/configuracion" && request.method === "GET") {
    return new Response(PAGINA, { headers: { ...PRIVADO, "Content-Type": "text/html; charset=utf-8" } });
  }
  // Sin el token de GitHub la página se puede ver, pero no guardar ni actualizar.
  if (!env.GITHUB_TOKEN_CONFIG) {
    if (ruta === "/api/config" && request.method === "GET") {
      return json({ prompts: ORIGINALES, cambiados: {}, sha: null, sinToken: true, sinClave: !pedirClave });
    }
    if (ruta === "/api/estado" && request.method === "GET") return json({ ultima: null, sinToken: true });
    return json({ error: "Falta el secreto GITHUB_TOKEN_CONFIG: sin él no se puede guardar ni actualizar." }, 503);
  }

  if (ruta === "/api/config" && request.method === "GET") return leerConfig(env, pedirClave);
  if (ruta === "/api/config" && request.method === "PUT") return guardarConfig(request, env);
  if (ruta === "/api/estado" && request.method === "GET") return estado(env);
  if (ruta === "/api/actualizar" && request.method === "POST") return actualizar(request, env);
  return json({ error: "No existe." }, 404);
}

// ----------------------------------------------------------------------
// La clave
// ----------------------------------------------------------------------

// El navegador envía "usuario:clave" (el usuario da igual). Se comparan los
// resúmenes SHA-256 para que la comparación tarde siempre lo mismo.
async function claveCorrecta(request, env) {
  const cabecera = request.headers.get("Authorization") || "";
  if (!cabecera.startsWith("Basic ")) return false;
  let recibida;
  try {
    const bytes = Uint8Array.from(atob(cabecera.slice(6)), (letra) => letra.charCodeAt(0));
    const usuarioYClave = new TextDecoder().decode(bytes);
    recibida = usuarioYClave.slice(usuarioYClave.indexOf(":") + 1);
  } catch {
    return false;
  }
  const [a, b] = await Promise.all([resumen(recibida), resumen(env.CLAVE_CONFIGURACION.trim())]);
  let distintos = 0;
  for (let i = 0; i < a.length; i++) distintos |= a[i] ^ b[i];
  return distintos === 0;
}

async function resumen(cadena) {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(cadena)));
}

function esperar(milisegundos) {
  return new Promise((resolver) => setTimeout(resolver, milisegundos));
}

// ----------------------------------------------------------------------
// Hablar con GitHub
// ----------------------------------------------------------------------

function github(env, camino, opciones = {}) {
  const base = env.GITHUB_API || "https://api.github.com";
  return fetch(`${base}/repos/${env.REPO}${camino}`, {
    ...opciones,
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN_CONFIG.trim()}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "portadas-ia-configuracion",
      ...(opciones.body ? { "Content-Type": "application/json" } : {}),
    },
  });
}

async function fallo(respuesta, que) {
  let detalle = "";
  try {
    detalle = (await respuesta.json()).message || "";
  } catch {}
  let pista = "";
  if (respuesta.status === 401) pista = " El token de GitHub no vale o ha caducado.";
  if (respuesta.status === 403 || respuesta.status === 404) pista = " Revisa los permisos del token de GitHub.";
  return json({ error: `GitHub no ha podido ${que} (${respuesta.status}: ${detalle}).${pista}` }, 502);
}

// Lee config/prompts.json: los prompts cambiados y su "sha" (la huella de la
// versión, que GitHub pide para guardar encima).
async function leerCambiados(env) {
  const respuesta = await github(env, `/contents/${ARCHIVO}?ref=${env.RAMA}`);
  if (respuesta.status === 404) return { valores: {}, sha: null };
  if (!respuesta.ok) return { error: await fallo(respuesta, "leer los prompts") };
  const archivo = await respuesta.json();
  const bytes = Uint8Array.from(atob(archivo.content.replace(/\s/g, "")), (letra) => letra.charCodeAt(0));
  let valores = {};
  try {
    valores = JSON.parse(new TextDecoder().decode(bytes));
  } catch {}
  return { valores, sha: archivo.sha };
}

// ----------------------------------------------------------------------
// Las acciones
// ----------------------------------------------------------------------

async function leerConfig(env, pedirClave) {
  const cambiados = await leerCambiados(env);
  if (cambiados.error) return cambiados.error;
  return json({ prompts: ORIGINALES, cambiados: cambiados.valores, sha: cambiados.sha, sinClave: !pedirClave });
}

// Las mismas comprobaciones que hace prompts.py.
function erroresDe(texto, variables) {
  const errores = [];
  if (!texto.trim()) errores.push("está vacío");
  let resto = texto;
  for (const variable of variables) {
    if (!texto.includes(`{${variable}}`)) errores.push(`falta {${variable}}`);
    resto = resto.split(`{${variable}}`).join("");
  }
  if (/[{}]/.test(resto)) errores.push("tiene llaves { } que no son de una variable permitida");
  return errores;
}

async function guardarConfig(request, env) {
  const cuerpo = await request.json();
  const recibidos = cuerpo.valores || {};

  // Solo se guarda lo que es distinto del original, y solo si es válido.
  const guardar = {};
  for (const prompt of ORIGINALES) {
    const valor = recibidos[prompt.id];
    if (typeof valor !== "string") continue;
    const limpio = valor.replace(/\r\n/g, "\n").trim();
    if (limpio === prompt.texto.trim()) continue;
    if (limpio.length > 6000) {
      return json({ error: `«${prompt.grupo} · ${prompt.titulo}» es demasiado largo (máximo 6000 letras).` }, 400);
    }
    const errores = erroresDe(limpio, prompt.variables);
    if (errores.length) {
      return json({ error: `«${prompt.grupo} · ${prompt.titulo}»: ${errores.join("; ")}.` }, 400);
    }
    guardar[prompt.id] = limpio;
  }

  const contenido = JSON.stringify(guardar, null, 2) + "\n";
  const bytes = new TextEncoder().encode(contenido);
  let binario = "";
  for (const byte of bytes) binario += String.fromCharCode(byte);

  const respuesta = await github(env, `/contents/${ARCHIVO}`, {
    method: "PUT",
    body: JSON.stringify({
      message: "Configuración: prompts cambiados desde la web",
      content: btoa(binario),
      branch: env.RAMA,
      ...(cuerpo.sha ? { sha: cuerpo.sha } : {}),
    }),
  });
  if (respuesta.status === 409 || respuesta.status === 422) {
    return json({ error: "Los prompts han cambiado desde que abriste la página. Recárgala y repite el cambio." }, 409);
  }
  if (!respuesta.ok) return fallo(respuesta, "guardar los prompts");
  const resultado = await respuesta.json();
  return json({ ok: true, cambiados: guardar, sha: resultado.content.sha });
}

async function estado(env) {
  const respuesta = await github(env, `/actions/workflows/${WORKFLOW}/runs?per_page=1`);
  if (!respuesta.ok) return fallo(respuesta, "consultar las actualizaciones");
  const ultima = (await respuesta.json()).workflow_runs?.[0];
  if (!ultima) return json({ ultima: null });
  return json({
    ultima: {
      estado: ultima.status,          // queued, in_progress, completed
      resultado: ultima.conclusion,   // success, failure… (solo al terminar)
      inicio: ultima.created_at,
      origen: ultima.event,           // schedule (automática) o workflow_dispatch (a mano)
      // No se devuelve la dirección de GitHub: llevaría el nombre de la cuenta.
    },
  });
}

async function actualizar(request, env) {
  const cuerpo = await request.json().catch(() => ({}));
  const pais = String(cuerpo.pais || "").toLowerCase();
  if (!/^[a-z]{0,2}$/.test(pais)) return json({ error: "País no válido." }, 400);

  const respuesta = await github(env, `/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ ref: env.RAMA, inputs: { forzar: "true", pais } }),
  });
  if (!respuesta.ok) return fallo(respuesta, "lanzar la actualización");
  return json({ ok: true });
}

// ----------------------------------------------------------------------

function json(datos, status = 200) {
  return new Response(JSON.stringify(datos), {
    status,
    headers: { ...PRIVADO, "Content-Type": "application/json; charset=utf-8" },
  });
}

function texto(mensaje, status = 200) {
  return new Response(mensaje, { status, headers: { ...PRIVADO, "Content-Type": "text/plain; charset=utf-8" } });
}
