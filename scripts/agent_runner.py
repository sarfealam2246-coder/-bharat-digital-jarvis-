import email
import imaplib
import json
import os
import random
import smtplib
import time
from datetime import datetime, timezone
from email.message import EmailMessage
import requests

from ai_departments import ceo_audit_outreach, estimate_market_rate, load_memory, run_department, save_memory
from demo_builder import build_demo_page, build_upi_payment_page, rebuild_portfolio_index, slugify
from jarvis_voice import generate_jarvis_brief_mp3

# Agent 1 Zone: North + West + Central India
AGENT_1_CITIES = [
    ("Delhi", 28.6139, 77.2090),
    ("Noida", 28.5355, 77.3910),
    ("Gurugram", 28.4595, 77.0266),
    ("Faridabad", 28.4089, 77.3178),
    ("Ghaziabad", 28.6692, 77.4538),
    ("Jaipur", 26.9124, 75.7873),
    ("Jodhpur", 26.2389, 73.0243),
    ("Udaipur", 24.5854, 73.7125),
    ("Kota", 25.2138, 75.8648),
    ("Lucknow", 26.8467, 80.9462),
    ("Varanasi", 25.3176, 82.9739),
    ("Kanpur", 26.4499, 80.3319),
    ("Prayagraj", 25.4358, 81.8463),
    ("Agra", 27.1767, 78.0081),
    ("Gorakhpur", 26.7606, 83.3732),
    ("Meerut", 28.9845, 77.7064),
    ("Patna", 25.5941, 85.1376),
    ("Gaya", 24.7914, 85.0002),
    ("Muzaffarpur", 26.1197, 85.3910),
    ("Ranchi", 23.3441, 85.3096),
    ("Jamshedpur", 22.8046, 86.2029),
    ("Bhopal", 23.2599, 77.4126),
    ("Indore", 22.7196, 75.8577),
    ("Gwalior", 26.2183, 78.1828),
    ("Jabalpur", 23.1815, 79.9864),
    ("Surat", 21.1702, 72.8311),
    ("Ahmedabad", 23.0225, 72.5714),
    ("Vadodara", 22.3072, 73.1812),
    ("Rajkot", 22.3039, 70.8022),
    ("Mumbai", 19.0760, 72.8777),
    ("Pune", 18.5204, 73.8567),
    ("Thane", 19.2183, 72.9781),
    ("Nashik", 19.9975, 73.7898),
    ("Nagpur", 21.1458, 79.0882),
    ("Chandigarh", 30.7333, 76.7794),
    ("Ludhiana", 30.9010, 75.8573),
    ("Amritsar", 31.6340, 74.8723),
    ("Dehradun", 30.3165, 78.0322),
    ("Raipur", 21.2514, 81.6296),
]

# Agent 2 Zone: South + East + North-East India + Online Gigs
AGENT_2_CITIES = [
    ("Bengaluru", 12.9716, 77.5946),
    ("Mysuru", 12.2958, 76.6394),
    ("Mangaluru", 12.9141, 74.8560),
    ("Hubballi", 15.3647, 75.1240),
    ("Hyderabad", 17.3850, 78.4867),
    ("Warangal", 17.9689, 79.5941),
    ("Visakhapatnam", 17.6868, 83.2185),
    ("Vijayawada", 16.5062, 80.6480),
    ("Tirupati", 13.6288, 79.4192),
    ("Chennai", 13.0827, 80.2707),
    ("Coimbatore", 11.0168, 76.9558),
    ("Madurai", 9.9252, 78.1198),
    ("Kochi", 9.9312, 76.2673),
    ("Thiruvananthapuram", 8.5241, 76.9366),
    ("Kolkata", 22.5726, 88.3639),
    ("Siliguri", 26.7271, 88.3953),
    ("Durgapur", 23.5204, 87.3119),
    ("Bhubaneswar", 20.2961, 85.8245),
    ("Cuttack", 20.4625, 85.8830),
    ("Guwahati", 26.1445, 91.7362),
]


