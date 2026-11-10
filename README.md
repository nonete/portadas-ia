# 📰 Portadas IA

Web hecha con **Streamlit** que, al entrar, lee las portadas de **El País, El Mundo, ABC, Público y OKdiario** y las resume con **ChatGPT** a través de **LangChain**.

## Cómo funciona

1. **Leer**: descarga los titulares de portada de cada periódico por RSS (si un RSS falla, los saca de la portada web).
2. **Resumir**: una cadena de LangChain (`prompt | modelo | texto`) pide a ChatGPT un resumen de cada portada y otro con los temas que más se repiten.
3. **Mostrar**: Streamlit pinta los resúmenes y, debajo de cada uno, los titulares originales con su enlace.

El resultado se guarda 30 minutos, así que no se gasta dinero de OpenAI en cada visita. El botón **Actualizar ahora** fuerza una lectura nueva.

## Secrets necesarios

En Streamlit Community Cloud → tu app → **Settings → Secrets**:

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```

## Publicarla en Streamlit Community Cloud

1. Entra en https://share.streamlit.io y pulsa **Create app**.
2. Elige este repositorio, rama `main` y archivo `app.py`.
3. En **Advanced settings → Secrets** pega las dos líneas de arriba con tu clave y tu modelo.
4. Pulsa **Deploy**.

## Probarla en tu ordenador

```bash
pip install -r requirements.txt
# crea .streamlit/secrets.toml con las dos líneas de arriba
streamlit run app.py
```
