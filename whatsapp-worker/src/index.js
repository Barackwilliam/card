// Worker ya WhatsApp (Baileys) kwa mfumo wa michango ya harusi.
//
// - Session inahifadhiwa Postgres (wa_auth), QR na hali vinaandikwa wa_hali
//   ili msimamizi ascan QR kwenye ukurasa wa "WhatsApp" wa mfumo.
// - Jumbe zinachukuliwa kutoka foleni (michango_ujumbe, hali='kwenye_foleni')
//   na kutumwa polepole kwa kinga zote zilizo kwenye kinga.js / mtumaji.js.
// - Kufuli (advisory lock) linahakikisha worker moja tu inatumia session kwa wakati mmoja.
import http from 'node:http';

import makeWASocket, {
  Browsers,
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
} from '@whiskeysockets/baileys';
import pino from 'pino';

import { usePostgresAuthState } from './auth.js';
import { config as cfg } from './config.js';
import { hifadhi, tengenezaPool } from './db.js';
import { chambuaKikomo, chambuaTimelock, nambaKutokaJid, niOmbiLaKujitoa, sleep } from './kinga.js';
import { Mtumaji } from './mtumaji.js';

const log = pino({ level: cfg.logLevel });
const baileysLog = pino({ level: 'warn' });

if (!cfg.databaseUrl) {
  log.fatal('Weka DATABASE_URL (ileile ya mfumo wa Django).');
  process.exit(1);
}

const pool = tengenezaPool(cfg);
const db = hifadhi(pool);
const mtumaji = new Mtumaji({ db, cfg, log });
let sock = null;
let kuzima = false;
let majaribioYaKuunganisha = 0;
let hali = 'haijaanza';
let inaanzaUpya = false; // tunabadilisha namba: close handler isiunganishe yenyewe
let pairingNamba = cfg.pairingNamba;

// ---------- Kufuli: worker moja tu kwa wakati ----------
async function pataKufuli() {
  const client = await pool.connect();
  for (;;) {
    const r = await client.query('SELECT pg_try_advisory_lock(8248001) AS ok');
    if (r.rows[0].ok) {
      log.info('Kufuli limepatikana; worker hii ndiyo itakayotuma.');
      return client;
    }
    log.info('Worker nyingine inatumia session. Nasubiri...');
    await sleep(15000);
  }
}

// ---------- Kikomo cha WhatsApp ----------
async function kaguaKikomo() {
  if (!sock || hali !== 'imeunganishwa') return;
  try {
    const info = await sock.fetchNewChatMessageCap();
    const k = chambuaKikomo(info);
    await db.wekaHali({ kikomo_cha_whatsapp: k.muhtasari || 'hakuna onyo' });
    if (k.simama) {
      log.warn(k.sababu);
      await db.simamisha(k.mpaka, k.sababu);
    }
  } catch (e) {
    log.debug({ err: e?.message }, 'Kikomo hakikupatikana (si akaunti zote zinakionyesha)');
  }
  try {
    const t = chambuaTimelock(await sock.fetchAccountReachoutTimelock());
    if (t.simama) {
      log.warn(t.sababu);
      await db.simamisha(t.mpaka, t.sababu);
    }
  } catch (e) {
    log.debug({ err: e?.message }, 'Timelock haikupatikana');
  }
}

// ---------- Muunganisho ----------
function zimaSocket() {
  // Ondoa listeners zote kwanza: socket ya zamani isiandike tena session (creds.update) baada ya kufutwa
  try {
    for (const e of ['creds.update', 'connection.update', 'messages.update', 'messages.upsert', 'message-capping.update']) {
      sock?.ev?.removeAllListeners(e);
    }
  } catch {}
  try {
    sock?.end(undefined);
  } catch {}
  mtumaji.wekaSocket(null, false);
}

