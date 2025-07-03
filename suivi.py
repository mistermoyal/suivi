import requests
import json
import pytz
import os
from datetime import datetime, timezone, time as dtime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext

TIMEZONE = "America/Montreal"
TELEGRAM_CHAT_ID = "5473132759"
TELEGRAM_TOKEN = "7550473615:AAHB_bfMixVkvzJFE40wizuGiBEdY7NiWdM"
HOURS_CONFIG_PATH = "hours_config.json"

ACCOUNTS = {
    "Tom": {
        "USERNAME": "93656094",
        "PASSWORD": "Israel20202025!",
        "APPLICATION_NUMBER": "C002954573",
        "NAME": "Tom"
    },
}

PROXIES = {
    "http": "socks5h://infproxy_mistermoyal:JzjAr3m9ZsnRbhhAzuHu_city-toronto@proxy.infiniteproxies.com:2222",
    "https": "socks5h://infproxy_mistermoyal:JzjAr3m9ZsnRbhhAzuHu_city-toronto@proxy.infiniteproxies.com:2222",
}

USE_PROXY = True  # Mettre True pour utiliser proxy, False pour l'enlever

AUTH_URL = "https://cognito-idp.ca-central-1.amazonaws.com/"
TRACKER_URL = "https://api.tracker-suivi.apps.cic.gc.ca/user"
CLIENT_ID = "mtnf1qn9p739g2v8aij2anpju"

COGNITO_HEADERS = {
    "Content-Type": "application/x-amz-json-1.1",
    "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def timestamp_to_date(timestamp):
    mois_fr = {
        "January": "janvier", "February": "février", "March": "mars", "April": "avril",
        "May": "mai", "June": "juin", "July": "juillet", "August": "août",
        "September": "septembre", "October": "octobre", "November": "novembre", "December": "décembre"
    }
    date_en = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).strftime("%d %B %Y")
    for en, fr in mois_fr.items():
        date_en = date_en.replace(en, fr)
    return date_en

def get_token(username, password):
    payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": CLIENT_ID,
        "AuthParameters": {
            "USERNAME": username,
            "PASSWORD": password
        }
    }
    try:
        if USE_PROXY:
            response = requests.post(AUTH_URL, json=payload, headers=COGNITO_HEADERS, proxies=PROXIES)
        else:
            response = requests.post(AUTH_URL, json=payload, headers=COGNITO_HEADERS)
    except Exception as e:
        print(f"[get_token] Exception: {e}")
        return None
    if response.status_code == 200:
        return response.json().get("AuthenticationResult", {}).get("IdToken")
    else:
        print(f"🔴 Erreur Auth: {response.text}")
        return None

def get_application_details(token, application_number):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json"
    }
    payload = {"method": "get-application-details", "applicationNumber": application_number}
    try:
        if USE_PROXY:
            response = requests.post(TRACKER_URL, json=payload, headers=headers, proxies=PROXIES)
        else:
            response = requests.post(TRACKER_URL, json=payload, headers=headers)
    except Exception as e:
        print(f"[get_application_details] Exception: {e}")
        return None
    print(f"📡 Réponse API: {response.text}")
    return response.json() if response.status_code == 200 else None

def extract_last_update_date(data):
    try:
        timestamp = data["lastUpdatedTime"]
        return timestamp_to_date(timestamp)
    except (KeyError, IndexError):
        return "Date non disponible"

def format_application_status(data):
    if "status" not in data:
        return "⚠️ Erreur : Impossible de récupérer les informations."

    status_translation = {
        "closedSuccessful": "Terminé",
        "inProgress": "**En cours**",
        "notStarted": "**Non commencé**",
        "completed": "Terminé"
    }
    activity_translation = {
        "language": "Compétences linguistiques",
        "backgroundVerification": "Vérification des antécédents",
        "residency": "Présence effective",
        "prohibitions": "Interdictions",
        "citizenshipTest": "Examen pour la citoyenneté",
        "citizenshipOath": "Cérémonie de citoyenneté"
    }

    last_update_date = extract_last_update_date(data)
    status_fr = status_translation.get(data["status"], data["status"])
    message = f"📌 **Statut de la demande** : {status_fr}\n\n"
    message += f"📅 **Mise à jour : {last_update_date}**\n\n"
    message += "📍 **Progression des étapes :**\n\n"
    for activity in data.get("activities", []):
        activity_name = activity_translation.get(activity["activity"], activity["activity"])
        status_name = status_translation.get(activity["status"], activity["status"])
        message += f"➡️ {activity_name} : {status_name}\n"
    message += "\n"
    if "history" in data and data["history"]:
        message += "📅 **Historique des mises à jour :**\n\n"
        history_events = sorted(data["history"], key=lambda x: x["time"])
        for event in history_events:
            date = timestamp_to_date(event["time"])
            title = event['title']['fr']
            text = event['text']['fr']
            message += f"\n🔹 **{date} - {title}**"
            message += f"   📝 {text}\n\n"
    return message

def load_hours():
    if not os.path.exists(HOURS_CONFIG_PATH):
        hours = [[8,5], [13,30], [19,55]]
        with open(HOURS_CONFIG_PATH, "w") as f:
            json.dump(hours, f)
        return hours
    with open(HOURS_CONFIG_PATH) as f:
        return json.load(f)

