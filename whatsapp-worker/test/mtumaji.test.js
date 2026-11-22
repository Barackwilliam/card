// Mzunguko wa kutuma dhidi ya Postgres halisi (majedwali ya Django) na WhatsApp ya kuigiza.
// Inahitaji TEST_DATABASE_URL ya database iliyo na migrations za Django.
import assert from 'node:assert/strict';
import test from 'node:test';

import { initAuthCreds } from '@whiskeysockets/baileys';

import { usePostgresAuthState } from '../src/auth.js';
import { hifadhi, tengenezaPool } from '../src/db.js';
import { Mtumaji } from '../src/mtumaji.js';

const url = process.env.TEST_DATABASE_URL;
const skip = !url && 'TEST_DATABASE_URL haijawekwa';
const cfg = {
  databaseUrl: url, dbSsl: false, timezone: 'Africa/Dar_es_Salaam', saaKuanza: 8, saaMwisho: 20,
  kikomoKwaSaa: 30, kikomoKwaSiku: 150, kusubiriMin: 40, kusubiriMax: 90, pumzikoKila: 8,
  pumzikoMin: 240, pumzikoMax: 480, makosaMfululizo: 3, simamaDakika: 60, umriKikumbushoSaa: 12, majaribioMax: 3,
};
const SAA_TISA = new Date('2026-11-25T06:00:00Z'); // 09:00 Tanzania
const log = { info() {}, warn() {}, error() {}, debug() {} };

function socketYaKuigiza({ wasio = [], kosa = null } = {}) {
  const s = { zilizotumwa: [], presence: [] };
  s.onWhatsApp = async (n) => [{ jid: `${n}@s.whatsapp.net`, exists: !wasio.includes(n) }];
  s.sendPresenceUpdate = async (p, jid) => s.presence.push(p);
  s.sendMessage = async (jid, content) => {
    if (kosa) throw kosa;
    s.zilizotumwa.push({ jid, content });
    return { key: { id: `WA${s.zilizotumwa.length}` }, message: {} };
  };
  return s;
}

async function andaa(pool) {
  await pool.query('TRUNCATE michango_ujumbe, michango_mchango, michango_mgeni, michango_harusi, wa_hali, wa_auth RESTART IDENTITY CASCADE');
  await pool.query(`INSERT INTO michango_harusi (jina, mwenye_harusi, familia, tarehe_mwisho, maelekezo_malipo, kadi_template,
      jina_x, jina_y, jina_ukubwa, jina_upana_max, jina_rangi, jina_fonti, vikumbusho_vimewashwa, vikumbusho_kwa_siku,
      vikumbusho_jumla_max, shukrani_zimewashwa, ujumbe_kadi, ujumbe_kikumbusho, ujumbe_salio, ujumbe_shukrani, created)
    VALUES ('H', 'R', '', '2026-11-30', 'M-Pesa', 't.jpg', .5, .45, 50, .7, '#000000', 'GreatVibes-Regular.ttf', true, 1, 4, true, '', '', '', '', now())`);
  const mgeni = async (jina, simu, amejitoa = false) =>
    (await pool.query(`INSERT INTO michango_mgeni (harusi_id, jina, simu, kadi, amejitoa, maelezo, created)
       VALUES (1, $1, $2, '', $3, '', now()) RETURNING id`, [jina, simu, amejitoa])).rows[0].id;
  const ujumbe = async (mgeniId, aina, { picha = '', created = new Date(SAA_TISA.getTime() - 60000) } = {}) =>
    (await pool.query(`INSERT INTO michango_ujumbe (mgeni_id, aina, hali, wa_id, kosa, simu, maandishi, picha_url, majaribio, haraka, created, updated)
       SELECT $1, $2, 'kwenye_foleni', '', '', simu, 'Habari ' || jina, $3, 0, false, $4, now() FROM michango_mgeni WHERE id = $1 RETURNING id`,
       [mgeniId, aina, picha, created])).rows[0].id;
  await hifadhi(pool).hakikishaHali();
  return { mgeni, ujumbe };
}

const hali = async (pool, id) => (await pool.query('SELECT hali, kosa, wa_id, majaribio FROM michango_ujumbe WHERE id = $1', [id])).rows[0];

