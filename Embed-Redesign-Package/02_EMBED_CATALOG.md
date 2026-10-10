# EMBED_CATALOG.md — الجرد الكامل لكل ردود البوت (قبل التحسين)

> **الغرض:** مرجع تصميمي لكل رسالة/Embed يُرسلها بوت Apostado-Play حرفياً (شكل + قالب + وجهة + أزرار + عمر الرسالة)، لنُحسّن التصاميم لاحقاً دون الحاجة لقراءة الكود من جديد.
> **المصدر:** `freefire-bot-main.py` عند commit `4a50267` (main).
> **ملاحظة:** هذا ملف توثيقي فقط — لا يغيّر أي سلوك في البوت.

---

## 0. نظام التصميم المشترك (Design System)

| العنصر | القيمة | الملف/السطر |
|---|---|---|
| `PREFIX` | `!!` | 69 |
| `BOT_FOOTER` | `"✨ {server_name} • Dev By Aizen"` | 196 |
| `separator()` | `"──────────────────────"` (22 شرطة) | 321-323 |
| `apply_branding(embed, guild)` | يضبط الفوتر = `BOT_FOOTER.format(server_name=guild.name)` + `embed.timestamp = utcnow()` — **بدون صور/GIF** | 238-250 |
| `BUILD_ID` | `RAILWAY_GIT_COMMIT_SHA` أو `BOT_BUILD_ID` أو `local-dev` | 99 |

### لوحة الألوان `COLORS` (سطر 172-193)
| المفتاح | HEX | الاستخدام |
|---|---|---|
| `success` | `0x2ECC71` | نجاح |
| `error` | `0xE74C3C` | خطأ |
| `warning` | `0xF1C40F` | تحذير |
| `info` | `0x3498DB` | معلومات |
| `play` | `0xFFD700` | اللعب |
| `profile` | `0x9B59B6` | البروفايل |
| `leaderboard` | `0xF1C40F` | اللوحة |
| `match` | `0x3498DB` | الماتش |
| `admin` | `0xC0392B` | إداري |
| `vote` | `0x8E44AD` | التصويت |
| `auto` | `0x16A085` | تلقائي |
| `rank_low/mid/high/elite/legend` | `0x95A5A6 / 0x3498DB / 0x9B59B6 / 0xF1C40F / 0xE74C3C` | حسب الرانك |

**ألوان ثابتة مستخدمة مباشرة (خارج `COLORS`):** `0xFFD700` (لوبي/play)، `0xFF6B00` (برتقالي في `general`/`help`)، `0xE74C3C` (help admin)، `0x2ECC71` (نجاح صريح).

### جرد الـ Views / الأزرار / المودالات
| View / Modal | العناصر |
|---|---|
| `CreateLobbyView` | زر `📋 Create Lobby` (success) `create_lobby_btn` |
| `LobbyButtonsView` | `Join Team 1` (danger) • `Join Team 2` (success) • `Leave` (secondary) • `Cancel Game` (danger) |
| `StartVoteView` | `🗳️ Start Vote` (success) • `❌ Cancel Match` (danger) |
| `MvpVoteView` | Select `🏆 MVP WINNER` + Select `✦ MVP LOSER` (من مصوّري الفريقين، 4) + زر `tag_admin` + زر `status` |
| `MvpSelectionView` | Select winner + Select loser (كود قديم/غير مُفعّل) |
| `VoteView` | `🟠 Team 1` • `🟢 Team 2` (تصويت قديم/غير مُفعّل) |
| `ReportButtonView` | زر `⚠️ إبلاغ عن لاعب` (danger) |
| `ReportPlayerSelectView` | Select لاختيار اللاعب المُبلَّغ عنه |
| `RematchView` | زر `🔄 Rematch` (success) |
| `RoomInfoModal` | TextInput: Room ID • Password (اختياري) • Private Key (اختياري) |
| `JoinKeyModal` | TextInput: Private Match Key |
| `ReportReasonModal` | TextInput: سبب البلاغ |
| `LobbyCreateModal` | TextInput: Room ID • Password • Private Key |

---

## 1. الإعداد / بدء التشغيل / AUTO-DETECT

### 1.1 رسالة AUTO-DETECT الكاملة — `send_success()` (سطر 5636) → `success_ch.send(embed=...)`
- العنوان: `✅ AUTO-DETECT Complete`
- الوصف: `> 🤖 Bot: Free Fire Bot V3 MAX` · `> 🏠 Server: {guild.name}` · `> 📅 Time: {format_dt(now,'F')}` · فاصل · `> 📊 Channels detected:` `📝 Commands: {n}` `🎮 Play: {n}` `🔊 Waiting rooms: {n}` `🔍 Under check: {n}` · فاصل · `> ✅ كل القنوات...` `> ✅ البوت جاهز...` `> 💡 Use {PREFIX}help`
- اللون: `success` · الفوتر: `BOT_FOOTER • V3 MAX AUTO-DETECT` · **بدون أزرار**