def fetch_osm_leads(city: str, lat: float, lon: float) -> list[dict]:
    """Scan 55km radius across nodes, ways & relations (nwr) for businesses without a website."""
    query = f"""
    [out:json][timeout:30];
    (
      nwr["amenity"~"clinic|doctors|dentist|hospital|restaurant|cafe|school|college|coaching"](around:55000,{lat},{lon})["name"][!"website"];
      nwr["shop"~"beauty|hairdresser|electronics|mobile_phone|jewelry|car|motorcycle|furniture|supermarket"](around:55000,{lat},{lon})["name"][!"website"];
      nwr["office"~"estate_agent|lawyer|accountant|insurance"](around:55000,{lat},{lon})["name"][!"website"];
    );
    out center 50;
    """
    leads = []
    try:
        r = requests.post("https://overpass-api.de/api/interpreter", data={"data": query}, timeout=35)
        if r.ok:
            for el in r.json().get("elements", []):
                tags = el.get("tags", {})
                name = (tags.get("name") or "").strip()
                phone = (tags.get("phone") or tags.get("contact:phone") or tags.get("mobile") or "").strip()
                mail = (tags.get("email") or tags.get("contact:email") or "").strip()
                if not name or (not phone and not mail):
                    continue
                cat = tags.get("amenity") or tags.get("shop") or tags.get("office") or "business"
                leads.append({
                    "source": "All-India 55km Radar",
                    "name": name,
                    "category": cat,
                    "city": city,
                    "phone": phone,
                    "email": mail,
                    "slug": slugify(f"{name}-{city}"),
                })
    except Exception as exc:
        print(f"OSM note ({city}): {exc}")
    return leads


def fetch_india_online_gigs() -> list[dict]:
    leads = []
    for sub in ["FreelanceIndia", "FreelanceIndiaa", "forhire", "smallbusiness"]:
        try:
            r = requests.get(f"https://www.reddit.com/r/{sub}/new.json?limit=18", headers={"User-Agent": "BharatDigitalJarvis/2.0"}, timeout=15)
            if r.ok:
                for ch in r.json().get("data", {}).get("children", []):
                    d = ch.get("data", {})
                    title = (d.get("title") or "").strip()
                    if any(w in title.lower() for w in ["[hiring]", "need", "looking", "website", "landing", "app", "excel", "poster", "menu", "clinic"]):
                        leads.append({
                            "source": f"r/{sub}",
                            "name": title[:65],
                            "category": "online_gig",
                            "city": "India Online",
                            "phone": "",
                            "email": "",
                            "customRequest": (d.get("selftext") or title)[:220],
                            "postUrl": f"https://www.reddit.com{d.get('permalink', '')}",
                            "slug": slugify(f"gig-{d.get('id', 'x')}"),
                        })
        except Exception:
            continue
    return leads


def send_gmail(to_addr: str, subject: str, body: str) -> bool:
    gmail_addr = os.getenv("GMAIL_ADDRESS", "").strip()
    app_pwd = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not gmail_addr or not app_pwd or not to_addr:
        return False
    msg = EmailMessage()
    msg["From"] = f"Bharat Digital <{gmail_addr}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as smtp:
        smtp.login(gmail_addr, app_pwd)
        smtp.send_message(msg)
    return True


def check_gmail_inbox(deals: list) -> int:
    gmail_addr = os.getenv("GMAIL_ADDRESS", "").strip()
    app_pwd = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not gmail_addr or not app_pwd:
        return 0
    new_count = 0
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(gmail_addr, app_pwd)
        mail.select("INBOX")
        status, data = mail.search(None, "UNSEEN")
        if status == "OK":
            for num in data[0].split()[:10]:
                _, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                sender = email.utils.parseaddr(msg.get("From", ""))[1]
                subj = msg.get("Subject", "(No Subject)")
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                analysis = run_department(
                    "writer",
                    f"Client Email From: {sender}\nSubject: {subj}\nBody: {body[:1200]}\nReturn JSON: {{\"hindiExplanation\": \"2-line simple Hindi summary\", \"suggestedReply\": \"polite reply\", \"amountInr\": 2999}}",
                    "You are an Indian B2B deal assistant. Return ONLY JSON.",
                    expect_json=True,
                ) or {"hindiExplanation": f"{sender} ने नया जवाब भेजा है।", "suggestedReply": "Namaste! Hum aapka final page aur QR aaj hi chalu kar denge.", "amountInr": 2999}

                deals.append({
                    "id": f"deal_{int(time.time())}_{new_count}",
                    "sender": sender,
                    "subject": subj,
                    "clientText": body[:500],
                    "hindiExplanation": analysis["hindiExplanation"],
                    "suggestedReply": analysis["suggestedReply"],
                    "amountInr": int(analysis.get("amountInr") or 2999),
                    "status": "PENDING_APPROVAL",
                    "receivedAt": datetime.now(timezone.utc).isoformat(),
                })
                new_count += 1
        mail.logout()
    except Exception as exc:
        print(f"Gmail IMAP skipped: {exc}")
    return new_count


