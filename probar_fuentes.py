"""Prueba temporal: qué fuentes responden desde GitHub."""
import actualizar as a

C = {
 "us": {
  "The New York Times": ("https://www.nytimes.com", ["https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"]),
  "The Washington Post": ("https://www.washingtonpost.com", ["https://feeds.washingtonpost.com/rss/national", "https://www.washingtonpost.com/arcio/rss/", "https://feeds.washingtonpost.com/rss/politics"]),
  "The Wall Street Journal": ("https://www.wsj.com", ["https://feeds.content.dowjones.io/public/rss/RSSUSnews", "https://feeds.a.dj.com/rss/RSSWorldNews.xml", "https://feeds.content.dowjones.io/public/rss/RSSWorldNews"]),
  "USA Today": ("https://www.usatoday.com", ["https://rssfeeds.usatoday.com/usatoday-NewsTopStories", "https://www.usatoday.com/rss/"]),
  "New York Post": ("https://nypost.com", ["https://nypost.com/feed/"]),
  "Los Angeles Times": ("https://www.latimes.com", ["https://www.latimes.com/rss2.0.xml", "https://www.latimes.com/index.rss"]),
  "Fox News": ("https://www.foxnews.com", ["https://moxie.foxnews.com/google-publisher/latest.xml"]),
 },
 "gb": {
  "The Guardian": ("https://www.theguardian.com/uk", ["https://www.theguardian.com/uk/rss"]),
  "The Times": ("https://www.thetimes.com", ["https://www.thetimes.com/?service=rss", "https://www.thetimes.co.uk/rss"]),
  "The Telegraph": ("https://www.telegraph.co.uk", ["https://www.telegraph.co.uk/rss.xml", "https://www.telegraph.co.uk/news/rss.xml"]),
  "Daily Mail": ("https://www.dailymail.co.uk", ["https://www.dailymail.co.uk/home/index.rss", "https://www.dailymail.co.uk/news/index.rss"]),
  "The Sun": ("https://www.thesun.co.uk", ["https://www.thesun.co.uk/feed/", "https://www.thesun.co.uk/news/feed/"]),
  "Daily Mirror": ("https://www.mirror.co.uk", ["https://www.mirror.co.uk/?service=rss", "https://www.mirror.co.uk/news/?service=rss"]),
  "The Independent": ("https://www.independent.co.uk", ["https://www.independent.co.uk/rss", "https://www.independent.co.uk/news/uk/rss"]),
  "Financial Times": ("https://www.ft.com", ["https://www.ft.com/rss/home/uk", "https://www.ft.com/rss/home"]),
  "Daily Express": ("https://www.express.co.uk", ["https://www.express.co.uk/posts/rss/1", "https://feeds.feedburner.com/daily-express-news-showbiz-sport"]),
 },
 "de": {
  "Frankfurter Allgemeine": ("https://www.faz.net", ["https://www.faz.net/rss/aktuell/"]),
  "Süddeutsche Zeitung": ("https://www.sueddeutsche.de", ["https://rss.sueddeutsche.de/rss/Topthemen", "https://rss.sueddeutsche.de/app/service/rss/alles/index.rss"]),
  "Die Welt": ("https://www.welt.de", ["https://www.welt.de/feeds/topnews.rss", "https://www.welt.de/feeds/latest.rss"]),
  "Bild": ("https://www.bild.de", ["https://www.bild.de/feed/alles.xml", "https://www.bild.de/rssfeeds/vw-alles/vw-alles-26970192,dzbildplus=true,sort=1,teaserbildmobil=false,view=rss2.bild.xml", "https://www.bild.de/rssfeeds/rss3-20745882,feed=alles.bild.html"]),
  "Der Spiegel": ("https://www.spiegel.de", ["https://www.spiegel.de/schlagzeilen/tops/index.rss", "https://www.spiegel.de/schlagzeilen/index.rss"]),
  "Die Zeit": ("https://www.zeit.de", ["https://newsfeed.zeit.de/index"]),
  "taz": ("https://taz.de", ["https://taz.de/!p4608;rss/", "https://taz.de/rss.xml"]),
  "Der Tagesspiegel": ("https://www.tagesspiegel.de", ["https://www.tagesspiegel.de/contentexport/feed/home"]),
 },
 "it": {
  "Corriere della Sera": ("https://www.corriere.it", ["https://xml2.corriereobjects.it/rss/homepage.xml", "https://www.corriere.it/rss/homepage.xml"]),
  "la Repubblica": ("https://www.repubblica.it", ["https://www.repubblica.it/rss/homepage/rss2.0.xml"]),
  "La Stampa": ("https://www.lastampa.it", ["https://www.lastampa.it/rss/copertina.xml", "https://www.lastampa.it/rss.xml"]),
  "Il Giornale": ("https://www.ilgiornale.it", ["https://www.ilgiornale.it/feed.xml", "https://www.ilgiornale.it/rss.xml"]),
  "Il Fatto Quotidiano": ("https://www.ilfattoquotidiano.it", ["https://www.ilfattoquotidiano.it/feed/"]),
  "Libero": ("https://www.liberoquotidiano.it", ["https://www.liberoquotidiano.it/rss.xml"]),
  "Il Sole 24 Ore": ("https://www.ilsole24ore.com", ["https://www.ilsole24ore.com/rss/italia.xml", "https://www.ilsole24ore.com/rss/homepage.xml"]),
  "Il Messaggero": ("https://www.ilmessaggero.it", ["https://www.ilmessaggero.it/rss/home.xml"]),
 },
 "ru": {
  "Kommersant": ("https://www.kommersant.ru", ["https://www.kommersant.ru/RSS/main.xml", "https://www.kommersant.ru/RSS/news.xml"]),
  "Izvestia": ("https://iz.ru", ["https://iz.ru/xml/rss/all.xml"]),
  "Rossiyskaya Gazeta": ("https://rg.ru", ["https://rg.ru/xml/index.xml"]),
  "Komsomolskaya Pravda": ("https://www.kp.ru", ["https://www.kp.ru/rss/allsections.xml"]),
  "Moskovski Komsomolets": ("https://www.mk.ru", ["https://www.mk.ru/rss/index.xml", "https://www.mk.ru/rss/news/index.xml"]),
  "Vedomosti": ("https://www.vedomosti.ru", ["https://www.vedomosti.ru/rss/news", "https://www.vedomosti.ru/rss/articles"]),
  "RBC": ("https://www.rbc.ru", ["https://rssexport.rbc.ru/rbcnews/news/30/full.rss"]),
  "Nóvaya Gazeta Europa": ("https://novayagazeta.eu", ["https://novayagazeta.eu/feed/rss"]),
  "Meduza": ("https://meduza.io", ["https://meduza.io/rss/all", "https://meduza.io/rss2/all"]),
  "The Moscow Times": ("https://www.moscowtimes.ru", ["https://www.moscowtimes.ru/rss/news", "https://www.themoscowtimes.com/rss/news"]),
 },
 "cn": {
  "Diario del Pueblo": ("http://www.people.com.cn", ["http://www.people.com.cn/rss/politics.xml", "http://en.people.cn/rss/90000.xml", "http://www.people.com.cn/rss/world.xml"]),
  "Xinhua": ("https://www.news.cn", ["http://www.xinhuanet.com/politics/news_politics.xml", "http://www.xinhuanet.com/english/rss/chinarss.xml", "https://english.news.cn/rss/chinarss.xml"]),
  "Global Times": ("https://www.globaltimes.cn", ["https://www.globaltimes.cn/rss/outbrain.xml"]),
  "Huanqiu": ("https://www.huanqiu.com", []),
  "China Daily": ("https://www.chinadaily.com.cn", ["https://www.chinadaily.com.cn/rss/china_rss.xml", "http://www.chinadaily.com.cn/rss/cndy_rss.xml", "https://www.chinadaily.com.cn/rss/world_rss.xml"]),
  "South China Morning Post": ("https://www.scmp.com", ["https://www.scmp.com/rss/91/feed", "https://www.scmp.com/rss/4/feed", "https://www.scmp.com/rss/2/feed"]),
  "The Paper": ("https://www.thepaper.cn", []),
  "Caixin": ("https://www.caixinglobal.com", ["https://www.caixinglobal.com/rss.xml", "https://gateway.caixin.com/api/data/global/feedlyRss.xml"]),
  "CGTN": ("https://www.cgtn.com", ["https://www.cgtn.com/subscribe/rss/section/china.xml"]),
  "Guangming": ("https://www.gmw.cn", []),
  "Beijing News": ("https://www.bjnews.com.cn", []),
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
