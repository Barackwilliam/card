// Mhariri wa ujumbe: matoleo kadhaa (yanatenganishwa na "---"), vitufe vya vishika-nafasi
// na onyesho la ujumbe kama kiputo cha WhatsApp.
(() => {
  const mfanoEl = document.getElementById('mfano-vishika');
  const MFANO = mfanoEl ? JSON.parse(mfanoEl.textContent) : {};
  const ACHA = '(Jibu ACHA kama hutaki kupokea vikumbusho.)';
  const gawa = (t) => (t || '').split(/^\s*-{3,}\s*$/m).map(s => s.trim()).filter(Boolean);
  const jaza = (t) => t.replace(/\{(\w+)\}/g, (m, k) => (k in MFANO ? MFANO[k] : m));

  function anzisha(el) {
    const siri = el.querySelector('textarea[data-thamani]');
    const orodha = el.querySelector('[data-matoleo]');
    const kiputo = el.querySelector('[data-kiputo]');
    const niKikumbusho = el.dataset.kikumbusho === '1';
    let mwisho = null;

    function sasisha() {
      const maandishi = [...orodha.querySelectorAll('textarea')].map(t => t.value.trim()).filter(Boolean);
      siri.value = maandishi.join('\n---\n');
      const t = (mwisho && mwisho.value.trim()) || maandishi[0] || '';
      let onyesho = jaza(t);
      if (onyesho && niKikumbusho && !/\bacha\b/i.test(onyesho)) onyesho += '\n' + ACHA;
      kiputo.textContent = onyesho || 'Andika ujumbe wako hapo juu...';
      orodha.querySelectorAll('.toleo').forEach((d, i, all) => {
        d.querySelector('.toleo-lbl').textContent = all.length > 1 ? `Toleo ${i + 1}` : 'Ujumbe';
        d.querySelector('[data-ondoa]').hidden = all.length < 2;
      });
    }

    function ongeza(text) {
      const d = document.createElement('div');
      d.className = 'toleo';
      d.innerHTML = '<div class="toleo-head"><span class="toleo-lbl label"></span><button type="button" class="btn sm ghost danger" data-ondoa>Ondoa</button></div><textarea rows="6"></textarea>';
      const ta = d.querySelector('textarea');
      ta.value = text || '';
      ta.addEventListener('focus', () => { mwisho = ta; sasisha(); });
      ta.addEventListener('input', sasisha);
      d.querySelector('[data-ondoa]').addEventListener('click', () => { d.remove(); if (mwisho === ta) mwisho = null; sasisha(); });
      orodha.append(d);
      return ta;
    }

    (gawa(siri.value).length ? gawa(siri.value) : ['']).forEach(ongeza);
    siri.hidden = true;

    el.querySelectorAll('[data-kishika]').forEach(b => b.addEventListener('click', () => {
      const ta = mwisho || orodha.querySelector('textarea');
      const k = `{${b.dataset.kishika}}`;
      const [s, e] = [ta.selectionStart ?? ta.value.length, ta.selectionEnd ?? ta.value.length];
      ta.value = ta.value.slice(0, s) + k + ta.value.slice(e);
      ta.focus();
      ta.selectionStart = ta.selectionEnd = s + k.length;
      mwisho = ta;
      sasisha();
    }));
    el.querySelector('[data-ongeza]')?.addEventListener('click', () => { const ta = ongeza(''); ta.focus(); mwisho = ta; sasisha(); });
    el.querySelector('[data-rudisha]')?.addEventListener('click', (e) => {
      orodha.innerHTML = '';
      ongeza(e.currentTarget.dataset.rudisha);
      mwisho = null;
      sasisha();
    });
    sasisha();
    el.mhariri = { weka(text) { orodha.innerHTML = ''; (gawa(text).length ? gawa(text) : ['']).forEach(ongeza); mwisho = null; sasisha(); } };
  }

  document.querySelectorAll('.mhariri').forEach(anzisha);
})();