async function anzaUpya(namba) {
  inaanzaUpya = true;
  try {
    log.info({ pairing: Boolean(namba) }, 'Inaondoa namba ya zamani na kuanza upya');
    zimaSocket();
    await pool.query('DELETE FROM wa_auth');
    pairingNamba = (namba || '').replace(/\D/g, '') || cfg.pairingNamba;
    hali = 'inaunganisha';
    await db.wekaHali({ hali, qr: '', namba: '', taarifa: 'Inaandaa muunganisho mpya' });
    await db.kamilishaAnzaUpya();
    majaribioYaKuunganisha = 0;
    await sleep(1500);
    await unganisha();
  } finally {
    inaanzaUpya = false;
  }
}

async function unganisha() {
  const auth = await usePostgresAuthState(pool);
  let version;
  try {
    ({ version } = await fetchLatestBaileysVersion());
  } catch {
    version = undefined; // Baileys itatumia toleo lake
  }
  let codeImeombwa = false;

  sock = makeWASocket({
    version,
    auth: { creds: auth.state.creds, keys: makeCacheableSignalKeyStore(auth.state.keys, baileysLog) },
    logger: baileysLog,
    browser: Browsers.ubuntu('Chrome'),
    markOnlineOnConnect: false, // simu iendelee kupata notifications kama kawaida
    // Historia kamili haihitajiki, lakini usawazishaji wa mwanzo usizimwe: Baileys
    // inauhitaji kupata "LID mappings", vinginevyo session inayumba.
    syncFullHistory: false,
    generateHighQualityLinkPreview: false,
    getMessage: async (key) => mtumaji.zilizotumwa.get(key.id),
  });
  mtumaji.wekaSocket(sock, false);

  sock.ev.on('creds.update', auth.saveCreds);

  sock.ev.on('connection.update', async (u) => {
    try {
      if (u.qr) {
        if (pairingNamba && !auth.state.creds.registered) {
          if (!codeImeombwa) {
            codeImeombwa = true;
            const code = await sock.requestPairingCode(pairingNamba);
            hali = 'inasubiri_qr';
            await db.wekaHali({ hali, qr: `CODE:${code}`, taarifa: 'Andika code hii kwenye simu' });
          }
        } else {
          hali = 'inasubiri_qr';
          await db.wekaHali({ hali, qr: u.qr, taarifa: 'Scan QR kwa simu yenye namba ya kutuma' });
        }
      }
      if (u.connection === 'connecting' && hali !== 'inasubiri_qr') {
        hali = 'inaunganisha';
        await db.wekaHali({ hali });
      }
      if (u.connection === 'open') {
        majaribioYaKuunganisha = 0;
        hali = 'imeunganishwa';
        mtumaji.wekaSocket(sock, true);
        const namba = (sock.user?.id || '').split(':')[0].split('@')[0];
        await db.wekaHali({ hali, qr: '', namba: namba ? `+${namba}` : '', taarifa: 'Imeunganishwa' });
        log.info({ namba }, 'WhatsApp imeunganishwa');
        setTimeout(kaguaKikomo, 20000);
      }
      if (u.connection === 'close') {
        mtumaji.wekaSocket(sock, false);
        const code = u.lastDisconnect?.error?.output?.statusCode;
        log.warn({ code }, 'Muunganisho umefungwa');
        if (kuzima || inaanzaUpya) return;
        if (code === DisconnectReason.loggedOut) {
          hali = 'imeondolewa';
          await auth.futa();
          await db.wekaHali({ hali, qr: '', namba: '', taarifa: 'Kifaa kiliondolewa kwenye simu. Scan QR mpya.' });
          await sleep(5000);
        } else if (code === DisconnectReason.connectionReplaced) {
          await db.wekaHali({ taarifa: 'Session imefunguliwa mahali pengine. Nasubiri dakika 2.' });
          await sleep(120000);
        } else {
          majaribioYaKuunganisha += 1;
          const subiri = Math.min(2000 * 2 ** majaribioYaKuunganisha, 120000);
          await db.wekaHali({ taarifa: `Inaunganisha upya baada ya sekunde ${Math.round(subiri / 1000)} (code ${code ?? '?'})` });
          await sleep(subiri);
        }
        if (!kuzima && !inaanzaUpya) {
          zimaSocket();
          unganisha().catch((e) => log.error(e, 'Kuunganisha upya kumeshindwa'));
        }
      }
    } catch (e) {
      log.error(e, 'Kosa kwenye connection.update');
    }
  });

  // Risiti: imefika / imesomwa
  sock.ev.on('messages.update', async (updates) => {
    for (const { key, update } of updates) {
      if (!key?.fromMe || update?.status == null) continue;
      const hali = update.status >= 4 ? 'umesomwa' : update.status === 3 ? 'umefika' : null;
      if (hali) await db.risiti(key.id, hali).catch((e) => log.warn(e, 'Risiti haikuhifadhiwa'));
    }
  });

  // Majibu: anayejibu ACHA hatumiwi tena
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const m of messages) {
      if (m.key?.fromMe) continue;
      const text = m.message?.conversation || m.message?.extendedTextMessage?.text || '';
      if (!niOmbiLaKujitoa(text)) continue;
      let namba = nambaKutokaJid(m.key.remoteJid, m.key.remoteJidAlt, m.key.senderPn, m.key.participantAlt);
      if (!namba && m.key.remoteJid?.endsWith('@lid')) {
        const pn = await sock.signalRepository?.lidMapping?.getPNForLID?.(m.key.remoteJid).catch(() => null);
        namba = nambaKutokaJid(pn);
      }
      if (!namba) continue;
      const n = await db.jitoa(namba);
      log.info({ n }, 'Mgeni ameomba kusitisha ujumbe');
      if (n > 0) {
        await sleep(3000 + Math.random() * 4000);
        await sock
          .sendMessage(m.key.remoteJid, { text: 'Sawa, hutapokea vikumbusho zaidi kuhusu michango. Asante sana.' })
          .catch(() => {});
      }
    }
  });

  sock.ev.on('message-capping.update', async (info) => {
    const k = chambuaKikomo(info);
    await db.wekaHali({ kikomo_cha_whatsapp: k.muhtasari || 'hakuna onyo' }).catch(() => {});
    if (k.simama) await db.simamisha(k.mpaka, k.sababu).catch(() => {});
  });
}

