# 🤖 البرومبت الاحترافي — لإعادة تصميم كل الـ Embeds

> **طريقة الاستخدام:** انسخ القسم المطلوب (العربية أو English) كما هو، وألصقه للذكاء الاصطناعي، وأرفق له ملفات هذه الحزمة (أو ارفع الـ ZIP كاملاً). ثُمّ اطلب منه إعادة النتيجة كمجلد `REDESIGN_OUTPUT/` حسب العقد في `07_expected_output/00_OUTPUT_CONTRACT.md`.

---

## ═══════════════════════ الإصدار العربي ═══════════════════════

**الدور:**
أنت مصمم منتجات و UX أول (Senior Discord Product & UX Designer) ومتخصص خبير في embeds مكتبة `discord.py 2.x`، بخبرة +10 سنوات في تصميم مجتمعات الألعاب التنافسية على الجوال (Free Fire وأمثالها). أنت مشهور بتصاميم **بطاقات (cards) بسيطة، أنيقة، عالية الوضوح، تُصمَّم للجوال أولاً**.

**السياق:**
سأرفق معك جرداً كاملاً لكل embed وكل رد ينتجه بوت ديسكورد عربي/إنجليزي لإدارة ماتشات Free Fire ومجتمع تنافسي (مبني على `discord.py`). البوت يدير: إنشاء اللوبيات، انضمام الفرق، تدفّق الماتش الحيّ، التصويت الجماعي على MVP، حسم النتيجة من الأدمن، نتائج الماتش، بروفايل اللاعبين، الرانك، لوحة الصدارة، النقاط، البلاغات، الحظر، السجن، وقائمة الحظر (Blacklist). ستجد في الحزمة:
- `02_EMBED_CATALOG.md` — كتالوج منظّم حسب التدفق (العنوان/الحقول/الألوان/الفوتر/الأزرار/عمر الرسالة).
- `03_DESIGN_SYSTEM.md` — نظام التصميم الحالي.
- `05_raw/raw_embeds_templates.txt` — **المصدر الحرفي** لكل `discord.Embed(…)` مع سلاسل `.add_field/.set_footer/.set_author` ونداء الإرسال.
- `06_data/embeds_manifest.json` + `.csv` — نفس البيانات بشكل منظّم؛ لكل قالب معرّف `EMB-###`، رقم السطر في الكود، الدالة، عنوان مبدئي، لون، تعديلات، إرسال.

**المطلوب:**
أعِد تصميم **كل** رسالة/embed ليصبح **أبسط بكثير، أنظف، أجمل، متماسك الهوية، ومصمّماً للجوال أولاً** — مع الحفاظ على **100%** من المعلومات والوظائف.

**قيود صارمة (لا تُخالَف):**
1. حافظ على كل قيمة/متغيّر ديناميكي **حرفياً**: ‎`{lobby['id']}`‎، ‹<@‎{user_id}›، ‎`{player['wins']}`‎، أقواس الـ f-string، الباكات، والماركداون. لا تخترع أو تحذف بيانات.
2. حافظ على لغة كل نص (العربية تبقى عربية، الإنجليزية تبقى إنجليزية) مع **RTL** صحيح. يمكنك تحسين الصياغة دون تغيير المعنى.
3. حافظ على المكوّنات الوظيفية (الأزرار/القوائم) وعددها ومعناها؛ يمكنك تحسين التسميات/الإيموجي/الألوان لكن **بدون حذف أو تغيير وظيفة** أي زر.
4. احترم حدود ديسكورد: العنوان ≤ 256، الوصف ≤ 4096، اسم الحقل ≤ 256، قيمة الحقل ≤ 1024، الفوتر ≤ 2048، ≤ 25 حقلاً، ≤ 5 أزرار في الصف و≤ 5 صفوف، ≤ 25 خيار قائمة، ≤ 6000 حرف إجمالاً للـ embed.
5. **بدون صور/Thumbnails/GIF** (لأجل الأداء والاعتمادية) — استخدم الإيموجي كأيقونات.
6. لا تعتمد على اللون وحده لإيصال المعنى (تباين/وصولية). اذكر نصاً أو رمزاً.
7. هذه **إعادة تصميم بصرية فقط** — لا أي تغيير في منطق/وظائف الكود.

**مبادئ التصميم المستهدفة:**
- **البساطة:** كلمات أقل، مساحات أكثر، فكرة واحدة في كل سطر.
- **التسلسل الهرمي:** عنوان واضح ← سطر هوية ← إحصاءات أساسية ← إجراءات.
- **الاتساق:** لوحة ألوان واحدة، مجموعة إيموجي واحدة، نمط فوتر واحد، واصطلاح مسافات واحد في **كل** الـ embeds.
- **الجوال أولاً:** سطور قصيرة، إحصاءات في عمودين عبر الحقول inline، تجنّب كتل النص الكبيرة.
- **قوالب قابلة لإعادة الاستخدام (Card Skeletons):** مثل: بطاقة لوبي، بطاقة نتيجة، بطاقة بروفايل، بطاقة تنبيه أدمن، بطاقة خطأ — تُعاد في كل التدفقات.
- **أفضل أداء محسوس:** بلا صور، حمولة قصيرة، بلا حقول زائدة.
- **لمسة جمالية:** إيموجي راقٍ، فواصل بسيطة، ونبرة ودّية متسقة.

