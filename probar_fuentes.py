"""Prueba temporal: qué fuentes responden desde GitHub."""
import actualizar as a

C = {
 "br": {
  "Folha de S.Paulo": ("https://www.folha.uol.com.br", ["https://feeds.folha.uol.com.br/emcimadahora/rss091.xml", "https://feeds.folha.uol.com.br/poder/rss091.xml"]),
  "O Globo": ("https://oglobo.globo.com", ["https://oglobo.globo.com/rss/oglobo", "https://oglobo.globo.com/rss.xml", "https://oglobo.globo.com/rss/top_noticias/"]),
  "O Estado de S. Paulo": ("https://www.estadao.com.br", ["https://www.estadao.com.br/arc/outboundfeeds/feeds/rss/sections/politica/", "https://www.estadao.com.br/rss/ultimas.xml", "https://www.estadao.com.br/arc/outboundfeeds/rss/?outputType=xml"]),
  "Correio Braziliense": ("https://www.correiobraziliense.com.br", ["https://www.correiobraziliense.com.br/rss/noticia-brasil.xml", "https://www.correiobraziliense.com.br/rss.xml", "https://www.correiobraziliense.com.br/rss/noticia-politica.xml"]),
  "Gazeta do Povo": ("https://www.gazetadopovo.com.br", ["https://www.gazetadopovo.com.br/feed/rss/ultimas-noticias.xml", "https://www.gazetadopovo.com.br/feed/rss/republica.xml", "https://www.gazetadopovo.com.br/rss/"]),
  "CartaCapital": ("https://www.cartacapital.com.br", ["https://www.cartacapital.com.br/feed/"]),
  "Valor Econômico": ("https://valor.globo.com", ["https://valor.globo.com/rss/valor", "https://pox.globo.com/rss/valor"]),
  "G1": ("https://g1.globo.com", ["https://g1.globo.com/rss/g1/", "https://g1.globo.com/rss/g1/politica/"]),
  "Metrópoles": ("https://www.metropoles.com", ["https://www.metropoles.com/feed"]),
  "UOL": ("https://www.uol.com.br", ["https://rss.uol.com.br/feed/noticias.xml"]),
  "Jornal do Brasil": ("https://www.jb.com.br", ["https://www.jb.com.br/rss.xml", "https://www.jb.com.br/feed"]),
  "Brasil de Fato": ("https://www.brasildefato.com.br", ["https://www.brasildefato.com.br/rss2.xml", "https://www.brasildefato.com.br/feed/"]),
  "O Dia": ("https://odia.ig.com.br", ["https://odia.ig.com.br/rss.xml"]),
 },
}

for pais, periodicos in C.items():
    print(f"\n===== {pais} =====")
    for nombre, (web, feeds) in periodicos.items():
        for url in feeds:
            try:
                n = a.leer_rss(url)
                print(f"RSS  {nombre} | {len(n)} | {url} | {n[0]['titulo'][:90] if n else ''} | entradilla={bool(n and n[0]['entradilla'])}")
            except Exception as e:
                print(f"RSS  {nombre} | ERROR {str(e)[:80]} | {url}")
        try:
            n = a.leer_web(web)
            print(f"WEB  {nombre} | {len(n)} | {web} | {n[0]['titulo'][:90] if n else ''}")
        except Exception as e:
            print(f"WEB  {nombre} | ERROR {str(e)[:80]} | {web}")
