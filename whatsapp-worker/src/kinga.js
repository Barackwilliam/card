// Kinga dhidi ya kufungiwa: maamuzi yote ya "tutume sasa au tusubiri" yako hapa
// kama functions safi (pure) ili ziweze kujaribiwa bila WhatsApp.

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export const bahati = (min, max, rnd = Math.random) => min + rnd() * (max - min);

/** Saa ya sasa (0-23) katika time zone iliyotolewa. */
export function saaYaEneo(date, timeZone) {
  const h = new Intl.DateTimeFormat('en-GB', { timeZone, hour: 'numeric', hour12: false }).format(date);
  return Number(h) % 24;
}

export function ndaniYaSaaZaKutuma(date, cfg) {
  const h = saaYaEneo(date, cfg.timezone);
  return h >= cfg.saaKuanza && h < cfg.saaMwisho;
}

/** Muda wa kusubiri baada ya ujumbe wa n (1-based), kwa milisekunde. */
export function mudaWaKusubiri(n, cfg, rnd = Math.random) {
  if (cfg.pumzikoKila > 0 && n % cfg.pumzikoKila === 0) {
    return Math.round(bahati(cfg.pumzikoMin, cfg.pumzikoMax, rnd) * 1000);
  }
  return Math.round(bahati(cfg.kusubiriMin, cfg.kusubiriMax, rnd) * 1000);
}

/** Muda wa "anaandika..." kulingana na urefu wa ujumbe (sekunde 2-7). */
export function mudaWaKuandika(maandishi, rnd = Math.random) {
  const base = 2000 + Math.min((maandishi || '').length * 25, 4000);
  return Math.round(base + rnd() * 1000);
}

/**
 * Soma taarifa ya kikomo kutoka WhatsApp (fetchNewChatMessageCap) na uamue kama tusimame.
 * Hurudisha { simama: bool, mpaka: Date|null, sababu: string, muhtasari: string }.
 */
export function chambuaKikomo(info, sasa = new Date()) {
  if (!info || typeof info !== 'object') return { simama: false, mpaka: null, sababu: '', muhtasari: '' };
  const status = info.capping_status;
  const total = Number(info.total_quota);
  const used = Number(info.used_quota);
  const mwisho = info.cycle_end_timestamp ? new Date(Number(info.cycle_end_timestamp) * (String(info.cycle_end_timestamp).length <= 10 ? 1000 : 1)) : null;
  const mpaka = mwisho && mwisho > sasa ? mwisho : new Date(sasa.getTime() + 24 * 3600 * 1000);
  const parts = [];
  if (status) parts.push(`hali ${status}`);
  if (Number.isFinite(total) && total > 0) parts.push(`watu wapya ${Number.isFinite(used) ? used : '?'}/${total}`);
  const muhtasari = parts.join(', ');

  if (status && status !== 'NONE') {
    return { simama: true, mpaka, sababu: `WhatsApp imetoa onyo la kikomo (${status}). Tunasimama ili kulinda namba.`, muhtasari };
  }
  if (Number.isFinite(total) && total > 0 && Number.isFinite(used) && used >= total - 5) {
    return { simama: true, mpaka, sababu: `Kikomo cha WhatsApp cha watu wapya kimekaribia kujaa (${used}/${total}).`, muhtasari };
  }
  return { simama: false, mpaka: null, sababu: '', muhtasari };
}

/** Kizuizi cha muda (reachout timelock) kutoka fetchAccountReachoutTimelock. */
export function chambuaTimelock(t, sasa = new Date()) {
  if (!t || !t.isActive) return { simama: false };
  const ends = t.timeEnforcementEnds ? new Date(t.timeEnforcementEnds) : null;
  return {
    simama: true,
    mpaka: ends && ends > sasa ? ends : new Date(sasa.getTime() + 24 * 3600 * 1000),
    sababu: `WhatsApp imeweka kizuizi cha kuwasiliana na watu wapya (${t.enforcementType || 'haijulikani'}).`,
  };
}

/** Kosa la kutuma: je, ni dalili ya kikomo (tusimame muda mrefu)? */
export function niKosaLaKikomo(err) {
  const s = `${err?.message || ''} ${err?.data?.toString?.() || ''} ${err?.output?.statusCode || ''}`.toLowerCase();
  return s.includes('rate-overlimit') || s.includes('429') || s.includes('too many');
}

/** Kosa la muunganisho (ujumbe ubaki foleni bila kuhesabiwa kama kosa). */
export function niKosaLaMuunganisho(err) {
  const s = `${err?.message || ''}`.toLowerCase();
  return s.includes('connection closed') || s.includes('connection lost') || s.includes('timed out') || s.includes('not open');
}

export const MANENO_YA_KUJITOA = new Set(['acha', 'stop', 'sitaki', 'unsubscribe', 'ondoa']);

export function niOmbiLaKujitoa(text) {
  return MANENO_YA_KUJITOA.has(String(text || '').trim().toLowerCase().replace(/[.!]+$/, ''));
}

/** Pata namba (tarakimu tu) kutoka JIDs za ujumbe unaoingia. */
export function nambaKutokaJid(...jids) {
  for (const j of jids) {
    if (j && /@s\.whatsapp\.net$/.test(j)) return j.split('@')[0].split(':')[0].replace(/\D/g, '');
  }
  return '';
}
