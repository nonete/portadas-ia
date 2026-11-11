# 📰 Portadas IA

Web hecha con **Streamlit**, **LangChain** y **ChatGPT** que sigue el día en cinco portadas por país. Arriba hay un selector:

- **España**: El País, El Mundo, ABC, Público y OKdiario.
- **Francia**: Le Monde, Le Figaro, Libération, Le Parisien y Ouest-France.

Todo se muestra en español, también el análisis de la prensa francesa.

Qué muestra:

- **Crispación ahora**: nota de 0 a 100 con Crispito, la mascota, en uno de sus 6 estados.
- **¿Quién quieres que te dé la opinión?**: el día visto por un comunista, un anarquista, un liberal, uno de extrema derecha y una demócrata de centro (personajes inventados, texto de ChatGPT).
- **Lo más repetido hoy**: los temas que comparten las portadas.
- **Periódico a periódico**: resumen, nivel de populismo (0-100) y sesgo de cada uno.
- **Crispación día a día**: una tabla con un registro por día.

## Sección Discapacidad

Arriba del todo hay un selector de sección: **Portadas** y **Discapacidad** (también `?seccion=discapacidad` en la dirección).

La sección Discapacidad muestra noticias sobre discapacidad de medios españoles, repartidas sin repetirse en **hoy**, **últimas semanas**, **último mes** y **último año**, y un **resumen de la IA** de lo que se está hablando en España.

- `actualizar_discapacidad.py` busca las noticias (Google Noticias, Bing Noticias y el RSS de unos 50 medios), pide el resumen a ChatGPT y guarda `datos/discapacidad/ultimo.json`. Lo ejecuta GitHub Actions después de `actualizar.py`.
- `seccion_discapacidad.py` enseña ese archivo; `app.py` lo llama al elegir la sección.
- Para añadir un medio: una línea en `RSS_PERIODICOS` (o `RSS_ESPECIALIZADOS`) y, si su dirección no acaba en `.es`, `.cat`, `.eus` o `.gal`, otra en `MEDIOS_ES_OTRA_TERMINACION`.

## Cómo funciona

Hay dos piezas:

| Archivo | Qué hace | Quién lo ejecuta |
|---|---|---|
| `actualizar.py` | Lee las portadas, las analiza con ChatGPT y guarda el resultado en `datos/<país>/` | GitHub Actions, a las 8:00 y a las 18:00 (hora de Madrid) |
| `app.py` | Enseña lo que hay en `datos/<país>/`, según el selector | Streamlit Community Cloud |
| `crear_crispito.py` y `crear_caricaturas.py` | Dibujan la mascota y las caricaturas (carpetas `crispito/` y `caricaturas/`) | Tú, solo si quieres cambiar los dibujos |

En `datos/` hay una carpeta por país (`datos/es`, `datos/fr`) con dos archivos:

- `ultimo.json`: la última actualización (lo que se ve en la web).
- `historial.json`: un registro por día con el nivel de crispación. Cada día se añade uno.

La web no llama a OpenAI: solo lee esos archivos. Así el gasto es fijo (cinco actualizaciones al día por país) y el historial no se pierde.

## Secrets necesarios (en GitHub)

En el repositorio → **Settings → Secrets and variables → Actions → New repository secret**, crea estos dos:

| Nombre | Valor |
|---|---|
| `OPENAI_API_KEY` | tu clave de OpenAI (`sk-...`) |
| `OPENAI_MODEL` | el modelo, por ejemplo `gpt-4o-mini` |

Streamlit ya no necesita ningún Secret.

## Lanzar una actualización a mano

En el repositorio → pestaña **Actions** → **Actualizar portadas** → **Run workflow**.

## Publicarla en Streamlit Community Cloud

1. Entra en https://share.streamlit.io y pulsa **Create app**.
2. Elige este repositorio, rama `main` y archivo `app.py`.
3. Pulsa **Deploy**.