def save_hours(hours):
    with open(HOURS_CONFIG_PATH, "w") as f:
        json.dump(hours, f)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "👋 Bienvenue !\n\n"
        "📌 /Tom pour le suivi\n"
        "⏰ /listhours pour voir les horaires\n"
        "➕ /addhour HH:MM pour ajouter\n"
        "➖ /delhour HH:MM pour retirer\n"
    )

async def send_application_status(update: Update, context: CallbackContext):
    command = update.message.text.lstrip('/').capitalize()
    if command not in ACCOUNTS:
        await update.message.reply_text("❌ Commande invalide. Utilisez /Tom")
        return
    account = ACCOUNTS[command]
    print(f"📩 Le dossier de {account['NAME']} a été demandé manuellement.")
    await update.message.reply_text(f"🔄 Récupération des infos pour {account['NAME']}...")
    token = get_token(account["USERNAME"], account["PASSWORD"])
    if not token:
        await update.message.reply_text("❌ Échec de l'authentification.")
        return
    data = get_application_details(token, account["APPLICATION_NUMBER"])
    if not data:
        await update.message.reply_text("❌ Erreur lors de la récupération des détails.")
        return
    message = format_application_status(data)
    await update.message.reply_text(message, parse_mode="Markdown")

async def scheduled_check_tom(context: CallbackContext):
    print("🔔 Tâche planifiée exécutée (scheduled_check_tom) !")
    account = ACCOUNTS["Tom"]
    now = datetime.now(pytz.timezone(TIMEZONE))
    print(f"⏳ Vérification planifiée du dossier de Tom à {now.strftime('%H:%M (%d/%m/%Y)')} ({TIMEZONE})...")
    token = get_token(account["USERNAME"], account["PASSWORD"])
    if token:
        data = get_application_details(token, account["APPLICATION_NUMBER"])
        if data:
            heure_str = datetime.now(pytz.timezone(TIMEZONE)).strftime("%H:%M")
            message = f"📢 **Mise à jour planifiée pour Tom ({heure_str}) !**\n\n"
            message += format_application_status(data)
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
            print("✅ Notification envoyée.")
        else:
            print("❌ Impossible de récupérer les détails.")
    else:
        print("❌ Impossible d'obtenir le token.")

async def listhours(update: Update, context: CallbackContext):
    hours = load_hours()
    msg = "⏰ Heures de notifications automatiques:\n"
    for h, m in hours:
        msg += f"• {h:02}:{m:02}\n"
    await update.message.reply_text(msg)

async def addhour(update: Update, context: CallbackContext):
    if not context.args or not context.args[0].count(":") == 1:
        await update.message.reply_text("Format: /addhour HH:MM")
        return
    try:
        h, m = map(int, context.args[0].split(":"))
        assert 0 <= h < 24 and 0 <= m < 60
    except:
        await update.message.reply_text("Format: /addhour HH:MM (ex: /addhour 15:30)")
        return

    hours = load_hours()
    if [h, m] in hours:
        await update.message.reply_text(f"Déjà programmé à {h:02}:{m:02}")
        return
    hours.append([h, m])
    hours.sort()
    save_hours(hours)
    await update.message.reply_text(f"Ajouté : {h:02}:{m:02}. Je recharge les horaires...")
    reload_jobs(context.application, hours)

async def delhour(update: Update, context: CallbackContext):
    if not context.args or not context.args[0].count(":") == 1:
        await update.message.reply_text("Format: /delhour HH:MM")
        return
    try:
        h, m = map(int, context.args[0].split(":"))
    except:
        await update.message.reply_text("Format: /delhour HH:MM")
        return
    hours = load_hours()
    if [h, m] not in hours:
        await update.message.reply_text(f"Pas de notif à {h:02}:{m:02}")
        return
    hours.remove([h, m])
    save_hours(hours)
    await update.message.reply_text(f"Supprimé : {h:02}:{m:02}. Je recharge les horaires...")
    reload_jobs(context.application, hours)

def reload_jobs(app, hours):
    # Supprime tous les jobs planifiés pour Tom
    for job in list(app.job_queue.jobs()):
        if job.name and job.name.startswith("auto_check_tom_"):
            job.schedule_removal()

    # Rajoute avec la nouvelle liste
    for h, m in hours:
        app.job_queue.run_daily(
            scheduled_check_tom,
            time=dtime(h, m, tzinfo=pytz.timezone(TIMEZONE)),
            name=f"auto_check_tom_{h:02}{m:02}"
        )
    print("Horaires rechargés :", hours)

def main():
    print("\n=== Lancement du bot ===")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("Tom", send_application_status))
    app.add_handler(CommandHandler("listhours", listhours))
    app.add_handler(CommandHandler("addhour", addhour))
    app.add_handler(CommandHandler("delhour", delhour))

    print("Heure Montréal (now):", datetime.now(pytz.timezone(TIMEZONE)).strftime("%H:%M:%S"))

    hours = load_hours()
    reload_jobs(app, hours)

    print(f"✅ Bot Telegram démarré avec checks automatiques à {[f'{h:02}:{m:02}' for h, m in hours]} ({TIMEZONE}) chaque jour.")
    app.run_polling()

if __name__ == "__main__":
    main()
