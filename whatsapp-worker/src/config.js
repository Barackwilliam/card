// Mipangilio ya worker. Thamani zote zinaweza kubadilishwa kwa environment variables.
// Chaguo-msingi zimewekwa kwa tahadhari: ni bora kutuma polepole kuliko namba kufungiwa.

const num = (name, def) => {
  const v = process.env[name];
  const n = v === undefined || v === '' ? def : Number(v);
  if (Number.isNaN(n)) throw new Error(`${name} lazima iwe namba`);
  return n;
};

export const config = {
  databaseUrl: process.env.DATABASE_URL,
  dbSsl: !['0', 'false', 'no'].includes(String(process.env.DB_SSL_REQUIRE ?? '1').toLowerCase()),
  timezone: 'Africa/Dar_es_Salaam',

  // Saa za kutuma (saa za Tanzania): 08:00 - 20:00
  saaKuanza: num('WA_SAA_KUANZA', 8),
  saaMwisho: num('WA_SAA_MWISHO', 20),

  // Vikomo vya idadi
  kikomoKwaSaa: num('WA_KIKOMO_SAA', 30),
  kikomoKwaSiku: num('WA_KIKOMO_SIKU', 150),

  // Muda wa kusubiri kati ya ujumbe mmoja na mwingine (sekunde, kwa bahati nasibu)
  kusubiriMin: num('WA_KUSUBIRI_MIN', 40),
  kusubiriMax: num('WA_KUSUBIRI_MAX', 90),

  // Pumziko refu baada ya kila jumbe N
  pumzikoKila: num('WA_PUMZIKO_KILA', 8),
  pumzikoMin: num('WA_PUMZIKO_MIN', 240),
  pumzikoMax: num('WA_PUMZIKO_MAX', 480),

  // Kinga ya makosa mfululizo
  makosaMfululizo: num('WA_MAKOSA_MFULULIZO', 3),
  simamaDakika: num('WA_SIMAMA_DAKIKA', 60),

  // Kikumbusho kilichokaa foleni muda mrefu (mfano worker ilikuwa imezimwa) hakitumwi
  umriKikumbushoSaa: num('WA_UMRI_KIKUMBUSHO_SAA', 12),

  // Ujumbe ukishindwa mara hizi, unaachwa
  majaribioMax: num('WA_MAJARIBIO_MAX', 3),

  // Hiari: namba (mfano 255754123456) ili kuunganisha kwa "pairing code" badala ya QR
  pairingNamba: (process.env.WA_NAMBA_PAIRING || '').replace(/\D/g, ''),

  port: process.env.PORT ? Number(process.env.PORT) : null,
  logLevel: process.env.LOG_LEVEL || 'info',
};