def handle_apk_action(history: list, deals: list, base_pages_url: str):
    action = os.getenv("APK_ACTION", "").strip()
    target_id = os.getenv("APK_TARGET_ID", "").strip()
    amount = int(os.getenv("APK_AMOUNT", "2999") or "2999")
    if not action or not target_id:
        return
    upi_id = os.getenv("MY_UPI_ID", "").strip() or "yourupi@okaxis"
    winning = load_memory("winning_patterns.json", {"sentCount": 0, "paidDeals": []})

    lead = next((h for h in history if h.get("slug") == target_id), None)
    if lead:
        if action == "mark_sent":
            lead["status"] = "SENT"
            winning["sentCount"] = winning.get("sentCount", 0) + 1
        elif action == "send_email" and lead.get("email"):
            if send_gmail(lead["email"], f"Prepared Website Demo for {lead['name']}", lead.get("pitchMessage", "")):
                lead["status"] = "SENT"
                winning["sentCount"] = winning.get("sentCount", 0) + 1
        elif action == "unlock_and_upi":
            build_demo_page(lead, base_pages_url, is_final=True)
            pay_url = build_upi_payment_page(lead, amount, upi_id, base_pages_url)
            lead["status"] = "PAID"
            lead["payUrl"] = pay_url
            lead["amountInr"] = amount
            winning.setdefault("paidDeals", []).append({"name": lead["name"], "amount": amount, "ts": datetime.now(timezone.utc).isoformat()})
            if lead.get("email"):
                send_gmail(lead["email"], f"Website Unlocked + UPI Payment (₹{amount})", f"Namaste! Aapki website unlock ho gayi hai: {lead['demoUrl']}\nUPI Payment Link: {pay_url}")

    deal = next((d for d in deals if d.get("id") == target_id), None)
    if deal:
        if action == "approve_reply":
            if send_gmail(deal["sender"], f"Re: {deal['subject']}", deal["suggestedReply"]):
                deal["status"] = "REPLIED"
        elif action == "approve_deal_upi":
            pay_url = build_upi_payment_page({"name": deal["sender"], "slug": slugify(deal["sender"])}, amount, upi_id, base_pages_url)
            send_gmail(deal["sender"], f"Order Confirmed — UPI Payment ₹{amount}", f"Namaste! Aapki deal confirm ho gayi hai.\nUPI Payment Link: {pay_url}\nUPI ID: {upi_id}")
            deal["status"] = "PAID"
            deal["payUrl"] = pay_url
            deal["amountInr"] = amount
            winning.setdefault("paidDeals", []).append({"name": deal["sender"], "amount": amount, "ts": datetime.now(timezone.utc).isoformat()})
        elif action == "cancel_deal":
            deal["status"] = "CANCELLED"

    save_memory("winning_patterns.json", winning)


def trigger_next_relay(current_shift: str):
    pat = os.getenv("GH_AUTO_PAT", "").strip()
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    enable_relay = os.getenv("ENABLE_RELAY", "true").lower() == "true"
    if not pat or not repo or not enable_relay:
        return
    next_wf = "agent_2_relay.yml" if current_shift == "agent1" else "agent_1_relay.yml"
    time.sleep(120)
    try:
        requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/{next_wf}/dispatches",
            headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"},
            json={"ref": "main"},
            timeout=15,
        )
    except Exception as exc:
        print(f"Relay dispatch note: {exc}")


