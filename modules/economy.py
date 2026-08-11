import random
import logging
from datetime import datetime, timezone
from flask import request
from utils.api import api_request
from utils.helpers import is_admin, msg_id
from database.mongo import db

logger = logging.getLogger(__name__)

def _mid():
    return msg_id(request.json)

def economy_col():
    return db.economy


# ── Balance / Cash / Gems ─────────────────────────────────────────────────────

def handle_balance(chat_id: int, user_id: int, text: str):
    _show_balance(chat_id, user_id, text)

def handle_cash(chat_id: int, user_id: int, text: str):
    _show_balance(chat_id, user_id, text)

def handle_bal(chat_id: int, user_id: int, text: str):
    _show_balance(chat_id, user_id, text)

def _show_balance(chat_id: int, user_id: int, text: str):
    mid = _mid()
    message = request.json.get("message", {})
    target_id = user_id
    target_name = message.get("from", {}).get("first_name", "User")

    if message.get("reply_to_message"):
        target_id = message["reply_to_message"]["from"]["id"]
        target_name = message["reply_to_message"]["from"].get("first_name", "User")

    user_data = economy_col().find_one({"chat_id": chat_id, "user_id": target_id})
    cash = user_data.get("cash", 0) if user_data else 0
    gems = user_data.get("gems", 0) if user_data else 0
    bank = user_data.get("bank", 0) if user_data else 0

    api_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"👤 **{target_name}'s Profile:**\n\n💵 Cash: `{cash}` coins\n💎 Gems: `{gems}` gems\n🏦 Bank: `{bank}` coins",
        "parse_mode": "Markdown",
        "reply_to_message_id": mid,
    })


def handle_gems(chat_id: int, user_id: int, text: str):
    mid = _mid()
    message = request.json.get("message", {})
    target_id = user_id
    target_name = message.get("from", {}).get("first_name", "User")

    if message.get("reply_to_message"):
        target_id = message["reply_to_message"]["from"]["id"]
        target_name = message["reply_to_message"]["from"].get("first_name", "User")

    user_data = economy_col().find_one({"chat_id": chat_id, "user_id": target_id})
    gems = user_data.get("gems", 0) if user_data else 0

    api_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"💎 **{target_name}** ke paas `{gems}` gems hain.",
        "parse_mode": "Markdown",
        "reply_to_message_id": mid,
    })


# ── Daily Bonus ───────────────────────────────────────────────────────────────

def handle_daily(chat_id: int, user_id: int, text: str):
    mid = _mid()
    now = datetime.now(timezone.utc)
    
    user_data = economy_col().find_one({"chat_id": chat_id, "user_id": user_id})
    last_daily = user_data.get("last_daily") if user_data else None

    if last_daily:
        last_date = datetime.fromisoformat(last_daily)
        if (now - last_date).total_seconds() < 86400:
            remaining = int(86400 - (now - last_date).total_seconds())
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            api_request("sendMessage", {
                "chat_id": chat_id,
                "text": f"⏳ Aap apna daily bonus pehle hi claim kar chuke hain! Agla bonus `{hours}h {minutes}m` baad milega.",
                "parse_mode": "Markdown",
                "reply_to_message_id": mid,
            })
            return

    reward = 500
    gem_reward = 5
    economy_col().update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {
            "$inc": {"cash": reward, "gems": gem_reward},
            "$set": {"last_daily": now.isoformat()}
        },
        upsert=True
    )

    api_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"🎉 Badhai ho! Aapko daily reward mein `{reward}` cash aur `{gem_reward}` gems mil gaye hain.",
        "parse_mode": "Markdown",
        "reply_to_message_id": mid,
    })


# ── Work / Kil (Earn Cash & Gems) ─────────────────────────────────────────────

def handle_kil(chat_id: int, user_id: int, text: str):
    mid = _mid()
    now = datetime.now(timezone.utc)
    
    user_data = economy_col().find_one({"chat_id": chat_id, "user_id": user_id})
    last_work = user_data.get("last_work") if user_data else None

    if last_work:
        last_date = datetime.fromisoformat(last_work)
        if (now - last_date).total_seconds() < 300:  # 5 minutes cooldown
            remaining = int(300 - (now - last_date).total_seconds())
            api_request("sendMessage", {
                "chat_id": chat_id,
                "text": f"⏱️ Aap thake hue hain! Dobara kaam karne ke liye `{remaining} seconds` wait karein.",
                "parse_mode": "Markdown",
                "reply_to_message_id": mid,
            })
            return

    earned_cash = random.randint(50, 300)
    earned_gems = random.choice([0, 0, 1, 2])
    
    economy_col().update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {
            "$inc": {"cash": earned_cash, "gems": earned_gems},
            "$set": {"last_work": now.isoformat()}
        },
        upsert=True
    )

    api_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"⚔️ Aapne mission complete kiya aur `{earned_cash}` cash kamaya!" + (f" Aur saath mein `{earned_gems}` gem bhi mila!" if earned_gems > 0 else ""),
        "parse_mode": "Markdown",
        "reply_to_message_id": mid,
    })


# ── Rob (Steal from others) ───────────────────────────────────────────────────