### 1.2 قواعد السيرفر (قناة rules) — `build_rules_embed(guild_name)` (سطر 6786)
- العنوان: `🛡️ قواعد السيرفر` · اللون: `warning` · author: `Server Rules` · footer: `BOT_FOOTER • Read carefully`
- الوصف: 5 قواعد مرقّمة (احترام متبادل / قواعد اللعب / عدم الغش / استخدام الأوامر / العقوبات) + `💬 لأي استفسار...`
- تُرسَل عبر `ensure_rules_channel` (6844) وتُعرض بـ `{PREFIX}rules` (8049).

---

## 2. تدفّق اللعب (Play Flow)

### 2.1 رسائل التحقق قبل إنشاء اللوبي — `create_mode_lobby` (سطر 6196-6284)
| # | العنوان | الوصف المختصر | اللون | عمر الرسالة |
|---|---|---|---|---|
| a | `🚫 أنت محظور من اللعب` | السبب + عدد البلاغات + تاريخ الحظر + توجيه لفويس التفتيش | `error` | `delete_after=20` |
| b | `❌ Not Allowed Here` | الأمر في قنوات play فقط | `error` | `delete_after=15` |
| c | `⏳ Must Be in a Waiting Room` | يجب الدخول لفويس انتظار + قائمة الغرف | `warning` | `delete_after=20` |
| d | `⏳ Wrong Voice Channel` | أنت في `{voice}` ليست غرفة انتظار + قائمة الغرف | `warning` | `delete_after=20` |
| e | `❌ Already in Lobby` | أنت في لوبي — استخدم `{PREFIX}leave` | `error` | `delete_after=10` |

### 2.2 رسالة إنشاء اللوبي (Create Prompt) — `create_mode_lobby` (سطر 6284) → `ctx.send(embed=..., view=create_view)`
- العنوان: `🎮 Create {MODE} Lobby`
- الوصف: `> اضغط الزر تحت لإدخال بيانات الغرفة وإنشاء اللوبي.` · فاصل مباشر · `> 💡 تحتاج:` `› Room ID` `› Password (اختياري)` `› Private Key (اختياري)` · `separator()` · `> ⏱️ تختفي هذه الرسالة تلقائياً بعد {CREATE_PROMPT_DELETE_AFTER} ثانية` `> ✅ وإذا أنشأت الغرفة — تنحذف مع انتهاء الروم.`
- اللون: `info` · الأزرار: **`📋 Create Lobby`** · عمر: تختفي بعد `CREATE_PROMPT_DELETE_AFTER` (120s) أو عند انتهاء الماتش

### 2.3 Modal بيانات الغرفة — `RoomInfoModal` (سطر 3315)
- TextInputs: `Room ID (Numbers Only)` (required) • `Password (Optional)` • `Private Match Key (Optional)`
- ردود الفشل (ephemeral): `❌ Match not active!` · `❌ Only the host!`
- رد النجاح: `✅ Room Info Saved` (ephemeral) — `> Room details stored successfully.` + Room ID/Code/Private Key في code blocks
- اللون: `success`

### 2.4 embed اللوبي الحيوي — `create_lobby_embed(lobby, guild)` (سطر 2143)
- العنوان: `✦ Free Fire — {MODE} Lobby`
- الوصف: `> Lobby ID: {id}` · `> Host: <@{creator_id}>` · `> Mode: {MODE} · Progress: {total}/{size} {pct}%` · `{progress_bar}`
- الحقول: `🔴 Team 1 — {n}/{size}` (inline) · `🟢 Team 2 — {n}/{size}` (inline) · `📋 Status` (full) · **اختياري:** `🔐 Private Match` (if private key)
- author: `Host: {host_name} · Match Lobby` · footer: `BOT_FOOTER • Lobby #{id}` · اللون: `0xFFD700`
- الأزرار: **`Join Team 1` / `Join Team 2` / `Leave` / `Cancel Game`**
- يُرسَل عند إنشاء اللوبي (`LobbyCreateModal.on_submit` سطر 5398) ويُعاد تحريره عند كل انضمام/مغادرة

### 2.5 Modal مفتاح الماتش الخاص — `JoinKeyModal` (سطر 3358)
- TextInput: `Private Match Key` (required)
- رد خاطئ: `❌ Wrong Key` (ephemeral) — `> The private key you entered is incorrect.` `> Please ask the host for the correct key.` · اللون `error`

