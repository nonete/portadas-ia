"""Prueba temporal: qué fuentes responden desde GitHub."""
import actualizar as a

C = {
 "lr": {
  "La Rioja (diario)": ("https://www.larioja.com", ["https://www.larioja.com/rss/2.0/portada", "https://www.larioja.com/rss/2.0/?section=la-rioja", "https://www.larioja.com/rss/2.0/portada/index.rss"]),
  "NueveCuatroUno": ("https://nuevecuatrouno.com", ["https://nuevecuatrouno.com/feed/"]),
  "Rioja2": ("https://www.rioja2.com", ["https://www.rioja2.com/feed/", "https://www.rioja2.com/rss/", "https://www.rioja2.com/rss.xml"]),
  "Noticias de La Rioja": ("https://www.noticiasdelarioja.com", ["https://www.noticiasdelarioja.com/rss/", "https://www.noticiasdelarioja.com/feed/", "https://www.noticiasdelarioja.com/rss/portada.xml"]),
  "El Día de La Rioja": ("https://www.eldiadelarioja.es", ["https://www.eldiadelarioja.es/rss", "https://www.eldiadelarioja.es/rss/portada.xml", "https://www.eldiadelarioja.es/RSS/Portada.xml"]),
  "elDiario.es La Rioja": ("https://www.eldiario.es/la-rioja/", ["https://www.eldiario.es/rss/la-rioja/", "https://www.eldiario.es/la-rioja/rss/", "https://www.eldiario.es/rss/section/la-rioja/"]),
  "20minutos La Rioja": ("https://www.20minutos.es/la-rioja/", ["https://www.20minutos.es/rss/la-rioja/", "https://www.20minutos.es/rss/la-rioja"]),
  "Europa Press La Rioja": ("https://www.europapress.es/la-rioja/", ["https://www.europapress.es/rss/rss.aspx?ch=00283", "https://www.europapress.es/rss/rss.aspx?ch=283"]),
  "Haro Digital": ("https://harodigital.com", ["https://harodigital.com/feed/"]),
  "Actualidad Rioja Baja": ("https://www.actualidadriojabaja.com", ["https://www.actualidadriojabaja.com/feed/"]),
  "Rioja Actual": ("https://www.riojaactual.com", ["https://www.riojaactual.com/feed/"]),
  "COPE La Rioja": ("https://www.cope.es/emisoras/la-rioja", ["https://www.cope.es/api/es/emisoras/la-rioja/rss"]),
  "RTVE La Rioja": ("https://www.rtve.es/noticias/la-rioja/", ["https://www.rtve.es/api/tematicas/1565/noticias.rss"]),
  "La Vanguardia La Rioja": ("https://www.lavanguardia.com/local/la-rioja", ["https://www.lavanguardia.com/rss/local/la-rioja.xml"]),
  "Logroño en sus bares / Gente": ("https://www.gentedigital.es/logrono/", ["https://www.gentedigital.es/rss/logrono/", "https://www.gentedigital.es/logrono/rss/"]),
 },
}

for pais, periodicos in C.items():
    print(f"\n===== {pais} =====")
    for nombre, (web, feeds) in periodicos.items():
        for url in feeds:
            try:
                n = a.leer_rss(url)
                print(f"RSS  {nombre} | {len(n)} | {url} | {n[0]['titulo'][:80] if n else ''} | entradilla={bool(n and n[0]['entradilla'])}")
            except Exception as e:
                print(f"RSS  {nombre} | ERROR {str(e)[:60]} | {url}")
        try:
            n = a.leer_web(web)
            print(f"WEB  {nombre} | {len(n)} | {web} | {n[0]['titulo'][:80] if n else ''} || {n[3]['titulo'][:60] if len(n)>3 else ''}")
        except Exception as e:
            print(f"WEB  {nombre} | ERROR {str(e)[:60]} | {web}")