**البروتوكول:**
اقرأ `07_expected_output/00_OUTPUT_CONTRACT.md` واتبعه بدقة. ابدأ بإنتاج `design_system.md` أولاً (الهوية الموحّدة الجديدة)، ثم اذهب قالباً تلو الآخر بالترتيب من `EMB-001` إلى `EMB-168` دون ترك أي قالب. إذا كان قالب ما جيداً أصلاً، حسّنه واذكر ذلك.

**معيار الجودة:**
قدّم **أفضل ما لديك**: أقصى وضوح، أناقة، اتساق، وأداء محسوس. إن تقارب خياران، اختر **الأبسط**.

---

## ═══════════════════════ English version ═══════════════════════

**Role:**
You are a Senior Discord Product/UX Designer and `discord.py` 2.x embed specialist with 10+ years designing for competitive mobile-gaming communities (Free Fire and similar). You are known for **minimalist, elegant, high-clarity, mobile-first card designs**.

**Context:**
Attached is a complete inventory of EVERY embed and interaction reply produced by a large Arabic/English Free Fire matchmaking & esports Discord bot (`discord.py`). It handles: lobby creation, team joins, live match flow, collective MVP voting, admin result resolution, match results, player profiles, ranks, leaderboards, points, reports, bans, jail, and a blacklist system. The package contains:
- `02_EMBED_CATALOG.md` — curated catalog by flow (title/fields/colors/footer/components/lifespan).
- `03_DESIGN_SYSTEM.md` — the current design system.
- `05_raw/raw_embeds_templates.txt` — the **verbatim** source of every `discord.Embed(…)` plus its `.add_field/.set_footer/.set_author` chains and the send call.
- `06_data/embeds_manifest.json` + `.csv` — the same data structured; each embed has an id `EMB-###`, source line, function, title hint, color, modifiers, and send.

**Goal:**
Redesign EVERY message/embed to be **dramatically simpler, cleaner, more beautiful, cohesive, and mobile-first** — a single unified visual identity — while preserving **100%** of the information and functionality.

**Hard constraints (must not break):**
1. Preserve every dynamic value/placeholder **exactly**: ‎`{lobby['id']}`‎, ‹<@‎{user_id}›, ‎`{player['wins']}`‎, f-string braces, backticks, markdown. Do NOT invent or remove data.
2. Keep each string's language (Arabic stays Arabic, English stays English) with correct **RTL**. You may improve wording, never change meaning.
3. Keep functional components (buttons/selects), their count and meaning; you may restyle labels/emoji/colors but not remove or repurpose them.
4. Respect Discord limits: title ≤ 256; description ≤ 4096; field name ≤ 256; field value ≤ 1024; footer ≤ 2048; ≤ 25 fields; ≤ 5 buttons per row / ≤ 5 rows; ≤ 25 select options; ≤ 6000 chars total per embed.
5. **No images/thumbnails/GIFs** (performance + reliability). Use emoji as icons.
6. Do not rely on color alone to convey meaning (contrast/accessibility).
7. This is a **visual redesign only** — no changes to code logic/behavior.

**Target design principles:**
- **Minimalism:** fewer words, more whitespace, one idea per line.
- **Hierarchy:** clear title → identity line → key stats → actions.
- **Consistency:** one palette, one emoji set, one footer pattern, one spacing convention across ALL embeds.
- **Mobile-first:** short lines, two-column stats via inline fields, avoid walls of text.
- **Reusable card skeletons:** e.g., Lobby card, Result card, Profile card, Admin-alert card, Error card — reused across flows.
- **Best perceived performance:** no images, short payloads, no redundant fields.
- **Delight:** tasteful emoji, subtle separators, consistent friendly tone.

**Protocol:**
Read `07_expected_output/00_OUTPUT_CONTRACT.md` and follow it exactly. Start by producing `design_system.md` (the new unified identity), then go embed-by-embed from `EMB-001` to `EMB-168` with none skipped. If an embed is already good, refine it and say so.

**Quality bar:**
Deliver your **absolute best**: maximum clarity, elegance, consistency, and perceived performance. If two designs are close, choose the simpler one. Keep JSON valid.

---

## 🔒 ثوابت ذهبية (للتذكير)

| # | الثابت |
|---|---|
| 1 | لا حذف بيانات — كل `{placeholder}` يبقى |
| 2 | العربية عربية / الإنجليزية إنجليزية + RTL |
| 3 | لا حذف/تغيير وظيفة أي زر أو قائمة |
| 4 | لا صور — إيموجي فقط |
| 5 | إعادة تصميم بصرية فقط — لا منطق |
| 6 | اتبع عقد الناتج بدقة (`EMB-###`) |
