# Mfumo wa Michango ya Harusi

Mfumo wa kusimamia michango ya harusi:

- **Wageni**: orodha yote, ingiza kutoka Excel (CSV), tafuta, chuja.
- **Kadi**: kila mgeni anapata kadi yenye jina lake. Kadi zinahifadhiwa kwenye Supabase Storage na kutumwa WhatsApp.
- **Michango**: ingiza kila malipo (M-Pesa, Mixx, Airtel, HaloPesa, benki, taslimu). Mfumo unaonyesha ahadi, aliyotoa na salio la kila mtu.
- **Dashibodi**: jumla ya michango yote, wangapi wametumiwa kadi, wangapi wamechangia, salio la ahadi, na mgawanyo kwa njia ya malipo.
- **WhatsApp**: kadi, vikumbusho **mara 2 kwa siku** kwa ambao hawajachangia (au wana salio la ahadi), na shukrani mchango ukipokelewa. Mtu akijibu "ACHA" au "STOP", hatumiwi tena.

Teknolojia: Django 5.2, Postgres (Supabase), Supabase Storage, WhatsApp Cloud API ya Meta.

---

## 1. Kuendesha kwenye kompyuta yako

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DEBUG=1                      # bila DATABASE_URL inatumia SQLite
python manage.py migrate
python manage.py createsuperuser
python manage.py anzisha_harusi --malipo "M-Pesa 0754 000 000 (Michael Mchome)"
python manage.py runserver
```

Fungua http://localhost:8000. Bila funguo za WhatsApp, mfumo uko kwenye **hali ya majaribio**: kadi zinatengenezwa na ujumbe unaandikwa kwenye kumbukumbu kama "Jaribio", lakini hakuna kinachotumwa.

Majaribio (tests): `python manage.py test michango`

## 2. Supabase

1. **Database**: Project Settings → Database → Connection string → **Session pooler**. Iweke kama `DATABASE_URL`.
2. **Storage**: tengeneza bucket inayoitwa `kadi` na uiweke **Public**, kwa sababu WhatsApp inapakua kadi kupitia link ya umma.
3. Storage → Settings → **S3 access keys**: tengeneza key. Weka `SUPABASE_S3_ACCESS_KEY_ID`, `SUPABASE_S3_SECRET_ACCESS_KEY`, na `SUPABASE_S3_REGION` (region ya project yako).
4. `SUPABASE_URL` = `https://<project-ref>.supabase.co`.

Vigezo vyote viko kwenye `.env.example`.

## 3. Kuweka hewani kwenye Render

Repo ina `render.yaml`, kwa hiyo Render inasoma mipangilio yenyewe:

1. Render → **New → Blueprint** → chagua repo hii na tawi lake.
2. Jaza thamani unazoombwa (`DATABASE_URL`, `SUPABASE_*`, `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`, `HARUSI_MALIPO`). `SECRET_KEY` na `CRON_SECRET` zinatengenezwa zenyewe.
3. Build ikimaliza, mfumo unakuwa umetengeneza msimamizi na harusi ya kwanza wenyewe, bila kuhitaji terminal. Ingia kwenye `https://<jina>.onrender.com`.

Mpango wa bure wa Render "unalala" baada ya dakika 15 bila mtu. Mtu wa kwanza kufungua baada ya hapo atasubiri kama dakika moja. Vikumbusho vya GitHub Actions vinauamsha wenyewe.

Kubadilisha jina la bwana harusi, tarehe ya mwisho, maelekezo ya malipo, picha ya kadi au mahali jina linapokaa: **Mipangilio** (`/admin/`) → Harusi.

## 4. WhatsApp (Meta WhatsApp Cloud API)

1. Fungua app kwenye https://developers.facebook.com, chagua aina **Business**, kisha ongeza **WhatsApp**.
2. Ongeza na uthibitishe namba ya simu ya kutumia. Lazima iwe namba ambayo haitumiki kwenye WhatsApp ya kawaida.
3. Tengeneza **System User token** ya kudumu yenye ruhusa `whatsapp_business_messaging`. Hiyo ndiyo `WHATSAPP_TOKEN`. `WHATSAPP_PHONE_NUMBER_ID` iko kwenye ukurasa wa API Setup.
4. **Webhook**: Callback URL = `https://<mfumo-wako>/webhook/whatsapp/`, Verify token = `WHATSAPP_VERIFY_TOKEN`. Jiunge na `messages`. Weka pia `WHATSAPP_APP_SECRET` (App Settings → Basic) ili mfumo uthibitishe kwamba webhook inatoka kwa Meta.
5. Tengeneza **message templates** hizi kwenye WhatsApp Manager, lugha *Swahili (sw)*, kisha subiri ziidhinishwe:

