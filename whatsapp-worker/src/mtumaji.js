// Mtumaji: anachukua ujumbe mmoja kutoka foleni, anaukagua na kuutuma, kisha
// anasema asubiri muda gani kabla ya kuchukua unaofuata.
import {
  bahati,
  mudaWaKuandika,
  mudaWaKusubiri,
  ndaniYaSaaZaKutuma,
  niKosaLaKikomo,
  niKosaLaMuunganisho,
  sleep as defaultSleep,
} from './kinga.js';

const DAKIKA = 60 * 1000;

async function pakuaPicha(url) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 30000);
  try {
    const r = await fetch(url, { signal: ctrl.signal });
    if (!r.ok) throw new Error(`Picha ya kadi haikupatikana (HTTP ${r.status})`);
    return Buffer.from(await r.arrayBuffer());
  } finally {
    clearTimeout(t);
  }
}

export class Mtumaji {
  constructor({ db, cfg, log, sleep = defaultSleep, sasa = () => new Date(), pakua = pakuaPicha, rnd = Math.random }) {
    Object.assign(this, { db, cfg, log, sleep, sasa, pakua, rnd });
    this.sock = null;
    this.imeunganishwa = false;
    this.idadi = 0; // jumbe zilizotumwa tangu worker ianze (kwa pumziko refu)
    this.makosa = 0; // makosa mfululizo
    this.zilizotumwa = new Map(); // id -> message, kwa getMessage (retry za WhatsApp)
  }

  wekaSocket(sock, imeunganishwa) {
    this.sock = sock;
    this.imeunganishwa = imeunganishwa;
  }

  kumbuka(msg) {
    if (!msg?.key?.id) return;
    this.zilizotumwa.set(msg.key.id, msg.message);
    if (this.zilizotumwa.size > 500) this.zilizotumwa.delete(this.zilizotumwa.keys().next().value);
  }

  /** Hatua moja. Hurudisha { subiri: ms, sababu }. */
  async hatua() {
    const { db, cfg } = this;
    const sasa = this.sasa();
    if (!this.sock || !this.imeunganishwa) return { subiri: 10000, sababu: 'haijaunganishwa' };

    const hali = await db.soma();
    if (hali.imesitishwa) return { subiri: 30000, sababu: 'imesitishwa' };
    if (hali.imesimamishwa_mpaka && new Date(hali.imesimamishwa_mpaka) > sasa) return { subiri: DAKIKA, sababu: 'kinga' };
    // Nje ya saa za kutuma, ni majaribio ya haraka tu (kitufe "Tuma sasa hivi") yanayotumwa.
    const ndani = ndaniYaSaaZaKutuma(sasa, cfg);

    const idadi = await db.idadiZilizotumwa();
    if (idadi.saa >= cfg.kikomoKwaSaa) return { subiri: 5 * DAKIKA, sababu: 'kikomo_saa' };
    if (idadi.siku >= cfg.kikomoKwaSiku) return { subiri: 15 * DAKIKA, sababu: 'kikomo_siku' };

    const u = await db.unaofuata({ harakaPekee: !ndani });
    if (!u) return ndani ? { subiri: 15000, sababu: 'foleni_tupu' } : { subiri: 20000, sababu: 'nje_ya_saa' };

    if (u.amejitoa) {
      await db.ghairi(u.id, 'Ameomba asitumiwe ujumbe');
      return { subiri: 0, sababu: 'amejitoa' };
    }
    if (u.aina === 'kikumbusho' && sasa - new Date(u.created) > cfg.umriKikumbushoSaa * 3600 * 1000) {
      await db.ghairi(u.id, 'Muda wake umepita (kilikaa foleni muda mrefu)');
      return { subiri: 0, sababu: 'muda_umepita' };
    }

    const namba = String(u.simu || '').replace(/\D/g, '');
    let jid;
    try {
      // Kutuma kwa namba zisizo na WhatsApp ni dalili ya spam: kagua kwanza.
      const [r] = (await this.sock.onWhatsApp(namba)) || [];
      if (!r?.exists) {
        await db.shindwa(u.id, 'Namba hii haipo kwenye WhatsApp');
        return { subiri: Math.round(bahati(5000, 12000, this.rnd)), sababu: 'haipo_whatsapp' };
      }
      jid = r.jid;
    } catch (e) {
      return this.kosa(u, e);
    }

    try {
      await this.sock.sendPresenceUpdate('composing', jid);
      await this.sleep(mudaWaKuandika(u.maandishi, this.rnd));
      await this.sock.sendPresenceUpdate('paused', jid);

      const content = u.picha_url
        ? { image: await this.pakua(u.picha_url), caption: u.maandishi }
        : { text: u.maandishi };
      const msg = await this.sock.sendMessage(jid, content);
      this.kumbuka(msg);
      await db.umetumwa(u.id, msg?.key?.id, u.aina, u.mgeni_id);
      this.makosa = 0;
      this.idadi += 1;
      this.log.info({ id: u.id, aina: u.aina }, 'Ujumbe umetumwa');
      return { subiri: mudaWaKusubiri(this.idadi, cfg, this.rnd), sababu: 'imetumwa' };
    } catch (e) {
      return this.kosa(u, e);
    }
  }

  async kosa(u, e) {
    const { db, cfg } = this;
    const ujumbe = String(e?.message || e).slice(0, 300);
    this.log.warn({ id: u.id, err: ujumbe }, 'Kutuma kumeshindwa');

    if (niKosaLaMuunganisho(e)) return { subiri: 15000, sababu: 'muunganisho' }; // ubaki foleni

    if (niKosaLaKikomo(e)) {
      await db.jaribioLimeshindwa(u.id, ujumbe, cfg.majaribioMax);
      await db.simamisha(new Date(this.sasa().getTime() + 120 * DAKIKA), 'WhatsApp imesema kikomo kimefikiwa. Tunasimama saa 2.');
      return { subiri: DAKIKA, sababu: 'kikomo_whatsapp' };
    }

    await db.jaribioLimeshindwa(u.id, ujumbe, cfg.majaribioMax);
    this.makosa += 1;
    if (this.makosa >= cfg.makosaMfululizo) {
      await db.simamisha(
        new Date(this.sasa().getTime() + cfg.simamaDakika * DAKIKA),
        `Makosa ${this.makosa} mfululizo (la mwisho: ${ujumbe}). Tunasimama dakika ${cfg.simamaDakika}.`,
      );
      this.makosa = 0;
    }
    return { subiri: Math.round(bahati(60000, 120000, this.rnd)), sababu: 'kosa' };
  }
}
