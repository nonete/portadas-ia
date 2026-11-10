# 📰 Portadas IA

Web hecha con **Streamlit** que resume las portadas de **El País, El Mundo, ABC, Público y OKdiario** con **ChatGPT** a través de **LangChain**, puntúa su nivel de populismo y lleva un registro diario de la crispación.

## Cómo funciona

Hay dos piezas:

| Archivo | Qué hace | Quién lo ejecuta |
|---|---|---|
| `actualizar.py` | Lee las portadas, las analiza con ChatGPT y guarda el resultado en `datos/` | GitHub Actions, a las 8:00, 11:00, 14:00, 17:00 y 20:00 (hora de Madrid) |
| `app.py` | Enseña lo que hay en `datos/` | Streamlit Community Cloud |

En `datos/` se guardan dos archivos:

- `ultimo.json`: la última actualización (lo que se ve en la web).
- `historial.json`: un registro por día con el nivel de crispación. Cada día se añade uno.

La web no llama a OpenAI: solo lee esos archivos. Así el gasto es fijo (cinco actualizaciones al día) y el historial no se pierde.

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