// ---------- Mzunguko wa kutuma ----------
async function zunguka() {
  while (!kuzima) {
    let subiri = 15000;
    try {
      ({ subiri } = await mtumaji.hatua());
    } catch (e) {
      log.error(e, 'Kosa kwenye mzunguko wa kutuma');
      subiri = 30000;
    }
    await sleep(subiri);
  }
}

// ---------- Health check (kwa Render) ----------
function anzishaHealth() {
  if (!cfg.port) return;
  http
    .createServer(async (req, res) => {
      let foleni = null;
      try {
        foleni = await db.foleni();
      } catch {}
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ hali, foleni }));
    })
    .listen(cfg.port, () => log.info({ port: cfg.port }, 'Health check iko hewani'));
}

async function main() {
  anzishaHealth();
  await db.hakikishaHali();
  const kufuli = await pataKufuli();
  await db.wekaHali({ hali: 'inaunganisha', taarifa: 'Worker imeanza' });
  setInterval(() => db.pigo().catch(() => {}), 30000);
  db.pigo().catch(() => {});
  setInterval(kaguaKikomo, 20 * 60 * 1000);
  // Msimamizi akibofya "Unganisha namba nyingine" kwenye mfumo
  setInterval(async () => {
    if (inaanzaUpya || kuzima) return;
    try {
      const h = await db.soma();
      if (h.anza_upya) await anzaUpya(h.pairing_namba);
    } catch (e) {
      log.error(e, 'Kuanza upya kumeshindwa');
    }
  }, 5000);
  await unganisha();
  zunguka();

  const zima = async (sig) => {
    if (kuzima) return;
    kuzima = true;
    log.info({ sig }, 'Inazima kwa usalama');
    try {
      sock?.end(undefined); // si logout: session ibaki
    } catch {}
    await db.wekaHali({ hali: 'haijaanza', taarifa: 'Worker imezimwa' }).catch(() => {});
    kufuli.release();
    await pool.end().catch(() => {});
    process.exit(0);
  };
  process.on('SIGTERM', () => zima('SIGTERM'));
  process.on('SIGINT', () => zima('SIGINT'));
}

main().catch((e) => {
  log.fatal(e, 'Worker imeshindwa kuanza');
  process.exit(1);
});
