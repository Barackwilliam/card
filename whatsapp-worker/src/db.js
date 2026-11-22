// Mawasiliano na database ya mfumo (majedwali yanatengenezwa na Django).
import pg from 'pg';

export function tengenezaPool(cfg) {
  return new pg.Pool({
    connectionString: cfg.databaseUrl,
    ssl: cfg.dbSsl ? { rejectUnauthorized: false } : false,
    max: 4,
    idleTimeoutMillis: 30000,
  });
}

const TZ = 'Africa/Dar_es_Salaam';

export function hifadhi(pool) {
  return {
    async hakikishaHali() {
      await pool.query(
        `INSERT INTO wa_hali (id, hali, qr, namba, taarifa, imesitishwa, sababu_ya_kusimama, kikomo_cha_whatsapp,
           anza_upya, pairing_namba, kikomo_siku, kikomo_saa, updated)
         VALUES (1, 'haijaanza', '', '', '', false, '', '', false, '', 40, 15, now()) ON CONFLICT (id) DO NOTHING`,
      );
    },

    async wekaHali(fields) {
      const keys = Object.keys(fields);
      if (!keys.length) return;
      const sets = keys.map((k, i) => `${k} = $${i + 1}`).join(', ');
      await pool.query(`UPDATE wa_hali SET ${sets}, updated = now() WHERE id = 1`, keys.map((k) => fields[k]));
    },

    async pigo() {
      await pool.query('UPDATE wa_hali SET mapigo = now() WHERE id = 1');
    },

    async soma() {
      const r = await pool.query(
        'SELECT imesitishwa, imesimamishwa_mpaka, anza_upya, pairing_namba, kikomo_siku, kikomo_saa FROM wa_hali WHERE id = 1',
      );
      return r.rows[0] || { imesitishwa: false, imesimamishwa_mpaka: null, anza_upya: false, pairing_namba: '' };
    },

    async kamilishaAnzaUpya() {
      await pool.query('UPDATE wa_hali SET anza_upya = false, updated = now() WHERE id = 1');
    },

    async simamisha(mpaka, sababu) {
      await pool.query(
        'UPDATE wa_hali SET imesimamishwa_mpaka = $1, sababu_ya_kusimama = $2, updated = now() WHERE id = 1',
        [mpaka, sababu],
      );
    },

    async idadiZilizotumwa() {
      const r = await pool.query(
        `SELECT
           count(*) FILTER (WHERE umetumwa_at > now() - interval '1 hour') AS saa,
           count(*) FILTER (WHERE umetumwa_at >= (date_trunc('day', now() AT TIME ZONE '${TZ}') AT TIME ZONE '${TZ}')) AS siku
         FROM michango_ujumbe WHERE umetumwa_at IS NOT NULL`,
      );
      return { saa: Number(r.rows[0].saa), siku: Number(r.rows[0].siku) };
    },

    /** Ujumbe unaofuata. harakaPekee: majaribio ya haraka tu (kwa nje ya saa za kutuma). */
    async unaofuata({ harakaPekee = false } = {}) {
      const r = await pool.query(
        `SELECT u.id, u.aina, u.simu, u.maandishi, u.picha_url, u.majaribio, u.created, u.mgeni_id, u.haraka, m.amejitoa
         FROM michango_ujumbe u JOIN michango_mgeni m ON m.id = u.mgeni_id
         WHERE u.hali = 'kwenye_foleni' ${harakaPekee ? 'AND u.haraka' : ''}
         ORDER BY u.haraka DESC, CASE u.aina WHEN 'shukrani' THEN 0 WHEN 'kadi' THEN 1 ELSE 2 END, u.created
         LIMIT 1`,
      );
      return r.rows[0] || null;
    },

    async umetumwa(id, waId, aina, mgeniId) {
      await pool.query(
        `UPDATE michango_ujumbe SET hali = 'umetumwa', wa_id = $2, kosa = '', umetumwa_at = now(), updated = now() WHERE id = $1`,
        [id, waId || ''],
      );
      if (aina === 'kadi') {
        await pool.query('UPDATE michango_mgeni SET kadi_imetumwa = now() WHERE id = $1 AND kadi_imetumwa IS NULL', [mgeniId]);
      }
    },

    async ghairi(id, sababu) {
      await pool.query(`UPDATE michango_ujumbe SET hali = 'imeghairiwa', kosa = $2, updated = now() WHERE id = $1`, [id, sababu]);
    },

    async shindwa(id, kosa) {
      await pool.query(`UPDATE michango_ujumbe SET hali = 'umeshindwa', kosa = $2, updated = now() WHERE id = $1`, [id, kosa]);
    },

    async jaribioLimeshindwa(id, kosa, max) {
      const r = await pool.query(
        `UPDATE michango_ujumbe SET majaribio = majaribio + 1, kosa = $2, updated = now(),
           hali = CASE WHEN majaribio + 1 >= $3 THEN 'umeshindwa' ELSE hali END
         WHERE id = $1 RETURNING hali`,
        [id, kosa.slice(0, 500), max],
      );
      return r.rows[0]?.hali;
    },

    async risiti(waId, hali) {
      // Usishushe hali (mfano kutoka "umesomwa" kurudi "umefika")
      const ruhusiwa = hali === 'umesomwa' ? ['umetumwa', 'umefika'] : ['umetumwa'];
      await pool.query(
        'UPDATE michango_ujumbe SET hali = $1, updated = now() WHERE wa_id = $2 AND hali = ANY($3)',
        [hali, waId, ruhusiwa],
      );
    },

    async jitoa(simu) {
      const r = await pool.query('UPDATE michango_mgeni SET amejitoa = true WHERE simu = $1 AND amejitoa = false', [simu]);
      await pool.query(
        `UPDATE michango_ujumbe SET hali = 'imeghairiwa', kosa = 'Ameomba asitumiwe', updated = now()
         WHERE hali = 'kwenye_foleni' AND mgeni_id IN (SELECT id FROM michango_mgeni WHERE simu = $1)`,
        [simu],
      );
      return r.rowCount;
    },

    async foleni() {
      const r = await pool.query(`SELECT count(*) AS n FROM michango_ujumbe WHERE hali = 'kwenye_foleni'`);
      return Number(r.rows[0].n);
    },
  };
}