def handle_rob(chat_id: int, user_id: int, text: str):
    mid = _mid()
    message = request.json.get("message", {})
    
    if not message.get("reply_to_message"):
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": "❌ Kisi user ke message par reply karke `/rob` use karein.",
            "parse_mode": "Markdown",
            "reply_to_message_id": mid,
        })
        return

    target_id = message["reply_to_message"]["from"]["id"]
    target_name = message["reply_to_message"]["from"].get("first_name", "User")

    if target_id == user_id:
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": "❌ Aap khud ko nahi loot sakte!",
            "reply_to_message_id": mid,
        })
        return

    target_data = economy_col().find_one({"chat_id": chat_id, "user_id": target_id})
    target_cash = target_data.get("cash", 0) if target_data else 0

    if target_cash < 50:
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": f"❌ **{target_name}** ke paas lootne ke liye 50 cash bhi nahi hain!",
            "parse_mode": "Markdown",
            "reply_to_message_id": mid,
        })
        return

    success = random.choice([True, False, False]) # 33% success chance
    if success:
        stolen_amount = random.randint(20, min(target_cash, 200))
        economy_col().update_one({"chat_id": chat_id, "user_id": user_id}, {"$inc": {"cash": stolen_amount}})
        economy_col().update_one({"chat_id": chat_id, "user_id": target_id}, {"$inc": {"cash": -stolen_amount}})
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": f"🥷 Kamyabi! Aapne **{target_name}** se `{stolen_amount}` cash chura liya.",
            "parse_mode": "Markdown",
            "reply_to_message_id": mid,
        })
    else:
        fine = random.randint(30, 100)
        economy_col().update_one({"chat_id": chat_id, "user_id": user_id}, {"$inc": {"cash": -fine}}, upsert=True)
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": f"🚨 Pakde gaye! Police ne aapko fine laga diya aur aapke `{fine}` cash kat gaye.",
            "parse_mode": "Markdown",
            "reply_to_message_id": mid,
        })


# ── Pay / Transfer Coins ──────────────────────────────────────────────────────

def handle_pay(chat_id: int, user_id: int, text: str):
    mid = _mid()
    message = request.json.get("message", {})
    
    if not message.get("reply_to_message"):
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": "❌ Kisi user ke message par reply karke coins bhejein. Usage: `/pay <amount>`",
            "parse_mode": "Markdown",
            "reply_to_message_id": mid,
        })
        return

    target_id = message["reply_to_message"]["from"]["id"]
    target_name = message["reply_to_message"]["from"].get("first_name", "User")

    if target_id == user_id:
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": "❌ Aap khud ko coins nahi bhej sakte!",
            "reply_to_message_id": mid,
        })
        return

    parts = text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": "❌ Sahi amount likhein. Usage: `/pay <amount>`",
            "parse_mode": "Markdown",
            "reply_to_message_id": mid,
        })
        return

    amount = int(parts[1])
    if amount <= 0:
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": "❌ Amount 0 se zyada honi chahiye.",
            "reply_to_message_id": mid,
        })
        return

    sender_data = economy_col().find_one({"chat_id": chat_id, "user_id": user_id})
    sender_cash = sender_data.get("cash", 0) if sender_data else 0

    if sender_cash < amount:
        api_request("sendMessage", {
            "chat_id": chat_id,
            "text": f"❌ Aapke wallet mein itne cash nahi hain! Aapke paas sirf `{sender_cash}` cash hai.",
            "parse_mode": "Markdown",
            "reply_to_message_id": mid,
        })
        return

    economy_col().update_one({"chat_id": chat_id, "user_id": user_id}, {"$inc": {"cash": -amount}})
    economy_col().update_one({"chat_id": chat_id, "user_id": target_id}, {"$inc": {"cash": amount}}, upsert=True)

    api_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"✅ Safal transaction! Aapne `{amount}` cash **{target_name}** ko bhej diya hai.",
        "parse_mode": "Markdown",
        "reply_to_message_id": mid,
    })


# ── Leaderboards (Group Top 10 & Global Top 20) ───────────────────────────────

def handle_leaderboard(chat_id: int, user_id: int, text: str):
    mid = _mid()
    args = text.split()
    
    # Check if global leaderboard is requested: /leaderboard global
    if len(args) > 1 and args[1].lower() == "global":
        top_users = list(economy_col().aggregate([
            {"$group": {"_id": "$user_id", "total_cash": {"$sum": "$cash"}, "total_gems": {"$sum": "$gems"}}},
            {"$sort": {"total_cash": -1}},
            {"$limit": 20}
        ]))
        
        if not top_users:
            api_request("sendMessage", {"chat_id": chat_id, "text": "📊 Global leaderboard filhal khali hai.", "reply_to_message_id": mid})
            return

        out = "🌍 **Global Wealth Leaderboard (Top 20):**\n\n"
        for i, u in enumerate(top_users, 1):
            out += f"{i}. User ID: `{u['_id']}` — 💵 `{u['total_cash']}` | 💎 `{u['total_gems']}`\n"

        api_request("sendMessage", {"chat_id": chat_id, "text": out, "parse_mode": "Markdown", "reply_to_message_id": mid})
    
    else:
        # Group Leaderboard Top 10
        top_users = list(economy_col().find({"chat_id": chat_id}, {"_id": 0, "user_id": 1, "cash": 1, "gems": 1}).sort("cash", -1).limit(10))
        
        if not top_users:
            api_request("sendMessage", {"chat_id": chat_id, "text": "📊 Is group ka leaderboard filhal khali hai.", "reply_to_message_id": mid})
            return

        out = "🏆 **Group Wealth Leaderboard (Top 10):**\n\n"
        for i, u in enumerate(top_users, 1):
            out += f"{i}. User ID: `{u['user_id']}` — 💵 `{u.get('cash', 0)}` cash\n"

        api_request("sendMessage", {"chat_id": chat_id, "text": out, "parse_mode": "Markdown", "reply_to_message_id": mid})