### 2.6 ردود الانضمام الفورية — `LobbyButtonsView._handle_join` / `_complete_join`
| النوع | النص/العنوان | الوصف | اللون | ملاحظة |
|---|---|---|---|---|
| نص | `❌ Lobby not found!` | — | — | ephemeral |
| نص | `❌ Lobby not active!` | — | — | ephemeral |
| نص | `❌ Already in lobby #{id}! Leave first.` | — | — | ephemeral |
| نص | `❌ Lobby gone!` | — | — | ephemeral |
| نص | `❌ Team full! ({n}/{size})` | — | — | ephemeral |
| نص | `✅ Joined **{team_name}**!` | — | — | ephemeral |
| Embed | `🚫 أنت محظور من اللعب` | السبب + عدد البلاغات + توجيه للتفتيش | `error` | ephemeral |
| Embed | `⏳ Join a Waiting Room` | ادخل غويس انتظار + الغرف المتاحة | `warning` | ephemeral |
| Embed | `⏳ Wrong Voice Channel` | أنت في `{voice}` + الغرف المتاحة | `warning` | ephemeral |
| Embed | `⏳ Pending Match` | لديك ماتش معلّق يجب إنهاؤه | `warning` | ephemeral |

### 2.7 embed معلومات الغرفة — `room_embed` (سطر 3765/3870)
- العنوان: `ℹ️ Room Info` · الوصف: `Join the room with these credentials:`
- الحقول: `🆔 Room ID` `🔑 Password` (inline) · حقل بلا اسم: `🔥 Join now and good luck!`
- اللون: `auto` · يُرسَل ephemeral للاعب + إلى شات الفريق

### 2.8 رسائل بدء الماتش — `LobbyButtonsView._complete_join` (3819/3833)
| العنوان | الوصف | اللون | عمر |
|---|---|---|---|
| `❌ Failed to Start` | `Could not create match channels.` + `Lobby #{id} has been cancelled.` | `error` | `delete_after=15` |
| `✅ Match Ready!` | `Lobby is full — match is starting now!` + `Moving players to their team voice channels...` | `success` | يُحذف عند نهاية الماتش (registry) |

### 2.9 embed داخل قناة الماتش — `start_embed` (سطر 3882)
- العنوان: `📻 Match Started!` · الوصف: `> Lobby: #{id}` · `> Mode: {MODE} · Host: <@{creator_id}>`
- الحقول: حقل بلا اسم (`🎮 Match started...` + تعليمات الهوست) · `📡 Room Info` (`🆔 Room ID` + `🔑 Password`)
- author: `Match Live` · footer: `BOT_FOOTER • Match #{id}` · اللون: `auto` · الأزرار: **`🗳️ Start Vote` / `❌ Cancel Match`**

### 2.10 embed نظام البلاغ داخل الماتش — `report_embed` (سطر 3923)
- العنوان: `⚠️ نظام البلاغ` · الوصف: تعليمات الزر + حد البلاغات + نقل المحظور للتفتيش · اللون `error` · الأزرار: **`⚠️ إبلاغ عن لاعب`**

### 2.11 ردود إغلاق التصويت/الإلغاء — `StartVoteView`
| الحالة | العنوان/النص | اللون | ملاحظة |
|---|---|---|---|
| cooldown | `⏳ لم يحن وقت التصويت بعد` (المتبقي دقائق/ثوانٍ) | `warning` | ephemeral |
| نص | `❌ Cannot determine lobby! (restart?)` | — | ephemeral |
| نص | `❌ Match not active!` | — | ephemeral |
| نص | `❌ فقط الأدمنز والأونر والهوست يبدؤون التصويت!` | — | ephemeral |
| نص | `❌ Guild not found!` | — | ephemeral |
| نص | `✅ Vote started!` | — | ephemeral |
| نص | `⚠️ صوّت بالفعل! ({n}/{req})` | — | ephemeral |
| Embed | `🗳️ تصويت إلغاء الماتش` | `> <@{uid}> صوّت لإلغاء الماتش` + التقدم | `warning` | — |
| Embed | `🛡️ Match Cancelled` | Lobby/Mode/Cancelled by + إعادة اللاعبين | `error` | author `Match Cancelled` |

### 2.12 انتهاء/إغلاق اللوبي (Timeout / Closed) — سطر 2678 / 3121
| العنوان | الوصف | اللون | عمر |
|---|---|---|---|
| `⏰ Lobby Closed — Not Enough Players` | لم يكتمل العدد خلال **2 دقيقة** + `{PREFIX}play 4v4` | `warning` | `delete_after=TEMP_EMBED_DELETE_AFTER` (120) |
| `⏰ Lobby Timed Out` | اللوبي `#{id}` أُلغي لعدم النشاط + `{PREFIX}play 4v4` | `warning` | `delete_after=120` |

