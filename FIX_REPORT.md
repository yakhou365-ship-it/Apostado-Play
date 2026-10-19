# Fix report

## Applied
1. matches_hosted duplicates removed: CREATE TABLE (was L886-887), _migrate entry (was L976/978), create_lobby increment (was +2). Checks return 1/1/1.
2. setup_jail_system replaced with fix v2 (validates role + category + both channels, no "Free Fire Text" fallback, logger.warning on failures, no bare except). The persistent `jail_setup_done` marker was kept.
3. JAIL_CHAT_NAME = "・💬jail-chat", JAIL_PROUVES_NAME = "・💬jail-prouves".
4. TEXT/VOICE_PATTERNS: forbidden patterns absent; Arabic user patterns (قوانين, انتظار, خاص, تفتيش, أدمن) restored (they had been stripped).
5. 482 garbled/Arabic comments rewritten in clean English (0 mixed-script lines remain).
6. Stale comment claiming a hard-coded token removed (no token is in the code; scan found none).
7. UI text repair (see below), command docstrings rewritten, blacklist embed now shows `BLACKLIST_DURATION//60` minutes instead of a stale "10".

## Important finding: UI text was damaged by the previous pass
The earlier "translation" deleted Arabic words instead of translating them, leaving fragments such as `"🎯 : **"`, emoji-only field names and help lines without descriptions. About 300 user-facing lines were reconstructed in English from surrounding code. The original Arabic was not available, so wording is inferred; please review in Discord.

## Not done / limits
- Nothing was run against Discord (no token/network). Only py_compile, AST and text checks.
- Some internal helper docstrings (developer-only, never shown to users) still have missing words.
- Unusual damaged strings that have no punctuation artifact may remain undetected.
- cloud_backup.py was not modified (all 16 required sync/restore functions already exist).