test('mzunguko wa kutuma na kinga', { skip }, async (t) => {
  const pool = tengenezaPool(cfg);
  t.after(() => pool.end());
  const db = hifadhi(pool);
  const { mgeni, ujumbe } = await andaa(pool);

  const a = await mgeni('Asha', '255711000001');
  const b = await mgeni('Baraka', '255711000002', true);
  const c = await mgeni('Chausiku', '255711000003');
  const d = await mgeni('Daudi', '255711000004');
  const kadiA = await ujumbe(a, 'kadi', { picha: 'https://example.test/kadi.jpg' });
  const kikB = await ujumbe(b, 'kikumbusho');
  const kikC = await ujumbe(c, 'kikumbusho', { created: new Date(SAA_TISA.getTime() - 13 * 3600 * 1000) });
  const kikD = await ujumbe(d, 'kikumbusho');

  const sock = socketYaKuigiza({ wasio: ['255711000004'] });
  let sasa = SAA_TISA;
  const m = new Mtumaji({ db, cfg, log, sleep: async () => {}, sasa: () => sasa, pakua: async () => Buffer.from('jpg'), rnd: () => 0 });

  assert.equal((await m.hatua()).sababu, 'haijaunganishwa');
  m.wekaSocket(sock, true);

  // Usiku: hakuna kinachotumwa, isipokuwa jaribio la haraka
  sasa = new Date('2026-11-25T18:00:00Z');
  assert.equal((await m.hatua()).sababu, 'nje_ya_saa');
  const harakaMgeni = await mgeni('Haraka', '255711000009');
  const haraka = await ujumbe(harakaMgeni, 'kadi');
  await pool.query('UPDATE michango_ujumbe SET haraka = true WHERE id = $1', [haraka]);
  assert.equal((await m.hatua()).sababu, 'imetumwa'); // usiku, kwa sababu ni jaribio
  assert.equal((await hali(pool, haraka)).hali, 'umetumwa');
  assert.equal(sock.zilizotumwa[0].content.text, 'Habari Haraka');
  assert.equal((await m.hatua()).sababu, 'nje_ya_saa'); // kadiA bado inasubiri asubuhi
  assert.equal((await hali(pool, kadiA)).hali, 'kwenye_foleni');
  sock.zilizotumwa.length = 0;
  sock.presence.length = 0;
  sasa = SAA_TISA;

  // Kadi inatumwa kwanza, na picha + "anaandika"
  const r1 = await m.hatua();
  assert.equal(r1.sababu, 'imetumwa');
  assert.equal(r1.subiri, 40000);
  assert.deepEqual(sock.presence, ['composing', 'paused']);
  assert.ok(sock.zilizotumwa[0].content.image);
  assert.equal(sock.zilizotumwa[0].content.caption, 'Habari Asha');
  assert.equal((await hali(pool, kadiA)).hali, 'umetumwa');
  const kadiImetumwa = (await pool.query('SELECT kadi_imetumwa FROM michango_mgeni WHERE id = $1', [a])).rows[0].kadi_imetumwa;
  assert.ok(kadiImetumwa);

  // Vikumbusho vinachukuliwa kwa mpangilio wa muda: cha zamani (masaa 13) kwanza
  assert.equal((await m.hatua()).sababu, 'muda_umepita');
  assert.equal((await hali(pool, kikC)).hali, 'imeghairiwa');
  assert.equal((await m.hatua()).sababu, 'amejitoa');
  assert.equal((await hali(pool, kikB)).hali, 'imeghairiwa');
  assert.equal((await m.hatua()).sababu, 'haipo_whatsapp');
  assert.equal((await hali(pool, kikD)).hali, 'umeshindwa');
  assert.equal((await m.hatua()).sababu, 'foleni_tupu');
  assert.equal(sock.zilizotumwa.length, 1);

  // Risiti
  await db.risiti('WA1', 'umefika');
  assert.equal((await hali(pool, kadiA)).hali, 'umefika');
  await db.risiti('WA1', 'umesomwa');
  await db.risiti('WA1', 'umefika'); // haishuki
  assert.equal((await hali(pool, kadiA)).hali, 'umesomwa');

  // Msimamizi akisitisha
  await ujumbe(a, 'shukrani');
  await db.wekaHali({ imesitishwa: true });
  assert.equal((await m.hatua()).sababu, 'imesitishwa');
  await db.wekaHali({ imesitishwa: false });

  // Kikomo kilichowekwa kwenye ukurasa wa WhatsApp kinashinda kikubwa cha worker
  await db.wekaHali({ kikomo_saa: 1 });
  const m3 = new Mtumaji({ db, cfg, log, sleep: async () => {}, sasa: () => SAA_TISA, rnd: () => 0 });
  m3.wekaSocket(sock, true);
  assert.equal((await m3.hatua()).sababu, 'kikomo_saa');
  await db.wekaHali({ kikomo_saa: 15 });

  // Kikomo cha saa
  const kikomo = { ...cfg, kikomoKwaSaa: 1 };
  const m2 = new Mtumaji({ db, cfg: kikomo, log, sleep: async () => {}, sasa: () => SAA_TISA, rnd: () => 0 });
  m2.wekaSocket(sock, true);
  assert.equal((await m2.hatua()).sababu, 'kikomo_saa');
});