### 2.13 أوامر اللعب النصية — `play_cmd` / `play1v1_cmd` / `leave_cmd` / `matches_cmd`
| العنوان | الوصف المختصر | اللون | عمر |
|---|---|---|---|
| `❌ أمر غير صحيح` (no mode) | قائمة `play1v1..play4v4` | `error` | 15 |
| `❌ مود غير صحيح` (invalid) | المودات الصحيحة | `error` | 15 |
| `🔒 أمر محمي` (restricted) | شروط الرول العالي (position ≥ threshold) | `error` | 20 |
| `❌ Not in Lobby` (`leave`) | لست في لوبي | `error` | — |
| `🗑️ Lobby Cancelled` (`leave` آخر لاعب) | `Lobby #{id} was cancelled.` | `warning` | — |
| `✅ Left Lobby` (`leave`) | `You left lobby #{id}.` | `success` | — |
| `🎮 Active Lobbies` (فارغ) | لا لوبيات نشطة + `{PREFIX}play` | `info` | — |
| `🎮 Active Lobbies` (مع بيانات) | حقل لكل لوبي: `#{id} {emoji} {MODE} — {se}` + `🟠 n/size • 🟢 n/size` | `match` | — |

---

## 3. تدفّق التصويت الجماعي على MVP (MvpVoteView)

### 3.1 رسالة بدء التصويت — `auto_trigger_vote` (سطر 3034) → `general_text.send(content="🔱 {t1m} {t2m}", embed=..., view=mvp_view)`
- العنوان: `🗳️ تصويت MVP الجماعي — Match #{id}`
- الوصف: `>Match finished — اختروا الـ MVPs معاً.` · `> ⏱️ عندكم {VOTE_TIMEOUT_SECONDS} ثانية...` · `> 🎯 الاتفاق المطلوب: {MVP_CONSENSUS_NEEDED} أصوات من {len(voters)}` · فاصل · `> 🔴 مصوّني Team 1 (أول 2): ...` · `> 🟢 مصوّني Team 2 (أول 2): ...` · `> 💡 المصوّنين يدوّرون على MVP WINNER و MVP LOSER...` · `> ⚠️ ما اتفقتم؟ البوت ينقل أدمن...`
- الحقول: `🔴 Team 1 — {n} players` (inline) · `🟢 Team 2 — {n} players` (inline)
- author: `MVP Voting` · footer: `BOT_FOOTER • Match #{id}` · اللون: `vote`
- الأزرار: **Select `🏆 MVP WINNER` + Select `✦ MVP LOSER` (للمصوّرين الأربعة) + زر طلب أدمن + زر الحالة**

### 3.2 ردود المصوّرين — `MvpVoteView` (كلها ephemeral إلا ما ذُكر)
| النوع | النص/العنوان | اللون | ملاحظة |
|---|---|---|---|
| Embed | `⛔ ما أنت من المصوّنين` | `error` | يُظهر أسماء مصوّري الفريقين |
| Embed | `📊 حالة تصويت MVP — ماتش #{id}` | `info` | يُظهر من صوّت + عداد الأصوات + الاتفاق المطلوب |
| Embed | `⚠️ تم طلب تدخل الأدمن` | `warning` | يستدعي `escalate_mvp_dispute` |
| نص | `🏆 تم تسجيل تصويتك لـ MVP WINNER: <@{id}>` | — | ephemeral |
| نص | `✦ تم تسجيل تصويتك لـ MVP LOSER: <@{id}>` | — | ephemeral |
| Embed | `✅ تم الاتفاق على MVP!` | `success` | يُرسَل لقناة الماتش: `> 🤝 اتفاق {n} أصوات من {m} مصوّنين` + WINNER +80 / LOSER +30 |

### 3.3 كود قديم غير مُفعّل — `VoteView` (سطر 5060-5308) + `MvpSelectionView` (4203)
> هذه التدفقات غير مُستدعاة على أي مسار حيّ (dead code) لكن موجودة في الكود، وتشمل:
- `⏰ Vote Ended — No Votes!` (`warning`) · `⏰ Vote Tied!` (`warning`) · `⏰ Vote Closed!` (`success`) · `🎯 اختر MVP كل فريق` (`vote`, author `MVP Selection`) · Vote Progress (`description` فقط, `vote`) · `✅ Vote Complete!` (`success`)
- ردود: `❌ Cannot determine lobby!` / `❌ Vote not active!` / `❌ فقط الهوست وأول داخل يصوتون!` / `❌ Already voted!` / `✅ Voted **{dd}**!`
- `MvpSelectionView`: `✅ تم تطبيق النقاط!` (`success`) + `❌ فقط منشئ الروم يختار MVP!` + اختيارات MVP

### 3.4 تصعيد نزاع MVP — `escalate_mvp_dispute` (سطر 4404) → `channel.send(content=mentions, embed=...)`
- العنوان: `🚨 تعذّر الاتفاق على MVP — الماتش #{id}`
- الوصف: mentions + `> ⚠️ ما في تفاهم بين المصوّنين...` + السبب + فاصل + المصوّرين + ملخّص التصويت (WINNER/LOSER)
- الحقل: `🔧 الأمر المطلوب منك` (`{PREFIX}w ...` / `{PREFIX}l ...`)
- footer: `BOT_FOOTER • .Admin action required` · اللون: `error`

