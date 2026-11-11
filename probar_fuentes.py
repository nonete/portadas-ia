"""Prueba temporal: qué fuentes responden desde GitHub."""
import actualizar as a

C = {
 "eg": {
  "Al-Ahram": ("https://gate.ahram.org.eg", ["https://gate.ahram.org.eg/rss/", "https://gate.ahram.org.eg/rss.aspx", "https://gate.ahram.org.eg/RSS/1.aspx"]),
  "Ahram Online (en)": ("https://english.ahram.org.eg", ["https://english.ahram.org.eg/rss.aspx", "https://english.ahram.org.eg/RSS/0.aspx", "https://english.ahram.org.eg/rss/"]),
  "Al-Masry Al-Youm": ("https://www.almasryalyoum.com", ["https://www.almasryalyoum.com/rss/rssfeeds", "https://www.almasryalyoum.com/rss/rssfeed", "https://www.almasryalyoum.com/rss/rssfeeds?homePage=true"]),
  "Youm7": ("https://www.youm7.com", ["https://www.youm7.com/rss/SectionRss?SectionID=65", "https://www.youm7.com/rss/SectionRss?SectionID=203", "https://www.youm7.com/rss/SectionRss?SectionID=97"]),
  "Al-Shorouk": ("https://www.shorouknews.com", ["https://www.shorouknews.com/rss", "https://www.shorouknews.com/RSS/egypt", "https://www.shorouknews.com/rss.aspx"]),
  "Akhbar El-Yom": ("https://akhbarelyom.com", ["https://akhbarelyom.com/rss", "https://akhbarelyom.com/RSS/1", "https://akhbarelyom.com/feed"]),
  "El Watan": ("https://www.elwatannews.com", ["https://www.elwatannews.com/home/rssfeeds", "https://www.elwatannews.com/rss", "https://www.elwatannews.com/home/rss"]),
  "Al-Wafd": ("https://www.alwafd.news", ["https://www.alwafd.news/rss", "https://www.alwafd.news/feed", "https://alwafd.news/rss.xml"]),
  "Al-Dostor": ("https://www.dostor.org", ["https://www.dostor.org/rss.aspx", "https://www.dostor.org/rss", "https://www.dostor.org/feed"]),
  "Mada Masr": ("https://www.madamasr.com/ar/", ["https://www.madamasr.com/ar/feed/", "https://www.madamasr.com/en/feed/", "https://www.madamasr.com/feed/"]),
  "Egypt Independent (en)": ("https://www.egyptindependent.com", ["https://www.egyptindependent.com/feed/", "https://egyptindependent.com/feed/"]),
  "Daily News Egypt (en)": ("https://www.dailynewsegypt.com", ["https://www.dailynewsegypt.com/feed/", "https://dailynewsegypt.com/feed/"]),
  "Masrawy": ("https://www.masrawy.com", ["https://www.masrawy.com/rss/news", "https://www.masrawy.com/rss", "https://www.masrawy.com/rss/rssfeeds"]),
  "Egypt Today (en)": ("https://www.egypttoday.com", ["https://www.egypttoday.com/RSS/1", "https://www.egypttoday.com/rss", "https://www.egypttoday.com/feed"]),
  "Al-Gomhuria": ("https://www.gomhuriaonline.com", ["https://www.gomhuriaonline.com/rss", "https://www.gomhuriaonline.com/feed"]),
  "Cairo24": ("https://www.cairo24.com", ["https://www.cairo24.com/rss.aspx", "https://www.cairo24.com/rss"]),
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