def main():
    shift = os.getenv("AGENT_SHIFT", "agent1").strip() or "agent1"
    repo = os.getenv("GITHUB_REPOSITORY", "sarfealam2246-coder/-bharat-digital-jarvis-")
    owner, name = (repo.split("/", 1) + ["-bharat-digital-jarvis-"])[:2]
    base_pages_url = os.getenv("PAGES_BASE_URL", f"https://{owner}.github.io/{name}").strip()

    history = load_memory("leads_history.json", [])
    deals = load_memory("deal_chats.json", [])
    reports = load_memory("run_reports.json", [])

    handle_apk_action(history, deals, base_pages_url)

    zone_cities = list(AGENT_1_CITIES) if shift == "agent1" else list(AGENT_2_CITIES)
    random.shuffle(zone_cities)
    seen_slugs = {h.get("slug") for h in history}
    seen_phones = {h.get("phone") for h in history if h.get("phone")}
    fresh = []
    scanned_cities = []

    for city, lat, lon in zone_cities[:12]:
        scanned_cities.append(city)
        for item in fetch_osm_leads(city, lat, lon):
            ph = item.get("phone", "")
            if item["slug"] not in seen_slugs and (not ph or ph not in seen_phones):
                seen_slugs.add(item["slug"])
                if ph:
                    seen_phones.add(ph)
                fresh.append(item)
        if len(fresh) >= 4:
            break

    if len(fresh) < 4:
        for gig in fetch_india_online_gigs():
            if gig["slug"] not in seen_slugs:
                seen_slugs.add(gig["slug"])
                fresh.append(gig)
            if len(fresh) >= 4:
                break

    fresh = fresh[:4]
    built_count = 0
    for lead in fresh:
        pricing = estimate_market_rate(lead.get("category", ""), lead.get("name", ""), lead.get("customRequest", ""))
        lead["offerPriceInr"] = pricing["offerPriceInr"]
        lead["marketRateInr"] = pricing["marketRateInr"]

        demo_info = build_demo_page(lead, base_pages_url, is_final=False)
        writer_res = run_department(
            "writer",
            f"Business: {lead['name']} ({lead['city']}, {lead['category']})\nWork Scope: {pricing['workScope']}\nMarket Rate: {pricing['marketRateInr']}\nOur Offer Price: ₹{pricing['offerPriceInr']}\nLocked Demo URL: {demo_info['demoUrl']}\nReturn JSON: {{\"hindiSummary\": \"2-line Hindi summary mentioning what problem was solved and price\", \"clientMessage\": \"polite Hinglish pitch saying we already built their demo solution at {demo_info['demoUrl']}, market rate is {pricing['marketRateInr']}, our direct offer is ₹{pricing['offerPriceInr']} (open to discussion)\"}}",
            "You are an Indian B2B sales writer. Return ONLY JSON.",
            expect_json=True,
        ) or {}
        hindi_summary = writer_res.get("hindiSummary") or f"{lead['city']} का {lead['name']} — बिना वेबसाइट का बिज़नेस, ₹{pricing['offerPriceInr']} ऑफर का डेमो तैयार है।"
        pitch = writer_res.get("clientMessage") or f"नमस्ते {lead['name']} जी, मैंने देखा कि आपके {lead['category']} के लिए ऑनलाइन बुकिंग/वेबसाइट की कमी थी। मैंने आपके लिए पहले ही इसका डेमो हल तैयार कर दिया है: {demo_info['demoUrl']}। मार्केट में इसका खर्च {pricing['marketRateInr']} आता है, पर हम इसे ₹{pricing['offerPriceInr']} में आपके नंबर व QR के साथ लाइव कर देंगे।"

        audit = ceo_audit_outreach(lead, pitch, demo_info["demoUrl"])
        if audit.get("approved", True):
            history.append({
                **lead,
                "demoUrl": demo_info["demoUrl"],
                "hindiSummary": hindi_summary,
                "pitchMessage": audit.get("polishedMessage") or pitch,
                "status": "NEW",
                "foundAt": datetime.now(timezone.utc).isoformat(),
            })
            built_count += 1

    new_emails = check_gmail_inbox(deals)
    rebuild_portfolio_index()

    pending_outbox = sum(1 for h in history if h.get("status") == "NEW")
    pending_deals = sum(1 for d in deals if d.get("status") == "PENDING_APPROVAL")
    total_earned = sum(int(h.get("amountInr", 0)) for h in history if h.get("status") == "PAID") + sum(int(d.get("amountInr", 0)) for d in deals if d.get("status") == "PAID")

    cities_label = ", ".join(scanned_cities) if scanned_cities else "All India"
    report_msg = f"{shift.upper()} ने {cities_label} में खोज की: {built_count} नए लॉक डेमो बने, {new_emails} नए क्लाइंट ईमेल मिले। अभी भेजने के लिए {pending_outbox} कार्ड तैयार हैं।"
    reports.append({"ts": datetime.now(timezone.utc).isoformat(), "shift": shift, "city": cities_label, "built": built_count, "emails": new_emails, "summary": report_msg})

    jarvis_speech = (
        f"नमस्ते सर, मैं जार्विस बोल रहा हूँ। अभी {shift.upper()} ने {cities_label} में खोज पूरी की। "
        f"{built_count} नए बिज़नेस डेमो मार्केट रेट के हिसाब से तैयार हुए हैं। "
        f"आपके संदेश बॉक्स में {pending_outbox} क्लाइंट भेजने के लिए तैयार हैं, और {pending_deals} डील आपके हाँ या ना के इंतज़ार में हैं। "
        f"अब तक कुल {total_earned} रुपये की कमाई दर्ज हुई है।"
    )
    generate_jarvis_brief_mp3(jarvis_speech)

    live_status = {
        "lastRunAt": datetime.now(timezone.utc).isoformat(),
        "activeShift": shift,
        "lastCity": cities_label,
        "newBuilt": built_count,
        "newEmails": new_emails,
        "pendingOutbox": pending_outbox,
        "pendingDeals": pending_deals,
        "totalEarnedInr": total_earned,
        "jarvisScript": jarvis_speech,
        "statusText": report_msg,
    }

    save_memory("leads_history.json", history[-300:])
    save_memory("deal_chats.json", deals[-100:])
    save_memory("run_reports.json", reports[-60:])
    save_memory("live_status.json", live_status)
    print(f"RUN_REPORT_OK: {report_msg}")

    if not os.getenv("APK_ACTION"):
        trigger_next_relay(shift)


if __name__ == "__main__":
    main()