---

## 4. نتيجة الماتش

### 4.1 embed النتيجة — `process_match_result` (3259) و `process_match_result_with_mvps` (4965)
- العنوان: `🏅 Match Result — #{id}`
- الوصف: `## 🎉 {wd} Wins!` · فاصل · `> 🎮 Mode: {MODE}` · `> 🏆 Winner MVP: <@..> → +80 pts` · `> ✦ Loser MVP: <@..> → +30 pts`
- الحقول: `🏆 Winners — {n} players` (inline) · `☠️ Losers — {n} players` (inline)
- author: `Match Finished` · footer: `BOT_FOOTER • GG WP! • Match #{id}` · اللون: `success`
- **الوجهة الآن:** قناة `match-results` إن وُجدت (وإلا القناة الأصلية) — عبر `_post_match_result`

---

## 5. أدوات الأدمن — القنوات / Setup

| الأمر | العنوان | الوصف المختصر | اللون | عمر |
|---|---|---|---|---|
| `!!setup` | `✅ Setup Complete!` | القنوات المُنشأة + rules + Blacklist Role | `success` | — |
| `!!autosetup` | `🔄 جارٍ فحص السيرفر...` | فحص/إنشاء الناقص | `warning` | يُحرَّر |
| `!!autosetup` ✓ | `✅ تم الفحص والإصلاح!` | ملخص ما أُنشئ | `success` | — |
| `!!autosetup` ✗ | `❌ فشل Auto-setup` | الخطأ | `error` | — |
| `!!cleanup` | `🧹 Cleanup Complete!` | حذف كاتيجوريات الماتش | `success` | — |
| `!!scan` | `🔍 Server Scan — {n} Categories` | إحصائيات + حقول لكل كاتيجوري | `info` | — |
| `!!deletecat` (missing) | `❌ Missing Name` | الاستخدام | `error` | — |
| `!!deletecat` (not found) | `❌ Not Found` | لا كاتيجوري مطابق | `error` | — |
| `!!deletecat` (تأكيد) | `⚠️ Confirm Deletion` | Category + عدد القنوات + تحذير الحذف | `warning` | — |
| `!!confirmcat` (missing) | `❌ Missing Name` | الاستخدام | `error` | — |
| `!!confirmcat` (not found) | `❌ Not Found` | لا كاتيجوري مطابق | `error` | — |
| `!!confirmcat` ✓ | `🗑️ Category Deleted!` | عدد المحذوف + الأخطاء | `success` | — |
| `!!confirmcat` جزئي | `⚠️ Partial Delete` | تعذّر حذف الكاتيجوري نفسه | `warning` | — |
| `!!setcommandschannel` | `✅ Channel Removed` / `✅ Channel Added` | إضافة/إزالة قناة أوامر | `success` | — |
| `!!setleaderboard` | `✅ Leaderboard Set` | تعيين قناة اللوحة | `success` | — |

### 5.1 أوامر الرانك/الـ Roles/النقاط
| الأمر | العنوان | الوصف المختصر | اللون | عمر |
|---|---|---|---|---|
| `!!fixrankall` | `🚀 Applying Ranks...` → `✅ Done!` | معالجة `{n}` عضو | `warning`→`success` | يُحرَّر |
| `!!syncroles` | `🔄 جارٍ مزامنة الـ Roles...` → `✅ تمت مزامنة الـ Roles!` | مستويات الرولات #1 / #2-10 / #11-50 / #51-100 | `warning`→`success` | يُحرَّر |
| `!!resetrankall` | `🚀 جارٍ تصفير النقاط والرانك...` → `✅ تم تصفير كل البيانات!` | تصفير شامل | `warning`→`success` | يُحرَّر |
| `!!setlevel` | `✅ Level Updated` / `❌ Missing` / `❌ Invalid Level` | تعيين رانك لاعب (1..9999) | `success`/`error` | — |
| `!!setpoints` | `✅ Points Updated` / `❌ Missing` / `❌ Invalid Points` | تعيين نقاط لاعب (±99999) | `success`/`error` | — |
| `!!resetstats` | `✅ Stats Reset` / `❌ Missing User` | تصفير ستاتس لاعب | `success`/`error` | — |
| `!!syncnicknames` | `✅ Synced` | عدد الأعضاء المُزامَنين | `success` | — |
| `!!fixrank` | `🔧 Rank Applied` / `🔱 Server Owner` | تطبيق الرانك يدوياً | `success`/`warning` | — |

---

## 6. أوامر اللاعب — الإحصائيات والبروفايل