**`kadi_mchango`**: Header: *Image*

> Habari {{1}}, familia inapenda kukujulisha kuhusu harusi ya mpendwa wetu {{2}}. Tafadhali pokea kadi yako ya mchango. Tunaomba mchango wako kabla ya tarehe {{3}}.
> Malipo: {{4}}
> Asante na Mungu akubariki.

**`kikumbusho_mchango`**

> Habari {{1}}, tunakukumbusha kwa upendo kuhusu mchango wa harusi ya {{2}}. Mwisho wa kuchangia ni {{3}}.
> Malipo: {{4}}
> Kama umeshachangia, tafadhali puuza ujumbe huu. Jibu ACHA kama hutaki kupokea vikumbusho.

**`kikumbusho_salio`**

> Habari {{1}}, asante kwa mchango wako wa TSh {{2}} kwa harusi ya {{3}}. Salio la ahadi yako ni TSh {{4}}. Mwisho wa kuchangia ni {{5}}.
> Malipo: {{6}}
> Jibu ACHA kama hutaki kupokea vikumbusho.

**`shukrani_mchango`**

> Asante sana {{1}}! Tumepokea mchango wako wa TSh {{2}} kwa harusi ya {{3}}. Jumla uliyochangia ni TSh {{4}}. Mungu akubariki.

Majina ya templates yanaweza kubadilishwa kupitia `WHATSAPP_TEMPLATE_*`.

**Mambo ya kujua kuhusu WhatsApp:**
- Meta inatoza kila ujumbe unaoanzishwa na biashara, kwa bei ya nchi ya mpokeaji. Angalia bei za sasa kwenye ukurasa wa Meta wa WhatsApp pricing.
- Namba mpya ina kikomo cha watu wanaoweza kutumiwa kwa siku. Kikomo kinapanda kadiri namba inavyotumika vizuri.
- Watu wengi wakiripoti ujumbe kama spam, Meta inaweza kuzuia namba. Ndiyo maana vikumbusho vinasimama mara mtu anapochangia, anapojibu ACHA, au tarehe ya mwisho ikipita, na hakuna kinachotumwa kabla ya saa 2 asubuhi wala baada ya saa 2 usiku. Idadi ya vikumbusho kwa siku inabadilishwa kwenye Mipangilio.

## 5. Vikumbusho mara 2 kwa siku

Chagua njia moja:

- **GitHub Actions** (tayari ipo: `.github/workflows/vikumbusho.yml`): weka siri `MICHANGO_URL` na `CRON_SECRET` kwenye GitHub. Inaendesha saa 3 asubuhi na saa 12 jioni. GitHub wakati mwingine huchelewesha ratiba kwa dakika kadhaa.
- **cron-job.org** au huduma nyingine: tuma `POST https://<mfumo>/cron/vikumbusho/` na header `Authorization: Bearer <CRON_SECRET>`.
- **Cron kwenye server**: `0 9,18 * * * cd /app && python manage.py tuma_vikumbusho`

Ni salama hata ratiba ikiendeshwa mara nyingi zaidi: mgeni hapokei zaidi ya vikumbusho 2 kwa siku, na kuna pengo la angalau saa 5 kati ya kikumbusho kimoja na kingine.

## 6. Kuingiza wageni

Wageni → **Ingiza orodha (CSV)**. Safu: `jina,simu,ahadi,ametoa,maelezo`. Ni jina tu la lazima. Kuingiza faili lilelile mara mbili hakurudii wageni wala hakuongezi pesa mara mbili.

Andika majina bila "Bw. & Bi.", kwa sababu vyeo tayari viko kwenye kadi juu ya jina.

---

## Zana ya kadi pekee (bila server)

`index.html` ni ukurasa mmoja unaotengeneza kadi nyingi kwa haraka bila server: bandika majina, kisha pakua kadi zote kama ZIP. Picha za kadi ziko kwenye `templates/`.

Fonti: Great Vibes na Montserrat (SIL Open Font License), kutoka Google Fonts.
