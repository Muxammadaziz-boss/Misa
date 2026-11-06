# ========== core/v8/universal_bot.py ==========
# Phase 39 — Universal Telegram Bot ↔ Misa User App
# Multi-User Universal Telegram Bot Dispatcher
# Strict isolation by numeric telegram_user_id, zero PC connection in Phase 39

import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union

from core.v8.telegram_gateway import TelegramTransport, MockTelegramTransport
from core.v8.telegram_identity import TelegramIdentityManager, TelegramIdentity
from core.v8.account_device import AccountDeviceManager

logger = logging.getLogger("core.v8.universal_bot")


class UniversalTelegramBot:
    """
    Universal Telegram Bot for multi-user identity resolution & account linking.
    One bot serving many Telegram users and many Misa accounts.
    Strictly isolated by canonical numeric Telegram user ID.
    """

    OTP_REGEX = re.compile(r"^\s*`?(\d{3}[\s-]?\d{3})`?\s*$")

    def __init__(
        self,
        transport: Optional[TelegramTransport] = None,
        identity_manager: Optional[TelegramIdentityManager] = None,
        account_device_manager: Optional[AccountDeviceManager] = None,
        bot_username: str = "Misa_ai_agent_bot"
    ):
        self.transport: TelegramTransport = transport or MockTelegramTransport()
        self.identity_mgr: TelegramIdentityManager = identity_manager or TelegramIdentityManager.get_default_instance()
        self.account_device_mgr: AccountDeviceManager = account_device_manager or AccountDeviceManager.get_default_instance()
        self.bot_username: str = (bot_username or "Misa_ai_agent_bot").lstrip("@").strip() or "Misa_ai_agent_bot"

    def _get_link(self, tg_user_id: int):
        link = self.identity_mgr.get_link_by_telegram_user(tg_user_id)
        return link if (link and link.is_active) else None

    def _get_active_device(self, link):
        if not link:
            return None
        dev = self.account_device_mgr.get_selected_device(link.misa_user_id)
        if not dev:
            devices = self.account_device_mgr.get_devices_for_user(link.misa_user_id, include_revoked=False)
            if devices:
                dev = devices[0]
                self.account_device_mgr.select_device(link.misa_user_id, dev.device_id)
        return dev

    @staticmethod
    def _format_error_msg(msg: str) -> str:
        """Wrap error code prefix (e.g. INVALID_OTP) in backticks so underscores never break Telegram Markdown."""
        raw = str(msg or "").strip()
        if ":" in raw:
            code_part, desc_part = raw.split(":", 1)
            return f"`{code_part.strip()}`: {desc_part.strip()}"
        return f"`{raw}`" if "_" in raw else raw

    @staticmethod
    def _extract_cmd_arg(text: str, cmd: str) -> Optional[str]:
        """Match /cmd or /cmd@BotUsername and return argument string (or None if not matching)."""
        pattern = rf"^/{re.escape(cmd)}(?:@[A-Za-z0-9_]+)?(?:[\s:]+([\s\S]*)|$)"
        m = re.match(pattern, text.strip(), flags=re.IGNORECASE)
        if not m:
            return None
        return (m.group(1) or "").strip()

    async def process_update(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Ingest and process a single Telegram update dictionary.
        Extracts user metadata, canonical numeric ID, and dispatches to handler.
        """
        if "callback_query" in update and isinstance(update["callback_query"], dict):
            cq = update["callback_query"]
            cq_id = str(cq.get("id", ""))
            if cq_id:
                await self.transport.answer_callback_query(cq_id)
            cq_msg = cq.get("message", {}) if isinstance(cq.get("message"), dict) else {}
            cq_chat = cq_msg.get("chat", {}) if isinstance(cq_msg.get("chat"), dict) else {}
            cq_from = cq.get("from", {}) if isinstance(cq.get("from"), dict) else {}
            cq_data = str(cq.get("data", "")).strip()
            is_valid_cq_id, cq_tg_id = TelegramIdentity.validate_user_id(cq_from.get("id") or cq_chat.get("id"))
            if is_valid_cq_id and cq_tg_id and cq_data:
                return await self.handle_message(
                    chat_id=cq_chat.get("id") or cq_tg_id,
                    tg_user_id=cq_tg_id,
                    first_name=cq_from.get("first_name"),
                    username=cq_from.get("username"),
                    text=cq_data
                )
            return {"ok": True, "callback_answered": True}

        message = update.get("message") or update.get("edited_message")
        if not message:
            return None

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        from_user = message.get("from", {})
        if isinstance(from_user, dict) and from_user.get("is_bot") is True:
            logger.warning("[UniversalBot] Rad etildi: bot hisobidan kelgan xabar")
            return None

        raw_tg_id = from_user.get("id") or chat_id

        # Validate positive numeric Telegram User ID
        is_valid_id, tg_user_id = TelegramIdentity.validate_user_id(raw_tg_id)
        if not is_valid_id or tg_user_id is None:
            logger.warning(f"[UniversalBot] Rad etildi: yaroqsiz Telegram ID '{raw_tg_id}'")
            return None

        first_name = from_user.get("first_name")
        username = from_user.get("username")
        text = str(message.get("text", "")).strip()
        voice = message.get("voice") or message.get("audio")

        # Update or register identity
        self.identity_mgr.register_or_update_identity(
            telegram_user_id=tg_user_id,
            first_name=first_name,
            username=username
        )

        if not text and voice:
            return await self._handle_voice_update(
                chat_id=chat_id or tg_user_id,
                tg_user_id=tg_user_id,
                voice=voice
            )

        return await self.handle_message(
            chat_id=chat_id or tg_user_id,
            tg_user_id=tg_user_id,
            first_name=first_name,
            username=username,
            text=text
        )

    async def _handle_voice_update(
        self,
        chat_id: Union[int, str],
        tg_user_id: int,
        voice: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ovozli xabarni qabul qilish va qayta ishlash"""
        link = self.identity_mgr.get_link_by_telegram_id(tg_user_id)
        if not link or not link.is_active:
            return await self._send_reply(
                chat_id,
                "🔒 *Misa Bot:* Ovozli xabarni qabul qildim, lekin Telegram hisobingiz Misa bilan bog'lanmagan.\n"
                "Iltimos, avval Misa ilovasida ko'rsatilgan 6 xonali kodni yuboring."
            )

        duration = voice.get("duration", 0)
        return await self._send_reply(
            chat_id,
            f"🎙 *Ovozli xabar qabul qilindi* ({duration} soniya).\n\n"
            "Misa ovozli tahlil tizimi faol. Agar Whisper yoki STT plaginlari sozlanmagan bo'lsa, iltimos buyruqni matn ko'rinishida yuboring."
        )

    async def handle_message(
        self,
        chat_id: Union[int, str],
        tg_user_id: int,
        first_name: Optional[str],
        username: Optional[str],
        text: str
    ) -> Dict[str, Any]:
        """
        Route message according to commands, raw OTP, or natural text.
        Multi-user isolated: state and context strictly keyed by tg_user_id.
        """
        if not text:
            return await self._send_reply(chat_id, "Iltimos, matnli buyruq yoki tasdiqlash kodini yuboring.")

        # 1. /start [token]
        start_arg = self._extract_cmd_arg(text, "start")
        if start_arg is not None:
            logger.info(f"[UniversalBot] Handling /start for tg_user_id={tg_user_id} (has_token={bool(start_arg)})")
            return await self._handle_start(chat_id, tg_user_id, first_name, username, start_arg)

        # 2. /link [code] or /pair [code]
        link_arg = self._extract_cmd_arg(text, "link")
        if link_arg is None:
            link_arg = self._extract_cmd_arg(text, "pair")
        if link_arg is not None:
            cleaned_code = link_arg.strip().strip("`").strip()
            if cleaned_code.startswith("<") and cleaned_code.endswith(">"):
                cleaned_code = cleaned_code[1:-1].strip()
            if cleaned_code.lower() in ("kod", "code", "otp"):
                cleaned_code = ""
            elif cleaned_code.upper().startswith("MK-"):
                cleaned_code = cleaned_code.upper()
            else:
                cleaned_code = TelegramIdentityManager.normalize_otp_input(cleaned_code)
            logger.info(f"[UniversalBot] Handling /link or /pair for tg_user_id={tg_user_id} (has_code={bool(cleaned_code)})")
            return await self._handle_link(chat_id, tg_user_id, first_name, username, cleaned_code)

        # 3. Raw 6-digit numeric OTP entry (e.g. 583921, 583 921, `583921`)
        match_otp = self.OTP_REGEX.match(text)
        if match_otp:
            code = TelegramIdentityManager.normalize_otp_input(match_otp.group(1))
            logger.info(f"[UniversalBot] Handling raw 6-digit OTP input for tg_user_id={tg_user_id}")
            return await self._handle_link(chat_id, tg_user_id, first_name, username, code)

        # 4. /unlink or /unpair
        if self._extract_cmd_arg(text, "unlink") is not None or self._extract_cmd_arg(text, "unpair") is not None:
            return await self._handle_unlink(chat_id, tg_user_id)

        # 5. /account
        if self._extract_cmd_arg(text, "account") is not None:
            return await self._handle_account(chat_id, tg_user_id, first_name, username)

        # 6. /devices (Phase 40)
        if self._extract_cmd_arg(text, "devices") is not None:
            return await self._handle_devices(chat_id, tg_user_id)

        # 7. /select <query> (Phase 40)
        select_arg = self._extract_cmd_arg(text, "select")
        if select_arg is not None:
            return await self._handle_select(chat_id, tg_user_id, select_arg)

        # 8. /status
        if self._extract_cmd_arg(text, "status") is not None:
            return await self._handle_status(chat_id, tg_user_id)

        # 9. /session (Phase 40+ remote session inspection)
        if self._extract_cmd_arg(text, "session") is not None:
            return await self._handle_session(chat_id, tg_user_id)

        # 10. /logout or /lock (remote session only — not web Supabase session)
        if self._extract_cmd_arg(text, "logout") is not None or self._extract_cmd_arg(text, "lock") is not None:
            return await self._handle_logout(chat_id, tg_user_id)

        # 11. /access (Phase 47 - Agent Access Status)
        if self._extract_cmd_arg(text, "access") is not None:
            return await self._handle_access(chat_id, tg_user_id)

        # 12. /permissions (Phase 47 - List all permissions)
        if self._extract_cmd_arg(text, "permissions") is not None:
            return await self._handle_permissions(chat_id, tg_user_id)

        # 13. /revoke (Phase 47 - Emergency Revoke All)
        if self._extract_cmd_arg(text, "revoke") is not None:
            return await self._handle_revoke(chat_id, tg_user_id)

        # 14. /help
        if self._extract_cmd_arg(text, "help") is not None:
            return await self._handle_help(chat_id, first_name)

        # 15. Remote Control Commands (/sysinfo, /info, /sys, /apps, /network, /files, /screenshot, /open, /close, /sleep, /restart, /shutdown, /confirm, /cancel)
        for sys_cmd in ("sysinfo", "system_info", "info", "sys"):
            if self._extract_cmd_arg(text, sys_cmd) is not None:
                return await self._handle_remote_tool(chat_id, tg_user_id, "system.info", {})

        if self._extract_cmd_arg(text, "apps") is not None:
            return await self._handle_remote_tool(chat_id, tg_user_id, "app.list", {})

        if self._extract_cmd_arg(text, "network") is not None:
            return await self._handle_remote_tool(chat_id, tg_user_id, "network.info", {})

        files_arg = self._extract_cmd_arg(text, "files")
        if files_arg is not None:
            return await self._handle_remote_tool(chat_id, tg_user_id, "file.list", {"path": files_arg} if files_arg else {})

        if self._extract_cmd_arg(text, "screenshot") is not None:
            return await self._handle_remote_tool(chat_id, tg_user_id, "system.screenshot", {})

        for open_cmd in ("open", "launch", "run"):
            open_arg = self._extract_cmd_arg(text, open_cmd)
            if open_arg is not None:
                if not open_arg:
                    return await self._send_reply(
                        chat_id,
                        "ℹ️ *Ilova nomini kiriting.*\nFoydalanish: `/open <ilova_nomi>`\nRuxsat etilgan ilovalar: `calculator`, `notepad`, `explorer`, `browser`"
                    )
                return await self._handle_remote_tool(chat_id, tg_user_id, "app.launch", {"app_name": open_arg.strip().lower()})

        close_arg = self._extract_cmd_arg(text, "close")
        if close_arg is not None:
            if not close_arg:
                return await self._send_reply(chat_id, "ℹ️ *Yopiladigan ilova nomini kiriting.*\nFoydalanish: `/close <ilova_nomi>`")
            return await self._handle_remote_tool(chat_id, tg_user_id, "app.close", {"app_name": close_arg.strip().lower()})

        if self._extract_cmd_arg(text, "sleep") is not None:
            return await self._handle_remote_tool(chat_id, tg_user_id, "power.sleep", {})

        if self._extract_cmd_arg(text, "restart") is not None:
            return await self._handle_remote_tool(chat_id, tg_user_id, "power.restart", {})

        if self._extract_cmd_arg(text, "shutdown") is not None:
            return await self._handle_remote_tool(chat_id, tg_user_id, "power.shutdown", {})

        confirm_arg = self._extract_cmd_arg(text, "confirm")
        if confirm_arg is not None:
            return await self._handle_remote_confirm(chat_id, tg_user_id, confirm_arg)

        cancel_arg = self._extract_cmd_arg(text, "cancel")
        if cancel_arg is not None:
            return await self._handle_remote_cancel(chat_id, tg_user_id, cancel_arg)

        # 16. Natural language remote control & AI response for linked users
        link = self._get_link(tg_user_id)
        if link and not text.startswith("/"):
            return await self._handle_natural_message(chat_id, tg_user_id, link, text)

        # Fallback for unrecognized text
        return await self._send_reply(
            chat_id,
            "Tushunarsiz buyruq. Misa hisobingizni bog'lash uchun 6 xonali kodni yuboring yoki /help buyrug'idan foydalaning."
        )

    async def _handle_start(
        self,
        chat_id: Union[int, str],
        tg_user_id: int,
        first_name: Optional[str],
        username: Optional[str],
        token: str
    ) -> Dict[str, Any]:
        """Handle /start or deep link /start <link_token>."""
        if token:
            ok, msg, link = self.identity_mgr.verify_link_token(
                link_token=token,
                telegram_user_id=tg_user_id,
                first_name=first_name,
                username=username
            )
            logger.info(f"[UniversalBot] Deep-link verification for tg_user_id={tg_user_id}: ok={ok}")
            if ok and link:
                text = (
                    "🎉 *Tabriklaymiz!*\n\n"
                    f"Sizning Telegram hisobingiz Misa hisobingiz (`{link.misa_user_id}`) bilan "
                    "muvaffaqiyatli bog'landi.\n\n"
                    "Holatni tekshirish uchun: /account"
                )
                return await self._send_reply(chat_id, text)
            else:
                safe_msg = self._format_error_msg(msg)
                text = f"❌ *Bog'lanishda xatolik:*\n{safe_msg}\n\nIltimos, yangi havola oling yoki 6 xonali koddan foydalaning."
                return await self._send_reply(chat_id, text)

        # Standard /start welcome message
        name = str(first_name or "foydalanuvchi").replace("_", "\\_").replace("*", "\\*").replace("`", "")
        welcome_text = (
            f"👋 *Assalomu alaykum, {name}!*\n\n"
            "Misa AI Universal Telegram Botiga xush kelibsiz.\n"
            f"🆔 Sizning Telegram ID: `{tg_user_id}`\n\n"
            "Ushbu bot orqali Misa profilingizni xavfsiz bog'lashingiz mumkin.\n\n"
            "📱 *Bog'lash uchun:*\n"
            "1. Misa ilovasida 'Telegram' bo'limiga o'ting.\n"
            "2. 6 xonali ulanish kodini oling.\n"
            "3. Kodni ushbu botga to'g'ridan-to'g'ri yuboring (masalan: `123456`) "
            "yoki `/link 123456` buyrug'idan foydalaning.\n\n"
            "Yordam uchun: /help"
        )
        return await self._send_reply(chat_id, welcome_text)

    async def _handle_link(
        self,
        chat_id: Union[int, str],
        tg_user_id: int,
        first_name: Optional[str],
        username: Optional[str],
        code: str
    ) -> Dict[str, Any]:
        """Handle /link <code>, /pair <code>, or raw OTP."""
        if not code:
            prompt_text = (
                "ℹ️ *Tasdiqlash kodi talab qilinadi.*\n\n"
                f"🆔 Sizning Telegram ID: `{tg_user_id}`\n"
                "Iltimos, Misa ilovasida ko'rsatilgan 6 xonali tasdiqlash kodini kiriting:\n"
                "Misol: `/link 583921` yoki shunchaki `583921`"
            )
            return await self._send_reply(chat_id, prompt_text)

        if code.upper().startswith("MK-"):
            try:
                from core.v8.user_linking import UserLinkingStore
                linking = UserLinkingStore.get_default_instance()
                ok_pair, msg_pair, ulink = linking.redeem_pairing_code(code.upper(), str(tg_user_id))
                if ok_pair and ulink:
                    reply_text = (
                        "✅ *Qurilma muvaffaqiyatli bog'landi!*\n\n"
                        f"💻 Qurilma ID: `{ulink.device_id}`\n"
                        f"🆔 Telegram ID: `{tg_user_id}`\n"
                        "🔒 Masofaviy boshqaruv tayyor.\n\n"
                        "Hisob tafsilotlari: /account"
                    )
                    return await self._send_reply(chat_id, reply_text)
            except Exception as e:
                logger.debug(f"[UniversalBot] MK pairing code check failed: {e}")

        ok, msg, link = self.identity_mgr.verify_otp(
            otp=code,
            telegram_user_id=tg_user_id,
            first_name=first_name,
            username=username
        )
        logger.info(f"[UniversalBot] OTP verification for tg_user_id={tg_user_id}: ok={ok}")

        if ok and link:
            reply_text = (
                "✅ *Hisob muvaffaqiyatli bog'landi!*\n\n"
                f"👤 Misa User ID: `{link.misa_user_id}`\n"
                f"🆔 Telegram ID: `{tg_user_id}`\n"
                "🔒 Ulanish xavfsizlandi.\n\n"
                "Hisob tafsilotlari: /account"
            )
            return await self._send_reply(chat_id, reply_text)
        else:
            safe_msg = self._format_error_msg(msg)
            reply_text = (
                f"❌ *Bog'lanish muvaffaqiyatsiz:*\n{safe_msg}\n\n"
                "Iltimos, kodni tekshirib qayta kiriting yoki yangi kod generatsiya qiling."
            )
            return await self._send_reply(chat_id, reply_text)

    async def _handle_unlink(self, chat_id: Union[int, str], tg_user_id: int) -> Dict[str, Any]:
        """Handle /unlink to revoke Telegram account link."""
        unlinked = self.identity_mgr.unlink(telegram_user_id=tg_user_id)
        if unlinked:
            reply_text = (
                "🔓 *Hisob uzildi.*\n\n"
                "Sizning Telegram hisobingiz Misa ilovasidan muvaffaqiyatli uzildi.\n"
                "Qayta ulash uchun: `/link <kod>`"
            )
        else:
            reply_text = (
                "ℹ️ *Bog'lanish topilmadi.*\n\n"
                "Sizning Telegram hisobingiz Misa bilan bog'lanmagan."
            )
        return await self._send_reply(chat_id, reply_text)

    async def _handle_account(
        self,
        chat_id: Union[int, str],
        tg_user_id: int,
        first_name: Optional[str],
        username: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /account to inspect linking, identity, and device state."""
        link = self.identity_mgr.get_link_by_telegram_user(tg_user_id)
        ident = self.identity_mgr.get_identity(tg_user_id)

        if link and link.is_active:
            linked_dt = datetime.fromtimestamp(link.linked_at).strftime("%Y-%m-%d %H:%M:%S")
            uname = f"`@{ident.username}`" if (ident and ident.username) else (f"`@{username}`" if username else "Mavjud emas")
            devices = self.account_device_mgr.get_devices_for_user(link.misa_user_id, include_revoked=False)
            selected = self._get_active_device(link)
            selected_str = f"{selected.name} (`{selected.device_id}`)" if selected else "Tanlanmagan"

            text = (
                "👤 *Misa Hisob Ma'lumotlari:*\n\n"
                f"• Misa User ID: `{link.misa_user_id}`\n"
                f"• Telegram ID: `{tg_user_id}`\n"
                f"• Username: {uname}\n"
                f"• Bog'langan vaqt: `{linked_dt}`\n"
                f"• Holat: 🟢 Faol (Active)\n"
                f"• Ulangan kompyuterlar: {len(devices)} ta\n"
                f"• Faol tanlangan kompyuter: {selected_str}\n\n"
                "Qurilmalar ro'yxati: /devices\n"
                "Hisobni uzish uchun: /unlink"
            )
        else:
            text = (
                "👤 *Telegram Identifikatsiyasi:*\n\n"
                f"• Telegram ID: `{tg_user_id}`\n"
                f"• Holat: ⚪ Bog'lanmagan (Not Linked)\n\n"
                "Misa ilovangiz bilan bog'lash uchun:\n"
                "1. Misa ilovasida kod oling.\n"
                "2. Botga `/link <kod>` yuboring."
            )
        return await self._send_reply(chat_id, text)

    async def _handle_devices(self, chat_id: Union[int, str], tg_user_id: int) -> Dict[str, Any]:
        """Handle /devices to list user's owned devices and current selection."""
        link = self.identity_mgr.get_link_by_telegram_user(tg_user_id)
        if not link or not link.is_active:
            text = (
                "🔒 *Hisob bog'lanmagan.*\n\n"
                "Qurilmalarni ko'rish uchun avval Misa hisobingizni bog'lang:\n"
                "1. Misa ilovasidan 6 xonali kod oling.\n"
                "2. Botga `/link <kod>` yuboring."
            )
            return await self._send_reply(chat_id, text)

        devices = self.account_device_mgr.get_devices_for_user(link.misa_user_id, include_revoked=False)
        if not devices:
            text = (
                "💻 *Qurilmalar ro'yxati:*\n\n"
                "Sizning hisobingizga hozircha birorta ham kompyuter ulanmagan.\n"
                "Misa Desktop ilovasi orqali kompyuteringizni ro'yxatdan o'tkazing."
            )
            return await self._send_reply(chat_id, text)

        selected = self._get_active_device(link)
        selected_dev_id = selected.device_id if selected else None

        lines = ["💻 *Sizning Kompyuterlaringiz:*\n"]
        for idx, dev in enumerate(devices, start=1):
            status_dot = "🟢" if dev.is_online else ("🟡" if dev.status.lower() == "standby" else "⚪")
            selected_badge = " *(Faol)*" if (selected_dev_id and dev.device_id == selected_dev_id) else ""
            lines.append(f"{idx}. {status_dot} *{dev.name}*{selected_badge}")
            lines.append(f"   ID: `{dev.device_id}` | Holat: {dev.status.capitalize()}")

        lines.append("\nQurilmani tanlash uchun:\n`/select <nom_yoki_id>`")
        return await self._send_reply(chat_id, "\n".join(lines))

    async def _handle_select(self, chat_id: Union[int, str], tg_user_id: int, query: str) -> Dict[str, Any]:
        """Handle /select <name_or_id> to set user's active device."""
        link = self.identity_mgr.get_link_by_telegram_user(tg_user_id)
        if not link or not link.is_active:
            text = (
                "🔒 *Hisob bog'lanmagan.*\n\n"
                "Qurilmani tanlash uchun avval hisobingizni bog'lang: `/link <kod>`"
            )
            return await self._send_reply(chat_id, text)

        if not query:
            text = (
                "ℹ️ *Qurilma nomi yoki ID talab qilinadi.*\n\n"
                "Foydalanish: `/select <nom_yoki_id>`\n"
                "Mavjud qurilmalarni ko'rish uchun: /devices"
            )
            return await self._send_reply(chat_id, text)

        ok, msg, dev = self.account_device_mgr.select_device_by_query(link.misa_user_id, query)
        if ok and dev:
            text = (
                f"✅ *Faol qurilma tanlandi:*\n\n"
                f"• Nomi: *{dev.name}*\n"
                f"• Apparat ID: `{dev.device_id}`\n"
                f"• Holat: {dev.status.capitalize()}\n\n"
                "Barcha buyruqlar endi ushbu qurilmaga yo'naltiriladi."
            )
            return await self._send_reply(chat_id, text)
        else:
            safe_msg = self._format_error_msg(msg)
            text = f"❌ *Xatolik:*\n{safe_msg}\n\nQurilmalar ro'yxati: /devices"
            return await self._send_reply(chat_id, text)

    async def _handle_status(self, chat_id: Union[int, str], tg_user_id: int) -> Dict[str, Any]:
        """Handle /status — selected device state for linked users, bot health otherwise."""
        link = self.identity_mgr.get_link_by_telegram_user(tg_user_id)
        if link and link.is_active:
            dev = self._get_active_device(link)
            if not dev:
                text = (
                    "💻 *Qurilma holati:*\n\n"
                    "Faol tanlangan kompyuter yo'q.\n"
                    "Avval qurilmani tanlang: /devices → `/select <nom>`"
                )
                return await self._send_reply(chat_id, text)

            status_upper = dev.status.lower()
            if dev.is_revoked or status_upper == "revoked":
                state_label = "🔴 REVOKED"
            elif status_upper == "online":
                state_label = "🟢 ONLINE"
            elif status_upper in ("standby", "degraded"):
                state_label = "🟡 DEGRADED"
            else:
                state_label = "⚪ OFFLINE"

            last_seen = "Noma'lum"
            if dev.last_seen_at:
                last_seen = datetime.fromtimestamp(dev.last_seen_at).strftime("%Y-%m-%d %H:%M:%S")

            text = (
                "🖥️ *Tanlangan Qurilma Holati:*\n\n"
                f"• Nomi: *{dev.name}*\n"
                f"• Apparat ID: `{dev.device_id}`\n"
                f"• Holat: *{state_label}*\n"
                f"• Platforma: {dev.platform.capitalize()}\n"
                f"• Oxirgi faollik: `{last_seen}`\n\n"
                "Tizim resurslari: /sysinfo\n"
                "Sessiya holati: /session"
            )
            return await self._send_reply(chat_id, text)

        active_links = self.identity_mgr.count_active_links()
        pending_reqs = self.identity_mgr.count_pending_requests()
        text = (
            "🤖 *Misa Universal Telegram Bot Holati:*\n\n"
            "• Server: 🟢 Ishlamoqda (Online)\n"
            f"• Bot Username: `@{self.bot_username}`\n"
            f"• Faol ulanishlar: {active_links}\n"
            f"• Kutilayotgan so'rovlar: {pending_reqs}\n"
            "• Versiya: `v9.0.0 Phase 39 / Phase 40`"
        )
        return await self._send_reply(chat_id, text)

    async def _handle_session(self, chat_id: Union[int, str], tg_user_id: int) -> Dict[str, Any]:
        """Handle /session — remote control session presence (no secret/token exposure)."""
        link = self.identity_mgr.get_link_by_telegram_user(tg_user_id)
        if not link or not link.is_active:
            return await self._send_reply(
                chat_id,
                "🔒 *Hisob bog'lanmagan.*\n\nAvval hisobingizni bog'lang: `/link <kod>`"
            )

        dev = self._get_active_device(link)
        if not dev:
            return await self._send_reply(
                chat_id,
                "💻 *Faol qurilma tanlanmagan.*\n\nAvval kompyuteringizni tanlang: /devices"
            )

        from core.v8.auth_session import SessionManager
        session_mgr = SessionManager.get_default_instance()
        session = session_mgr.get_active_session(link.misa_user_id, dev.device_id)

        if session and session.is_valid():
            expires = datetime.fromtimestamp(session.expires_at).strftime("%Y-%m-%d %H:%M:%S")
            text = (
                "🔐 *Masofaviy Boshqaruv Sessiyasi:*\n\n"
                f"• Qurilma: *{dev.name}* (`{dev.device_id}`)\n"
                "• Holat: 🟢 *Faol*\n"
                f"• Tugash vaqti: `{expires}`\n\n"
                "Sessiyani yopish: /logout"
            )
        else:
            text = (
                "🔐 *Masofaviy Boshqaruv Sessiyasi:*\n\n"
                f"• Qurilma: *{dev.name}* (`{dev.device_id}`)\n"
                "• Holat: ⚪ *Faol emas*\n\n"
                "Masofaviy boshqaruv Misa Desktop/Web ilovasi orqali boshlanadi."
            )
        return await self._send_reply(chat_id, text)

    async def _handle_logout(self, chat_id: Union[int, str], tg_user_id: int) -> Dict[str, Any]:
        """Handle /logout — close remote session only (not Supabase web auth)."""
        link = self.identity_mgr.get_link_by_telegram_user(tg_user_id)
        if not link or not link.is_active:
            return await self._send_reply(
                chat_id,
                "🔒 *Hisob bog'lanmagan.*\n\nAvval hisobingizni bog'lang: `/link <kod>`"
            )

        dev = self._get_active_device(link)
        if not dev:
            return await self._send_reply(
                chat_id,
                "💻 *Faol qurilma tanlanmagan.*\n\nAvval kompyuteringizni tanlang: /devices"
            )

        from core.v8.auth_session import SessionManager
        session_mgr = SessionManager.get_default_instance()
        closed = session_mgr.close_session(link.misa_user_id, dev.device_id)

        if closed:
            text = (
                "🔓 *Masofaviy sessiya yopildi.*\n\n"
                f"• Qurilma: *{dev.name}* (`{dev.device_id}`)\n"
                "• Misa Web kirish sessiyasi saqlanib qoldi.\n\n"
                "Holatni tekshirish: /session"
            )
        else:
            text = (
                "ℹ️ *Faol masofaviy sessiya topilmadi.*\n\n"
                f"• Qurilma: *{dev.name}* (`{dev.device_id}`)\n"
                "Hech qanday ochiq remote session yo'q."
            )
        return await self._send_reply(chat_id, text)

    async def _handle_access(self, chat_id: Union[int, str], tg_user_id: int) -> Dict[str, Any]:
        """Phase 47: Show agent access level for active device."""
        link = self._get_link(tg_user_id)
        if not link:
            return await self._send_reply(chat_id, "❌ Telegram hisobingiz Misa'ga bog'lanmagan. /link buyrug'idan foydalaning.")

        dev = self._get_active_device(link)
        if not dev:
            return await self._send_reply(chat_id, "❌ Faol qurilma topilmadi. /select bilan tanlang.")

        from core.v8.agent_access import AgentAccessManager
        access_mgr = AgentAccessManager.get_default_instance()
        status = access_mgr.get_access_status(link.misa_user_id, dev.device_id)

        level = status.get("access_level", "LIMITED")
        level_icon = "🟢" if level == "FULL" else ("🟡" if level == "CUSTOM" else "🔴")
        granted = status.get("permissions_granted", 0)
        total = status.get("total_supported_permissions", 15)

        text = (
            f"🛡 *Agent Access Status*\n\n"
            f"• Qurilma: *{dev.name}* (`{dev.device_id}`)\n"
            f"• Daraja: {level_icon} *{level}*\n"
            f"• Ruxsatlar: {granted}/{total}\n"
            f"• Siyosat versiyasi: `{status.get('policy_version', '1.0.0')}`\n\n"
            "Batafsil: /permissions\n"
            "Bekor qilish: /revoke"
        )
        return await self._send_reply(chat_id, text)

    async def _handle_permissions(self, chat_id: Union[int, str], tg_user_id: int) -> Dict[str, Any]:
        """Phase 47: List all 15 permissions with status."""
        link = self._get_link(tg_user_id)
        if not link:
            return await self._send_reply(chat_id, "❌ Telegram hisobingiz Misa'ga bog'lanmagan.")

        dev = self._get_active_device(link)
        if not dev:
            return await self._send_reply(chat_id, "❌ Faol qurilma topilmadi. /select bilan tanlang.")

        from core.v8.permission_center import PermissionStore, STANDARD_PERMISSIONS
        store = PermissionStore.get_default_instance()
        profile = store.get_profile(link.misa_user_id, dev.device_id)

        lines = ["📋 *Ruxsatlar ro'yxati:*\n"]
        for perm in STANDARD_PERMISSIONS:
            granted = profile.is_granted(perm.id) if profile else perm.default_enabled
            icon = "✅" if granted else "❌"
            lines.append(f"  {icon} `{perm.id}` — {perm.label}")

        lines.append(f"\n🛡 Access Level: *{profile.access_level if profile else 'LIMITED'}*")
        return await self._send_reply(chat_id, "\n".join(lines))

    async def _handle_revoke(self, chat_id: Union[int, str], tg_user_id: int) -> Dict[str, Any]:
        """Phase 47: Emergency revoke all agent access."""
        link = self._get_link(tg_user_id)
        if not link:
            return await self._send_reply(chat_id, "❌ Telegram hisobingiz Misa'ga bog'lanmagan.")

        dev = self._get_active_device(link)
        if not dev:
            return await self._send_reply(chat_id, "❌ Faol qurilma topilmadi.")

        from core.v8.agent_access import AgentAccessManager
        access_mgr = AgentAccessManager.get_default_instance()
        ok, msg = access_mgr.emergency_revoke(link.misa_user_id, dev.device_id)

        if ok:
            text = (
                "🚨 *FAVQULODDA BEKOR QILISH BAJARILDI!*\n\n"
                f"• Qurilma: *{dev.name}*\n"
                "• Access level: LIMITED\n"
                "• Barcha pending buyruqlar bekor qilindi\n"
                "• Barcha confirmation tokenlar bekor qilindi\n\n"
                "Holatni tekshirish: /access"
            )
        else:
            text = f"⚠️ Bekor qilishda xatolik: {msg}"
        return await self._send_reply(chat_id, text)

    async def _handle_remote_tool(
        self,
        chat_id: Union[int, str],
        tg_user_id: int,
        tool_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute or queue a remote tool on the user's selected device."""
        link = self._get_link(tg_user_id)
        if not link:
            return await self._send_reply(
                chat_id,
                "🔒 *Hisob bog'lanmagan.*\n\nMasofaviy boshqaruv uchun avval hisobingizni bog'lang: `/link <kod>`"
            )

        dev = self._get_active_device(link)
        if not dev:
            return await self._send_reply(
                chat_id,
                "💻 *Faol qurilma topilmadi.*\n\nMisa Desktop ilovasini kompyuteringizda ishga tushiring va /devices buyrug'i bilan tekshiring."
            )

        from core.v8.permission_center import PermissionStore
        from core.v8.remote_tools import RemoteToolRegistry
        from core.v8.command_queue import CommandQueueManager

        registry = RemoteToolRegistry.get_default_instance()
        tool_def = registry.get_tool(tool_id)
        if not tool_def:
            return await self._send_reply(chat_id, f"❌ Noma'lum asbob: `{tool_id}`")

        perm_store = PermissionStore.get_default_instance()
        profile = perm_store.get_profile(link.misa_user_id, dev.device_id)
        req_perm = tool_def.required_permission
        if req_perm and profile and not profile.is_granted(req_perm):
            return await self._send_reply(
                chat_id,
                f"⛔ *Ruxsat berilmagan!*\n\n"
                f"• Qurilma: *{dev.name}*\n"
                f"• Talab qilingan ruxsat: `{req_perm}`\n\n"
                "Misa Desktop ilovasining *Masofaviy Boshqaruv* bo'limida ushbu ruxsatni yoqing."
            )

        latest_metrics = (dev.metadata or {}).get("latest_metrics") or {}

        # Immediate telemetry response if synced metrics are available on cloud or running locally
        if tool_id == "system.info" and latest_metrics:
            cpu = latest_metrics.get("cpu_percent", latest_metrics.get("cpu_usage_percent", "N/A"))
            ram_used = latest_metrics.get("ram_used_gb", "N/A")
            ram_total = latest_metrics.get("ram_total_gb", "N/A")
            disk_free = latest_metrics.get("disk_free_gb", "N/A")
            os_label = latest_metrics.get("os") or dev.platform.capitalize()
            local_ip = latest_metrics.get("local_ip", "127.0.0.1")
            text = (
                f"📊 *Tizim Ma'lumotlari — {dev.name}*\n\n"
                f"• Hostname: `{dev.hostname or dev.name}`\n"
                f"• Tizim: `{os_label}`\n"
                f"• CPU yuklamasi: `{cpu}%`\n"
                f"• Xotira (RAM): `{ram_used} GB / {ram_total} GB`\n"
                f"• Bo'sh disk (C:): `{disk_free} GB`\n"
                f"• Lokal IP: `{local_ip}`\n"
                f"• Holat: 🟢 Online"
            )
            return await self._send_reply(chat_id, text)

        if tool_id == "app.list" and latest_metrics.get("apps"):
            apps_list = latest_metrics.get("apps") or []
            lines = [f"🧩 *Ishlayotgan dasturlar — {dev.name}:*\n"]
            for idx, a in enumerate(apps_list[:20], start=1):
                aname = a.get("name") if isinstance(a, dict) else str(a)
                lines.append(f"{idx}. `{aname}`")
            return await self._send_reply(chat_id, "\n".join(lines))

        if tool_id == "network.info" and latest_metrics:
            local_ip = latest_metrics.get("local_ip", "127.0.0.1")
            mac = latest_metrics.get("mac_address", "N/A")
            up_mb = latest_metrics.get("upload_mb_s", 0.0)
            down_mb = latest_metrics.get("download_mb_s", 0.0)
            text = (
                f"🌐 *Tarmoq Holati — {dev.name}*\n\n"
                f"• Hostname: `{dev.hostname or dev.name}`\n"
                f"• Lokal IP: `{local_ip}`\n"
                f"• MAC Manzil: `{mac}`\n"
                f"• Yuklab olish (Download): `{down_mb} MB/s`\n"
                f"• Yuklash (Upload): `{up_mb} MB/s`\n"
                f"• Holat: 🟢 Ulangan"
            )
            return await self._send_reply(chat_id, text)

        # Queue the command for the PC Agent (and if running locally, execute immediately)
        cmd_mgr = CommandQueueManager.get_default_instance()
        risk_val = tool_def.risk_level.value if hasattr(tool_def.risk_level, "value") else str(tool_def.risk_level)
        try:
            cmd, token_obj = cmd_mgr.submit_command(
                device_id=dev.device_id,
                user_id=link.misa_user_id,
                tool_id=tool_id,
                params=params,
                origin="telegram",
                requires_confirmation=tool_def.requires_confirmation,
                risk_level=risk_val,
                telegram_user_id=str(tg_user_id)
            )
        except Exception as e:
            return await self._send_reply(chat_id, f"⚠️ Buyruqni yuborishda xatolik: {e}")

        if token_obj and cmd.requires_confirmation:
            text = (
                f"⚠️ *Tasdiqlash talab etiladi!*\n\n"
                f"• Qurilma: *{dev.name}*\n"
                f"• Amal: *{tool_def.name}* (`{tool_id}`)\n"
                f"• Xavf darajasi: `{risk_val.upper()}`\n\n"
                f"Tasdiqlash uchun 60 soniya ichida quyidagi buyruqni yuboring:\n"
                f"`/confirm {token_obj.token}`\n\n"
                f"Bekor qilish uchun:\n`/cancel {cmd.command_id}`"
            )
            return await self._send_reply(chat_id, text)

        text = (
            f"🚀 *Buyruq kompyuteringizga yuborildi!*\n\n"
            f"• Qurilma: *{dev.name}* (`{dev.device_id}`)\n"
            f"• Amal: *{tool_def.name}* (`{tool_id}`)\n"
            f"• Buyruq ID: `{cmd.command_id[:8]}`\n\n"
            "Natija kompyuteringiz bajargan zahoti shu yerga yuboriladi."
        )
        return await self._send_reply(chat_id, text)

    async def _handle_remote_confirm(self, chat_id: Union[int, str], tg_user_id: int, token_str: str) -> Dict[str, Any]:
        """Confirm a high-risk command via /confirm <token>."""
        link = self._get_link(tg_user_id)
        if not link:
            return await self._send_reply(chat_id, "🔒 *Hisob bog'lanmagan.*")

        token_clean = token_str.strip().strip("`").strip()
        if not token_clean:
            return await self._send_reply(chat_id, "ℹ️ Tasdiqlash tokenini kiriting: `/confirm <token>`")

        from core.v8.command_queue import CommandQueueManager
        cmd_mgr = CommandQueueManager.get_default_instance()
        token_obj = cmd_mgr._confirmations.get(token_clean)
        if not token_obj:
            return await self._send_reply(chat_id, "❌ Tasdiqlash tokeni topilmadi yoki muddati tugagan.")

        ok, msg = cmd_mgr.confirm_command(token_obj.command_id, token_clean, link.misa_user_id)
        if ok:
            return await self._send_reply(
                chat_id,
                f"✅ *Buyruq tasdiqlandi va navbatga qo'yildi!*\n• Buyruq ID: `{token_obj.command_id[:8]}`"
            )
        return await self._send_reply(chat_id, f"❌ Tasdiqlashda xatolik: {msg}")

    async def _handle_remote_cancel(self, chat_id: Union[int, str], tg_user_id: int, cmd_id_prefix: str) -> Dict[str, Any]:
        """Cancel a pending command via /cancel <cmd_id>."""
        link = self._get_link(tg_user_id)
        if not link:
            return await self._send_reply(chat_id, "🔒 *Hisob bog'lanmagan.*")

        clean_id = cmd_id_prefix.strip().strip("`").strip()
        from core.v8.command_queue import CommandQueueManager
        cmd_mgr = CommandQueueManager.get_default_instance()

        target_id = clean_id
        if clean_id and clean_id not in cmd_mgr._commands:
            for full_id, cobj in cmd_mgr._commands.items():
                if full_id.startswith(clean_id) and cobj.user_id == link.misa_user_id:
                    target_id = full_id
                    break

        if not target_id:
            return await self._send_reply(chat_id, "ℹ️ Bekor qilish uchun buyruq ID sini kiriting: `/cancel <id>`")

        ok, msg = cmd_mgr.cancel_command(target_id, link.misa_user_id)
        if ok:
            return await self._send_reply(chat_id, f"🛑 *Buyruq bekor qilindi:* `{target_id[:8]}`")
        return await self._send_reply(chat_id, f"❌ Xatolik: {msg}")

    async def _handle_natural_message(
        self,
        chat_id: Union[int, str],
        tg_user_id: int,
        link: Any,
        text: str
    ) -> Dict[str, Any]:
        """Route natural language remote commands or answer via AI for linked users."""
        lower = text.lower().strip()

        if any(k in lower for k in ("tizim holati", "kompyuter holati", "system info", "cpu", "ram", "resurs")):
            return await self._handle_remote_tool(chat_id, tg_user_id, "system.info", {})
        if any(k in lower for k in ("dasturlar", "ilovalar", "ishlayotgan dastur")):
            return await self._handle_remote_tool(chat_id, tg_user_id, "app.list", {})
        if any(k in lower for k in ("tarmoq", "ip manzil", "internet tezli")):
            return await self._handle_remote_tool(chat_id, tg_user_id, "network.info", {})
        if any(k in lower for k in ("skrinshot", "screenshot", "ekranni rasmga")):
            return await self._handle_remote_tool(chat_id, tg_user_id, "system.screenshot", {})
        if any(k in lower for k in ("fayllar", "papka")):
            return await self._handle_remote_tool(chat_id, tg_user_id, "file.list", {})
        if any(k in lower for k in ("kalkulyator", "calculator", "calc")):
            return await self._handle_remote_tool(chat_id, tg_user_id, "app.launch", {"app_name": "calculator"})
        if any(k in lower for k in ("bloknot", "notepad")):
            return await self._handle_remote_tool(chat_id, tg_user_id, "app.launch", {"app_name": "notepad"})
        if any(k in lower for k in ("provodnik", "explorer")):
            return await self._handle_remote_tool(chat_id, tg_user_id, "app.launch", {"app_name": "explorer"})
        if any(k in lower for k in ("brauzer", "chrome", "browser")):
            return await self._handle_remote_tool(chat_id, tg_user_id, "app.launch", {"app_name": "browser"})

        # Try AI Engine response if available
        try:
            from core import ai_engine
            if hasattr(ai_engine, "ai_mavjudmi") and ai_engine.ai_mavjudmi():
                import asyncio
                reply = await asyncio.to_thread(ai_engine.ai_javob_ol, text)
                if reply:
                    return await self._send_reply(chat_id, f"🤖 *Misa AI:*\n\n{reply}")
        except Exception as e:
            logger.debug(f"[UniversalBot] AI chat fallback error: {e}")

        dev = self._get_active_device(link)
        dev_str = f"*{dev.name}* (`{dev.device_id}`)" if dev else "Tanlanmagan (/devices)"
        return await self._send_reply(
            chat_id,
            f"🤖 *Misa Masofaviy Boshqaruv*\n\n"
            f"• Faol kompyuter: {dev_str}\n\n"
            "Tezkor buyruqlar:\n"
            "• `/sysinfo` — CPU, RAM, Disk va tizim holati\n"
            "• `/apps` — Ishlayotgan dasturlar ro'yxati\n"
            "• `/network` — IP manzil va tarmoq tezligi\n"
            "• `/open calculator` — Ilovani ishga tushirish\n"
            "• `/screenshot` — Ekranni rasmga olish\n"
            "• `/devices` — Ulangan kompyuterlar\n"
            "• `/help` — Barcha buyruqlar"
        )

    async def _handle_help(self, chat_id: Union[int, str], first_name: Optional[str]) -> Dict[str, Any]:
        """Handle /help command catalog."""
        help_text = (
            "📖 *Misa Telegram Bot Buyruqlari:*\n\n"
            "🔗 *Hisob va Qurilmalar:*\n"
            "• `/start` — Botni ishga tushirish va yo'riqnoma\n"
            "• `/link <kod>` — Misa 6 xonali kodi orqali bog'lash\n"
            "• `/unlink` — Telegram hisobini Misadan uzish\n"
            "• `/account` — Bog'langan hisob va qurilmalar tafsilotlari\n"
            "• `/devices` — Sizning barcha kompyuterlaringiz ro'yxati\n"
            "• `/select <nom>` — Masofaviy boshqaruv uchun faol kompyuterni tanlash\n\n"
            "🖥️ *Masofaviy Boshqaruv:*\n"
            "• `/status` — Tanlangan kompyuter va bot holati\n"
            "• `/sysinfo` — CPU, RAM, Disk va OS telemetriyasi\n"
            "• `/apps` — Ishlayotgan dasturlar ro'yxati\n"
            "• `/network` — Tarmoq va IP ma'lumotlari\n"
            "• `/files` — Foydalanuvchi fayllari ro'yxati\n"
            "• `/open <ilova>` — Ilovani ochish (`calculator`, `notepad`, `explorer`, `browser`)\n"
            "• `/close <ilova>` — Ilovani yopish\n"
            "• `/screenshot` — Ekran tasvirini olish\n"
            "• `/sleep` | `/restart` | `/shutdown` — Quvvat boshqaruvi\n\n"
            "🔐 *Xavfsizlik va Sessiya:*\n"
            "• `/session` — Masofaviy boshqaruv sessiyasi holati\n"
            "• `/logout` — Masofaviy sessiyani yopish (Web kirish saqlanadi)\n"
            "• `/access` — Agent vakolat darajasi (Phase 47)\n"
            "• `/permissions` — Barcha ruxsatlar ro'yxati\n"
            "• `/revoke` — 🚨 Favqulodda barcha vakolatlarni bekor qilish\n"
            "• `/help` — Ushbu yordam menyusi\n\n"
            "💡 *Maslahat:* 6 xonali tasdiqlash kodini to'g'ridan-to'g'ri xabar sifatida ham yuborishingiz mumkin (masalan: `583921`)."
        )
        return await self._send_reply(chat_id, help_text)

    async def _send_reply(self, chat_id: Union[int, str], text: str) -> Dict[str, Any]:
        """Internal helper to dispatch message via transport."""
        return await self.transport.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown"
        )