| الأمر | العنوان | الوصف المختصر | اللون | ملاحظة |
|---|---|---|---|---|
| `!!p` / `!!card` | `create_profile_embed` (سطر 2232) | العنوان ديناميكي (اسم/رانك) + Rank/Points/MVPs + 6 حقول (Wins/Losses/W-L/Matches/MVPs/Kills) + Win Rate + تقدم للقمة | حسب الرانك | author `Player Profile` |
| `!!points` | `💰 نقاط اللاعب` (6477) | اللاعب + الرانك + النقاط + Wins/Losses/MVPs + Win Rate + التقدم نحو الأول | حسب الرانك | author `Player Points` |
| `!!top` (فارغ) | `🏆 Leaderboard` | لا لاعبين بعد | `leaderboard` | — |
| `!!top` (مع بيانات) | `🏆 Free Fire — Top 10 Leaderboard` | author = اسم السيرفر | `leaderboard` | footer: عدد اللاعبين |
| `!!mylevel` | `{rank_emoji} RANK — {name}` | Rank/Points + Wins/Losses/W-L/Win Rate | حسب الرانك | author `Player Rank` |
| `!!myrank` | `📝 Your Rank` | Member + RANK + Nickname الحالي/المستهدف | `profile` | — |
| `!!matches` | (انظر 2.15) | اللوبيات النشطة | `match` | — |
| `!!matchinfo` | `📋 Match — #{id}` / `❌ Missing ID` / `❌ Not Found` | الحالة + المود + الفريقان | `info`/`error` | — |

### 6.1 أوامر المساعدة العامة
| الأمر | العنوان | الوصف | اللون | ملاحظة |
|---|---|---|---|---|
| `!!general` | `🎮 Player Commands` | Play/Stats/Control/How to Play + نظام النقاط | `0xFF6B00` | footer: `Free Fire Bot v4.0 • !!help (admin)` |
| `!!help` (صفحة 1) | `🔥 Free Fire Bot v4.0 — أوامر اللاعبين` | اللعب/الإحصائيات/البلاغات/المساعدة | `0xFF6B00` | footer `صفحة 1/2` |
| `!!help` (صفحة 2) | `🔧 Free Fire Bot v4.0 — أوامر الأدمن` | القنوات/الرانك/البلاغات/JAIL/BLACKLIST/معلومات | `0xE74C3C` | footer `صفحة 2/2` |
| `!!botinfo` | `🤖 Bot Info` | Name/Version/Build/Prefix/Servers/Users/Owner + Coverage + Features | `info` | author `Bot Information` |
| `!!rules` | (قواعد السيرفر — انظر 1.2) | 5 قواعد | `warning` | — |

---

## 7. البلاغات والحظر

### 7.1 البلاغ — `report_cmd` / `ReportReasonModal` / `ReportButtonView` / `ReportPlayerSelectView`
| الحالة | النص/العنوان | اللون | عمر |
|---|---|---|---|
| missing | `❌ Missing User` (Usage) | `error` | 15 |
| self | `❌ لا يمكنك البلاغ عن نفسك` | `error` | 10 |
| bot | `❌ لا يمكنك البلاغ عن بوت` | `error` | 10 |
| already | `⚠️ بلغت من قبل` | `warning` | 10 |
| نجاح | `⚠️ تم تسجيل البلاغ` — اللاعب/المبلّغ/السبب/الإجمالي + يتبقى للحظر | `warning`/`error` | — |
| modal déjà | `⚠️ بلغت من قبل` | `warning` | ephemeral |
| modal نجاح | `✅ تم تسجيل البلاغ` (نفس الجدول) | `warning` | ephemeral |
| زر | `⚠️ اختر اللاعب المُبلَّغ عنه` | `error` | ephemeral + Select |
| نص | `❌ لا يوجد لاعبون للبلاغ!` · `❌ ليست قائمتك!` | — | ephemeral |

### 7.2 قائمة بلاغات لاعب — `reports_cmd` (7413)
- `⚠️ بلاغات اللاعب — {name}` · اللاعب + الإجمالي + يتبقى/محظور + فاصل + حقل لكل مبلّغ · author `Player Reports` · `error`/`warning`

### 7.3 حظر/فك حظر — `banplayer_cmd` / `unbanplayer_cmd` / `banned_cmd`
| الأمر | العنوان | الوصف | اللون |
|---|---|---|---|
| `!!banplayer` | `🚫 تم حظر اللاعب` | اللاعب/حظره/السبب/عدد البلاغات/فويس التفتيش | `error` |
| `!!unbanplayer` | `✅ تم فك الحظر` | اللاعب/فك الحظر/مسح البلاغات | `success` |
| `!!banned` | `📋 قائمة المحظورين` | الإجمالي + حقل لكل لاعب | `error`/`success` |
| نص | `❌ لا يمكنك حظر نفسك!` | — | 10 |

