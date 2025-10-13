// Service Worker per Gestionale Agricolo Agriolo
const CACHE_NAME = 'agriolo-v1.0.0';
const OFFLINE_URL = '/offline/';

// Risorse da cachare per il funzionamento offline
const CACHE_URLS = [
  '/',
  '/static/manifest.json',
  // CSS essenziali (Bootstrap sarà caricato dai template)
  // JS essenziali
  // Immagini essenziali (quando le aggiungeremo)
];

// Installazione del service worker
self.addEventListener('install', event => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Caching app shell');
        return cache.addAll(CACHE_URLS);
      })
      .then(() => {
        console.log('[SW] Skip waiting on install');
        return self.skipWaiting();
      })
  );
});

// Attivazione del service worker
self.addEventListener('activate', event => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Claiming control');
      return self.clients.claim();
    })
  );
});

// Strategia di fetch: Network First con Cache Fallback
self.addEventListener('fetch', event => {
  // Solo per richieste GET
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip per richieste esterne (API, CDN)
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Se la richiesta va a buon fine, aggiorna la cache
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(event.request, responseClone);
            });
        }
        return response;
      })
      .catch(() => {
        // Se la rete fallisce, prova a recuperare dalla cache
        return caches.match(event.request)
          .then(response => {
            if (response) {
              return response;
            }
            
            // Se è una richiesta di navigazione e non c'è cache, 
            // mostra una pagina offline
            if (event.request.mode === 'navigate') {
              return caches.match(OFFLINE_URL);
            }
          });
      })
  );
});

// Gestione dei messaggi dal client
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Sincronizzazione in background (per funzionalità future)
self.addEventListener('sync', event => {
  console.log('[SW] Background sync event:', event.tag);
  
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

// Funzione per sincronizzazione in background
function doBackgroundSync() {
  // Qui potremmo implementare la sincronizzazione dei dati
  // quando la connessione viene ripristinata
  return Promise.resolve();
}

// Notifiche push (per funzionalità future)
self.addEventListener('push', event => {
  console.log('[SW] Push event received:', event);
  
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/static/icons/icon-192x192.png',
      badge: '/static/icons/badge-72x72.png',
      vibrate: [200, 100, 200],
      data: {
        url: data.url
      },
      actions: [
        {
          action: 'open',
          title: 'Apri',
          icon: '/static/icons/action-open.png'
        },
        {
          action: 'close',
          title: 'Chiudi',
          icon: '/static/icons/action-close.png'
        }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Gestione click sulle notifiche
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification click received.');

  event.notification.close();

  if (event.action === 'open') {
    event.waitUntil(
      clients.openWindow(event.notification.data.url)
    );
  }
});

console.log('[SW] Service Worker loaded successfully');