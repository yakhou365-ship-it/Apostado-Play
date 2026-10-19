# 📄 عقد الناتج (Output Contract) — اقرأه مع الذكاء الاصطناعي

> اطلب من الذكاء الاصطناعي أن يُنتِج **مجلداً باسم `REDESIGN_OUTPUT/`** بهذا الشكل **حرفياً**، ثم اضافة الملفات ZIP وإرجاعها. هذا يجعلني أطبّق التصاميم الجديدة مباشرةً على الكود دون أي التباس.

---

## الهيكل المطلوب للناتج

```
REDESIGN_OUTPUT/
├── design_system.md              ← الهوية الجديدة الموحّدة (الأولوية الأولى)
├── REDESIGNED_EMBEDS.md          ← تصميم كل قالب (واحد لكل EMB-###)
├── redesigned_embeds.json        ← نفس التصاميم بصيغة منظّمة (JSON صالح)
├── CHANGELOG.md                  ← ملخص التغييرات
└── python_snippets/              ← (مُفضّل) كود جاهز للصق لكل قالب
    ├── EMB-001.py
    ├── EMB-002.py
    └── …
```

---

## 1) `design_system.md` — الهوية الجديدة

يجب أن يحتوي:
- **لوحة الألوان الجديدة:** جدول (اسم الرمز | HEX | الاستخدام) — 8–12 لوناً كحد أقصى، متمايزة.
- **مفردات الإيموجي:** قائمة موحّدة (لا خلط عشوائي).
- **قواعد الخط/المسافات:** طول السطر، الفواصل، متى تستخدم `>`، متى `` `code` ``.
- **نمط الفوتر الموحّد** (قالب واحد فقط).
- **نبرة الصوت (Tone):** ودّية/احترافية/قصيرة.
- **قوالب البطاقات (Card Skeletons):** 4–6 هياكل قابلة لإعادة الاستخدام.
- **قائمة Do / Don't**.

## 2) `REDESIGNED_EMBEDS.md` — لكل قالب قسم بهذا الشكل **بالضبط**

```markdown
### EMB-001 — notify_admins (line 790)
- TITLE: <العنوان الجديد كقالب مع نفس المتغيّرات>
- DESCRIPTION:
  ```
  <الوصف الجديد كقالب كامل مع نفس الـ placeholders>
  ```
- FIELDS:
  - <اسم الحقل> | <القيمة> | inline|full
- COLOR: <#RRGGBB أو اسم الرمز>
- FOOTER: <قالب الفوتر>
- AUTHOR: <الاسم أو none>
- COMPONENTS: <زر|style> أو none
- WHY: <جملة واحدة تشرح الفكرة>
- BEFORE→AFTER: <سطر يلخّص الفرق>
```

> **مهم:** نفس المتغيّرات/الـ placeholders **حرفياً** كما في الأصل (مأخوذة من `05_raw/raw_embeds_templates.txt`).

## 3) `redesigned_embeds.json` — منظّم للآلة

```json
[
  {
    "id": "EMB-001",
    "title": "…",
    "description": "…",
    "fields": [
      { "name": "…", "value": "…", "inline": true }
    ],
    "color": "#RRGGBB",
    "footer": "…",
    "author": "…",
    "components": [
      { "type": "button", "label": "…", "style": "success" }
    ],
    "why": "…"
  }
]
```
> **JSON صالح إلزامي.** لا تعليقات، لا فواصل زائدة. نفس ترتيب `EMB-001 … EMB-168`.

## 4) `python_snippets/EMB-###.py` (مُفضّل — يسرّع التطبيق كثيراً)

مقتطف جاهز للصق يحافظ على **نفس أسماء المتغيّرات** في الأصل، مثل:

```python
# EMB-002 — create_lobby_embed (line 2143)
embed = discord.Embed(
    title=f"…",
    description=( f"…{lobby['id']}…" ),
    color=0xFFD700,
    timestamp=discord.utils.utcnow()
)
embed.add_field(name=f"…{t1c}…", value=t1_text, inline=True)
embed.set_footer(text=f"{BOT_FOOTER}  •  Lobby #{lobby['id']}")
```

## 5) `CHANGELOG.md`

- ملخّص نقاط (bullets) لكل ما تغيّر.
- أي دمج/توحيد (مثلاً توحيد بطاقات الخطأ).
- أي قالب بقي كما هو ولماذا.

---

## ✅ قائمة تحقق قبل الإرجاع

- [ ] كل القوالب من `EMB-001` إلى `EMB-168` مغطّاة (بدون استثناء).
- [ ] لا حذف لأي `{placeholder}` أو معلومة.
- [ ] اللغة محفوظة (عربي/إنجليزي) + RTL.
- [ ] لا حذف/تغيير وظيفة لأي زر أو قائمة.
- [ ] احترام حدود ديسكورد.
- [ ] بلا صور/GIF.
- [ ] `redesigned_embeds.json` صالح (JSON parser).
- [ ] `design_system.md` موجود وكامل.
- [ ] الناتج داخل مجلد `REDESIGN_OUTPUT/` ثم مضغوط ZIP.