### 7.4 فويسات التفتيش — `setreportchannel_cmd` / `removereportchannel_cmd` / `reportchannels_cmd`
| الأمر | العنوان | الوصف | اللون |
|---|---|---|---|
| `!!setreportchannel` | `🎤 فويسات التفتيش` | الفويس + أُضيف/موجود + القائمة | `success`/`warning` |
| `!!removereportchannel` | `🗑️ حذف فويس التفتيش` | الفويس + حُذف/غير موجود + المتبقية | `success`/`warning` |
| `!!reportchannels` | `📋 فويسات التفتيش المحددة` | الإجمالي + حقل لكل فويس (أو محذوف) | `info` |

---

## 8. نظام السجن (JAIL)

| الأمر | العنوان | الوصف | اللون |
|---|---|---|---|
| `!!jail` (missing) | `❌ Missing User` | الاستخدام | `error` |
| `!!jail` (not member) | `❌ اللاعب غير موجود في السيرفر` | — | `error` |
| `!!jail` ✓ | `🔒 تم إرسال اللاعب للسجن` | اللاعب/الأدمن/السبب + مكان السجن + فويس السجن + لفك السجن | `error` |
| `!!jail` (داخل السجن) | `🔒 مرحباً بك في السجن` | أنت في السجن + السبب + يمكنك الكلام + ارفع الأدلة | `warning` |
| `!!unjail` (missing) | `❌ Missing User` | الاستخدام | `error` |
| `!!unjail` (not member) | `ℹ️ اللاعب غير موجود` | — | `info` |
| `!!unjail` ✓ | `✅ تم فك السجن` | اللاعب/الأدمن/حر الآن | `success` |
| نص | `❌ لا يمكنك سجن بوت!` · `❌ لم أستطع إنشاء نظام السجن!` · `❌ نظام السجن غير مُفعّل!` · `ℹ️ {member} ليس في السجن!` · `❌ لم أستطع إعطاء/إزالة الـ role!` | — | 10-15 |

---

## 9. نظام البلاك ليست (BLACKLIST)

| الأمر/المسار | العنوان | الوصف | اللون | ملاحظة |
|---|---|---|---|---|
| `!!blacklist` (missing) | `❌ Missing User` | الاستخدام | `error` | 15 |
| `!!blacklist` (self/bot) | `❌ لا يمكنك بلاك ليست نفسك!/بوت!` | — | — | 10 |
| `!!blacklist` (فشل) | `❌ فشل` | لم أستطع التطبيق | `error` | 10 |
| `!!blacklist` ✓ | `🔇 تمت إضافة اللاعب للبلاك ليست` | اللاعب/بواسطة/السبب/المدة 10 دقائق | `warning` | — |
| `!!unblacklist` (missing) | `❌ Missing User` | الاستخدام | `error` | 15 |
| `!!unblacklist` ✓ | `✅ تمت إزالة البلاك ليست` | اللاعب/بواسطة/يمكنه الاستخدام | `success` | — |
| `!!blacklisted` | `📋 قائمة البلاك ليست` | الإجمالي + حقل لكل لاعب | `warning`/`success` | — |
| قناة `🔇・Blacklisted` | `🔇 Blacklisted Players` | الإجمالي + فاصل + حقل لكل لاعب (Name/reason/expiry) | `warning`/`success` | author `🔇 Blacklist`، تُحدَّث تلقائياً |
| رسالة الحظر أثناء اللعب | `🚫 أنت محظور من اللعب` | السبب/البلاغات/التفتيش | `error` | — |
| `on_command_error` | `🔇 أنت في البلاك ليست` | ممنوع استخدام البوت 10 دقائق | `error` | 15 |

**ملاحظة مهمة:** بعد تعديل `859ca0a`، **تنبيهات `notify_admins` تُرسَل إلى قناة `🔇・Blacklisted`** (بدل `match-results`).

### 9.1 تنبيهات الأدمن (notify_admins — سطر 790)
- العنوان: `⚠️ {title}` · الوصف: `{admin_mention_str}\n{description}` · author `Admin Alert` · footer `BOT_FOOTER • Action required` · اللون افتراضيًا `error`
- يُرسَل كـ `channel.send(content=admin_mention_str, embed=embed)` — mentions في المحتوى.

---

## 10. أوامر النتيجة الإدارية (MVP يدوي / Vote)

