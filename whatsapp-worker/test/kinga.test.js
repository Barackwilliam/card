import assert from 'node:assert/strict';
import test from 'node:test';

import {
  chambuaKikomo,
  chambuaTimelock,
  mudaWaKusubiri,
  nambaKutokaJid,
  ndaniYaSaaZaKutuma,
  niKosaLaKikomo,
  niOmbiLaKujitoa,
  saaYaEneo,
} from '../src/kinga.js';

const cfg = {
  timezone: 'Africa/Dar_es_Salaam', saaKuanza: 8, saaMwisho: 20,
  kusubiriMin: 40, kusubiriMax: 90, pumzikoKila: 8, pumzikoMin: 240, pumzikoMax: 480,
};

test('saa za Tanzania (UTC+3)', () => {
  assert.equal(saaYaEneo(new Date('2026-11-25T05:30:00Z'), cfg.timezone), 8);
  assert.equal(ndaniYaSaaZaKutuma(new Date('2026-11-25T04:59:00Z'), cfg), false); // 07:59
  assert.equal(ndaniYaSaaZaKutuma(new Date('2026-11-25T05:00:00Z'), cfg), true); // 08:00
  assert.equal(ndaniYaSaaZaKutuma(new Date('2026-11-25T16:59:00Z'), cfg), true); // 19:59
  assert.equal(ndaniYaSaaZaKutuma(new Date('2026-11-25T17:00:00Z'), cfg), false); // 20:00
});

test('muda wa kusubiri na pumziko refu', () => {
  for (const r of [0, 0.5, 0.999]) {
    const ms = mudaWaKusubiri(3, cfg, () => r);
    assert.ok(ms >= 40000 && ms <= 90000, `${ms}`);
  }
  const pumziko = mudaWaKusubiri(8, cfg, () => 0);
  assert.equal(pumziko, 240000);
});

test('kikomo cha WhatsApp', () => {
  const sasa = new Date('2026-11-25T10:00:00Z');
  assert.equal(chambuaKikomo(null).simama, false);
  assert.equal(chambuaKikomo({ capping_status: 'NONE', total_quota: 100, used_quota: 10 }, sasa).simama, false);
  const onyo = chambuaKikomo({ capping_status: 'FIRST_WARNING', cycle_end_timestamp: String(sasa.getTime() / 1000 + 3600) }, sasa);
  assert.equal(onyo.simama, true);
  assert.equal(onyo.mpaka.getTime(), sasa.getTime() + 3600 * 1000);
  const karibu = chambuaKikomo({ capping_status: 'NONE', total_quota: 50, used_quota: 46 }, sasa);
  assert.equal(karibu.simama, true);
  assert.match(karibu.muhtasari, /46\/50/);
  assert.equal(chambuaTimelock({ isActive: false }).simama, false);
  assert.equal(chambuaTimelock({ isActive: true, enforcementType: 'BIZ_QUALITY' }, sasa).simama, true);
});

test('makosa, ACHA na namba', () => {
  assert.equal(niKosaLaKikomo(new Error('rate-overlimit')), true);
  assert.equal(niKosaLaKikomo(new Error('bad image')), false);
  for (const t of ['ACHA', ' acha ', 'Stop.', 'sitaki']) assert.equal(niOmbiLaKujitoa(t), true, t);
  assert.equal(niOmbiLaKujitoa('nitachangia kesho'), false);
  assert.equal(nambaKutokaJid('123@lid', '255711000001@s.whatsapp.net'), '255711000001');
  assert.equal(nambaKutokaJid('255711000001:12@s.whatsapp.net'), '255711000001');
  assert.equal(nambaKutokaJid('123@lid'), '');
});
