/* Service worker da TV Corporativa
   - player.html e arquivos .json: tenta a internet primeiro; sem internet, usa a última cópia salva
   - imagens, vídeos e logos (pasta midia/ e outros arquivos): usa a cópia salva; baixa só se ainda não tiver */
const CACHE_APP = 'tvcorp-app-v1';
const CACHE_MIDIA = 'tvcorp-midias';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_APP).then(c => c.addAll(['player.html', 'programacao.json']).catch(() => {})));
  self.skipWaiting();
});
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;                // clima (Open-Meteo) etc.: direto na internet
  if (req.headers.get('range')) return;                       // vídeo em pedaços: o player já trata pelo cache

  const chave = url.origin + url.pathname;                    // ignora ?t=... para guardar uma cópia só
  const ehApp = url.pathname.endsWith('.json') || url.pathname.endsWith('.html') || url.pathname.endsWith('/') || url.pathname.endsWith('sw.js');

  if (ehApp) {
    e.respondWith(fetch(req).then(r => {
      if (r.ok) { const c = r.clone(); caches.open(CACHE_APP).then(k => k.put(chave, c)); }
      return r;
    }).catch(async () => {
      const r = await (await caches.open(CACHE_APP)).match(chave);
      if (!r) return Response.error();
      // marca a resposta como "cópia salva" para o player saber que está sem internet
      const h = new Headers(r.headers); h.set('x-tvcorp-offline', '1');
      return new Response(await r.blob(), {status: 200, headers: h});
    }));
  } else {
    e.respondWith(caches.open(CACHE_MIDIA).then(async k => {
      const salvo = await k.match(req.url) || await k.match(chave);
      if (salvo) return salvo;
      const r = await fetch(req);
      if (r.ok) k.put(chave, r.clone());
      return r;
    }));
  }
});