| الأمر | العنوان | الوصف | اللون |
|---|---|---|---|
| `!!w` (missing) | `❌ Missing` | الاستخدام | `error` |
| `!!w` (not active) | `❌ Lobby not active` | اللوبي ليس في تصويت | `error` |
| `!!w` (not in match) | `❌ لاعب غير موجود في الماتش` | — | `error` |
| `!!w` ✓ | `✅ تم تعيين MVP WINNER` | MVP + Lobby | `success` |
| `!!l` (missing/not active/not in match) | مثل `!!w` | — | `error` |
| `!!l` ✓ | `✅ تم تعيين MVP LOSER` | MVP + Lobby | `success` |
| `!!startvote` (missing) | `❌ Missing Lobby ID` | الاستخدام | `error` (15) |
| `!!startvote` (not found) | `❌ Not Found` | اللوبي غير موجود | `error` (10) |
| `!!startvote` (not active) | `❌ Not Active` | الحالة الحالية | `error` (10) |
| `!!startvote` ✓ | `🗳️ تم بدء التصويت!` | تجاوز 10 دقائق | `success` |
| `!!resolve` (missing/invalid/no dispute) | `❌ Missing` / `❌ Invalid` / `❌ No Dispute` | — | `error` |
| `!!resolve` ✓ | `⚖️ Resolved!` | الأدمن حسم الفائز | `success` |
| `_apply_admin_mvp` | `❌ MVP من نفس الفريق!` | WINNER/LOSER من فريقين مختلفين | `error` |
| `_apply_admin_mvp` | `⚙️ جارٍ تطبيق النقاط...` | Winner Team + MVPWINNER + MVPLOSER | `success` |
| `_apply_admin_mvp` ✗ | `❌ فشل تطبيق النقاط` | الخطأ + أن الماتش انتهى | `error` |

---

## 11. Cloud / Owner

| الأمر | العنوان | الوصف | اللون |
|---|---|---|---|
| `!!cloudbackup` (معطّل) | `☁️ Cloud Backup` | Cloud backup not enabled | `error` |
| `!!cloudbackup` ✓ | `☁️ Cloud Backup` | `{✅/❌} {msg}` | حسب النتيجة |
| `!!cloudrestore` (معطّل) | `☁️ Cloud Restore` | not enabled | `error` |
| `!!cloudrestore` (تأكيد) | `⚠️ Cloud Restore` | تحذير حذف البيانات + تفاعل ✅/❌ | `warning` |
| `!!cloudrestore` ✓ | `☁️ Cloud Restore` | `{✅/❌} {msg}` | حسب النتيجة |
| `!!cloudstatus` | `☁️ Cloud Status` | الحالة | `info` |
| `!!cloudbackup` بدء | نص | `☁️ Starting full cloud backup...` | — |
| `!!cloudrestore` إلغاء/مهلة/بدء | نص | `❌ Cancelled.` / `⏰ Timed out.` / `☁️ Restoring from cloud...` | — |

### 11.1 `!!serverleave` (DM فقط، للمالك) — كلها نصوص
- `❌ هذا الأمر يعمل في الـ DM فقط!` · `❌ هذا الأمر لصاحب البوت فقط!` · `البوت لا يوجد في أي سيرفر.` · قائمة السيرفرات (نص mult-line) · `❌ ID غير صحيح...` · `❌ السيرفر {id} غير موجود.` · `✅ تم مغادرة السيرفر **{name}** بنجاح!` · `❌ فشل مغادرة السيرفر: {e}`

---

## 12. المعالجة العامة والرسائل الأمنية

| المسار | النص/العنوان | اللون | ملاحظة |
|---|---|---|---|
| DM | `📡 الأوامر داخل السيرفر فقط` | `info` | `delete_after=20` |
| قناة غير مسموحة | `❌ Not Allowed Here` (reply) | `error` | `delete_after=10` |
| Cooldown | `⏳ Cooldown` | `warning` | — |
| No permission | `❌ No Permission` | `error` | — |
| guild=None | `create_mode_lobby`: `❌ Not Allowed Here` | `error` | 15 |

---

## 13. قنوات النظام المُدارة تلقائياً

| القناة | Embed | المُحدِّث |
|---|---|---|
| `🔇・Blacklisted` | `🔇 Blacklisted Players` | `update_blacklist_channel` (auto_setup / `!!setup` / كل تغيير بلاك ليست) |
| Leaderboard | `◆ Free Fire — Top 10 Players` (author `🏆 {guild.name} Leaderboard`) | `update_leaderboard_channel` |
| `match-results` | `🏅 Match Result — #{id}` (نتائج الماتش فقط) | `_post_match_result` |
| `RULES_CHANNEL_NAME` | `🛡️ قواعد السيرفر` | `ensure_rules_channel` |

---

## 14. ملخّص إحصائي

- **قوالب Embed فريدة (مواقع الإنشاء):** 168
- **مواقع الإرسال/التحرير (`send`/`reply`/`edit`):** ~201
- **ردود `interaction.response.send_message` (معظمها ephemeral):** ~70
- **ردود نصية بحتة (بدون embed):** ~30 (رسائل تحقق، أخطاء، `serverleave`، cloud status)
- **Views:** 11 (منها 2 غير مُفعّلة: `VoteView`, `MvpSelectionView`) · **Modals:** 4
- **ألوان مستخدمة:** `success/error/warning/info/play/profile/leaderboard/match/admin/vote/auto` + `0xFF6B00` + `0xE74C3C` + `0xFFD700`

> **لأي تحسين قادم:** عدّل القالب في موقعه (خط الأرقام مذكور لكل قسم) ثم أعد فحص `apply_branding`/`separator`/`COLORS` لتوحيد الشكل.
