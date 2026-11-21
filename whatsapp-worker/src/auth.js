// Session ya Baileys ndani ya Postgres (jedwali wa_auth), badala ya mafaili.
// Hii ina maana session haipotei server ikizimwa au ku-deploy upya, hivyo
// hakuna haja ya kuscan QR tena na tena (kuunganisha mara nyingi ni dalili mbaya).
import { BufferJSON, initAuthCreds, proto } from '@whiskeysockets/baileys';

export async function usePostgresAuthState(pool) {
  const soma = async (jina) => {
    const r = await pool.query('SELECT data FROM wa_auth WHERE jina = $1', [jina]);
    return r.rows[0] ? JSON.parse(r.rows[0].data, BufferJSON.reviver) : null;
  };
  const andika = async (client, jina, value) => {
    await client.query(
      'INSERT INTO wa_auth (jina, data) VALUES ($1, $2) ON CONFLICT (jina) DO UPDATE SET data = EXCLUDED.data',
      [jina, JSON.stringify(value, BufferJSON.replacer)],
    );
  };

  const creds = (await soma('creds')) || initAuthCreds();

  return {
    state: {
      creds,
      keys: {
        get: async (type, ids) => {
          const majina = ids.map((id) => `${type}-${id}`);
          const r = await pool.query('SELECT jina, data FROM wa_auth WHERE jina = ANY($1)', [majina]);
          const map = new Map(r.rows.map((row) => [row.jina, row.data]));
          const data = {};
          for (const id of ids) {
            const raw = map.get(`${type}-${id}`);
            let value = raw ? JSON.parse(raw, BufferJSON.reviver) : null;
            if (type === 'app-state-sync-key' && value) {
              value = proto.Message.AppStateSyncKeyData.fromObject(value);
            }
            data[id] = value;
          }
          return data;
        },
        set: async (data) => {
          const client = await pool.connect();
          try {
            await client.query('BEGIN');
            for (const category in data) {
              for (const id in data[category]) {
                const value = data[category][id];
                const jina = `${category}-${id}`;
                if (value) await andika(client, jina, value);
                else await client.query('DELETE FROM wa_auth WHERE jina = $1', [jina]);
              }
            }
            await client.query('COMMIT');
          } catch (e) {
            await client.query('ROLLBACK').catch(() => {});
            throw e;
          } finally {
            client.release();
          }
        },
      },
    },
    saveCreds: async () => andika(pool, 'creds', creds),
    /** Futa session yote (baada ya kifaa kuondolewa kwenye simu). */
    futa: async () => pool.query('DELETE FROM wa_auth'),
  };
}