test('makosa mfululizo yanasimamisha, kikomo cha WhatsApp kinasimamisha saa 2', { skip }, async (t) => {
  const pool = tengenezaPool(cfg);
  t.after(() => pool.end());
  const db = hifadhi(pool);
  const { mgeni, ujumbe } = await andaa(pool);
  const ids = [];
  for (let i = 1; i <= 3; i++) ids.push(await ujumbe(await mgeni(`M${i}`, `25571100001${i}`), 'kikumbusho'));

  const sock = socketYaKuigiza({ kosa: new Error('media upload failed') });
  const m = new Mtumaji({ db, cfg, log, sleep: async () => {}, sasa: () => SAA_TISA, rnd: () => 0 });
  m.wekaSocket(sock, true);
  for (let i = 0; i < 3; i++) assert.equal((await m.hatua()).sababu, 'kosa');
  const h = await db.soma();
  assert.ok(new Date(h.imesimamishwa_mpaka) > SAA_TISA);
  assert.equal((await m.hatua()).sababu, 'kinga');
  // Ujumbe wa kwanza umejaribiwa mara 3 -> umeshindwa
  assert.equal((await hali(pool, ids[0])).hali, 'umeshindwa');

  await db.wekaHali({ imesimamishwa_mpaka: null });
  const m2 = new Mtumaji({ db, cfg, log, sleep: async () => {}, sasa: () => SAA_TISA, rnd: () => 0 });
  m2.wekaSocket(socketYaKuigiza({ kosa: new Error('rate-overlimit') }), true);
  assert.equal((await m2.hatua()).sababu, 'kikomo_whatsapp');
  const h2 = await db.soma();
  assert.ok(new Date(h2.imesimamishwa_mpaka).getTime() >= SAA_TISA.getTime() + 119 * 60000);

  // Kujitoa kunaghairi foleni yake
  await db.wekaHali({ imesimamishwa_mpaka: null });
  assert.equal(await db.jitoa('255711000013'), 1);
  assert.equal((await hali(pool, ids[2])).hali, 'imeghairiwa');
});

test('session ya WhatsApp inahifadhiwa Postgres', { skip }, async (t) => {
  const pool = tengenezaPool(cfg);
  t.after(() => pool.end());
  await pool.query('TRUNCATE wa_auth');
  const a1 = await usePostgresAuthState(pool);
  a1.state.creds.me = { id: '255711000001:5@s.whatsapp.net' };
  await a1.saveCreds();
  await a1.state.keys.set({ 'pre-key': { 1: { public: Buffer.from([1, 2, 3]), private: Buffer.from([4]) }, 2: null } });
  const a2 = await usePostgresAuthState(pool);
  assert.equal(a2.state.creds.me.id, '255711000001:5@s.whatsapp.net');
  assert.deepEqual(Buffer.from(a2.state.creds.noiseKey.public), Buffer.from(a1.state.creds.noiseKey.public));
  const k = await a2.state.keys.get('pre-key', ['1', '2']);
  assert.deepEqual([...k['1'].public], [1, 2, 3]);
  assert.equal(k['2'], null);
  await a2.state.keys.set({ 'pre-key': { 1: null } });
  assert.equal((await a2.state.keys.get('pre-key', ['1']))['1'], null);
  await a2.futa();
  assert.equal((await pool.query('SELECT count(*) FROM wa_auth')).rows[0].count, '0');
  assert.ok(initAuthCreds().noiseKey); // creds mpya zinatengenezwa bila session
});
