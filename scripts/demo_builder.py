import html
import os
import re
import urllib.parse
from pathlib import Path
from PIL import Image, ImageDraw

from ai_departments import (
    estimate_market_rate,
    generate_poster_image,
    load_memory,
    load_skill_for_category,
    run_department,
    verify_html_integrity,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
DEMOS_DIR = DOCS_DIR / "demos"
PAY_DIR = DOCS_DIR / "pay"
DEMOS_DIR.mkdir(parents=True, exist_ok=True)
PAY_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "demo").lower()).strip("-")
    return s[:48] or "business-demo"


def make_qr_png(data: str, out_path: Path):
    try:
        import qrcode
        qr = qrcode.QRCode(version=2, box_size=10, border=3)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#111827", back_color="white").convert("RGB")
        img.save(out_path)
    except Exception:
        img = Image.new("RGB", (240, 240), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([(12, 12), (228, 228)], outline="#111827", width=6)
        draw.text((64, 110), "SCAN QR", fill="#111827")
        img.save(out_path)


def build_demo_copy(lead: dict) -> dict:
    learnings = load_memory("demo_learnings.json", {"tips": ["Keep WhatsApp CTA at top", "Clear ₹ pricing"]})
    skill_rules = load_skill_for_category(lead.get("category", ""))
    prompt = f"""
Follow this Skill Playbook:
{skill_rules}

Create clean Hindi+English website copy specifically tailored to:
Name: {lead.get('name')}
Category: {lead.get('category')}
City: {lead.get('city')}
Custom Client Request (if any): {lead.get('customRequest', 'Standard high-converting layout')}
Learnings: {learnings.get('tips', [])[-4:]}

Return ONLY JSON:
{{
  "tagline": "Short trustworthy Hindi+English tagline for this exact business",
  "services": [
    {{"title": "Specific Service 1", "price": "₹...", "desc": "Short 1-line detail"}},
    {{"title": "Specific Service 2", "price": "₹...", "desc": "Short 1-line detail"}},
    {{"title": "Specific Service 3", "price": "₹...", "desc": "Short 1-line detail"}}
  ],
  "hours": "10:00 AM – 8:30 PM",
  "ctaLabel": "WhatsApp पर बुक / बात करें"
}}
"""
    res = run_department("builder", prompt, "You are an Indian SMB custom web builder. Return ONLY JSON.", expect_json=True)
    if isinstance(res, dict) and res.get("services"):
        return res
    text = f"{lead.get('category', '')} {lead.get('name', '')}".lower()
    if any(k in text for k in ["clinic", "doctor", "dentist", "hospital", "medical"]):
        return {
            "tagline": f"{lead.get('city', 'India')} का भरोसेमंद स्वास्थ्य एवं अपॉइंटमेंट सेंटर",
            "services": [
                {"title": "OPD परामर्श", "price": "₹300", "desc": "तुरंत WhatsApp से नंबर लगाएँ"},
                {"title": "जाँच एवं रिपोर्ट सलाह", "price": "₹500", "desc": "समय की बचत, बिना लंबी लाइन"},
                {"title": "फॉलो-अप विज़िट", "price": "₹200", "desc": "सीधा डॉक्टर से अपॉइंटमेंट"},
            ],
            "hours": "10:00 AM – 8:00 PM",
            "ctaLabel": "WhatsApp पर अपॉइंटमेंट बुक करें",
        }
    if any(k in text for k in ["school", "college", "coaching", "classes", "academy", "tuition"]):
        return {
            "tagline": f"{lead.get('city', 'India')} में नए बैच और ऑनलाइन एडमिशन रजिस्ट्रेशन",
            "services": [
                {"title": "नया बैच एडमिशन फॉर्म", "price": "ऑनलाइन", "desc": "छात्र सीधे नाम और नंबर दर्ज करें"},
                {"title": "कोर्स व फीस चार्ट", "price": "पूरा विवरण", "desc": "समय, विषय और डेमो क्लास"},
                {"title": "पैरेंट्स हेल्पडेस्क", "price": "1-टैप", "desc": "सीधा कॉल और लोकेशन लिंक"},
            ],
            "hours": "8:00 AM – 7:00 PM",
            "ctaLabel": "एडमिशन के लिए WhatsApp करें",
        }
    if any(k in text for k in ["hotel", "resort", "restaurant", "cafe", "sweets", "bakery", "dhaba"]):
        return {
            "tagline": f"{lead.get('city', 'India')} में ताज़ा स्वाद, टेबल बुकिंग व ऑनलाइन ऑर्डर",
            "services": [
                {"title": "टेबल / रूम बुकिंग", "price": "तुरंत", "desc": "बिना वेटिंग सीधे WhatsApp बुकिंग"},
                {"title": "स्पेशल मेनू व कैटरिंग", "price": "पूरा चार्ट", "desc": "ताज़ा रेट लिस्ट और पार्टी ऑर्डर"},
                {"title": "होम डिलीवरी / पार्सल", "price": "1-क्लिक", "desc": "सीधा कॉल और लोकेशन लिंक"},
            ],
            "hours": "9:00 AM – 10:30 PM",
            "ctaLabel": "ऑर्डर / बुकिंग के लिए WhatsApp करें",
        }
    if any(k in text for k in ["jewel", "sarees", "clothes", "furniture", "electronics", "estate", "property", "showroom"]):
        return {
            "tagline": f"{lead.get('city', 'India')} के चुनिंदा कलेक्शन व डायरेक्ट WhatsApp कैटलॉग",
            "services": [
                {"title": "लेटेस्ट डिज़ाइन कैटलॉग", "price": "फ्री देखें", "desc": "नए कलेक्शन और कीमत सीधे फोन पर"},
                {"title": "विज़िट अपॉइंटमेंट", "price": "1-टैप", "desc": "शोरूम लोकेशन और समय बुक करें"},
                {"title": "स्पेशल ऑफर व डील", "price": "उपलब्ध", "desc": "त्योहार व शादी के विशेष पैकेज"},
            ],
            "hours": "10:30 AM – 8:30 PM",
            "ctaLabel": "कैटलॉग व रेट के लिए WhatsApp करें",
        }
    return {
        "tagline": f"{lead.get('city', 'India')} में तेज़, भरोसेमंद और किफायती सेवा",
        "services": [
            {"title": "प्रमुख सेवा / पैकेज", "price": "बेस्ट रेट", "desc": "तुरंत बुकिंग व ग्राहक सहायता"},
            {"title": "होम विज़िट / ऑनलाइन सलाह", "price": "उपलब्ध", "desc": "सीधा WhatsApp पर जानकारी लें"},
            {"title": "मंथली / बल्क ऑर्डर", "price": "स्पेशल छूट", "desc": "नियमित ग्राहकों के लिए विशेष सुविधा"},
        ],
        "hours": "10:00 AM – 8:30 PM",
        "ctaLabel": "अभी WhatsApp पर बात करें",
    }


def validate_html_gate(html_str: str, is_final: bool) -> bool:
    ok_int, _ = verify_html_integrity(html_str)
    if not ok_int:
        return False
    if not is_final and "SAMPLE DEMO • LOCKED" not in html_str:
        return False
    return True


def build_demo_page(lead: dict, base_pages_url: str, is_final: bool = False) -> dict:
    slug = lead.get("slug") or slugify(f"{lead.get('name')}-{lead.get('city', 'in')}")
    out_dir = DEMOS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    pricing = estimate_market_rate(lead.get("category", ""), lead.get("name", ""), lead.get("customRequest", ""))
    offer_inr = lead.get("offerPriceInr") or pricing["offerPriceInr"]
    market_rate = lead.get("marketRateInr") or pricing["marketRateInr"]

    copy = build_demo_copy(lead)
    banner_path = out_dir / "banner.png"
    if not banner_path.exists():
        ok_img = generate_poster_image(
            f"Clean bright modern Indian {lead.get('category', 'shop')} storefront interior, welcoming warm lighting, no text",
            banner_path,
        )
        if not ok_img:
            img = Image.new("RGB", (768, 400), (24, 119, 242))
            draw = ImageDraw.Draw(img)
            for y in range(400):
                draw.line([(0, y), (768, y)], fill=(24, 119, min(255, 180 + y // 6)))
            img.save(banner_path)

    demo_url = f"{base_pages_url.rstrip('/')}/demos/{slug}/"
    make_qr_png(demo_url, out_dir / "qr.png")

    phone_digits = re.sub(r"\D", "", str(lead.get("phone", "")))
    if len(phone_digits) == 10:
        phone_digits = "91" + phone_digits
    real_wa_url = f"https://wa.me/{phone_digits}?text={urllib.parse.quote('नमस्ते, मुझे अपॉइंटमेंट/सर्विस के बारे में बात करनी है।')}" if phone_digits else "#contact-box"
    maps_q = urllib.parse.quote(f"{lead.get('name')} {lead.get('city', 'India')}")
    real_maps_url = f"https://www.google.com/maps/search/?api=1&query={maps_q}"

    wa_link = real_wa_url if is_final else "#contact-box"
    wa_onclick = "" if is_final else ' onclick="return handleLockedBtn(this, event);"'
    maps_link = real_maps_url if is_final else "#contact-box"
    maps_onclick = "" if is_final else ' onclick="return handleLockedBtn(this, event);"'
    bot_email = os.getenv("GMAIL_ADDRESS", "sarfe293@gmail.com").strip() or "sarfe293@gmail.com"
    owner_pin = os.getenv("OWNER_PIN", "7860").strip() or "7860"

    services_html = "\n".join(
        f'<div class="card"><div class="row"><strong>{html.escape(s.get("title", ""))}</strong><span class="price">{html.escape(s.get("price", ""))}</span></div><p class="muted">{html.escape(s.get("desc", ""))}</p></div>'
        for s in copy.get("services", [])
    )
    demo_ribbon = "" if is_final else '<div class="demo-badge" id="demoRibbon">🔒 DEMO PREVIEW ONLY — क्लाइंट बुकिंग व नंबर पेमेंट के बाद अनलॉक होंगे</div>'
    watermark_div = "" if is_final else '<div class="wm" id="wmLock">SAMPLE DEMO • LOCKED</div>'
    qr_section = (
        '<div class="qr-box"><strong>काउंटर QR कोड (स्कैन करके सेव करें)</strong><br/><img src="qr.png" alt="QR Code" /><br/><span class="muted">प्रिंट कराके दुकान/क्लिनिक काउंटर पर लगाएँ</span></div>'
        if is_final
        else '<div class="qr-box" id="qrLocked"><strong>🔒 काउंटर QR कोड (लॉक)</strong><br/><p class="muted">असली प्रिंटेबल QR कोड फाइनल सेटअप के बाद अनलॉक होगा।</p></div>'
    )
    owner_btn_html = "" if is_final else f"""
      <div style="text-align:center;margin-top:14px;">
        <button onclick="unlockOwnerPreview()" style="background:#f3f4f6;border:1px solid #d1d5db;color:#374151;padding:6px 12px;border-radius:6px;font-size:12px;cursor:pointer;">🔑 Owner View (सिर्फ़ मालिक के लिए)</button>
      </div>
      <script>
        var __ownerUnlocked = false;
        function handleLockedBtn(el, ev) {{
          if (__ownerUnlocked) return true;
          ev.preventDefault();
          alert('यह DEMO प्रीव्यू है! अपने असली WhatsApp नंबर से बुकिंग चालू करने के लिए नीचे ऑर्डर बटन से अनलॉक कराएँ।');
          return false;
        }}
        function unlockOwnerPreview() {{
          var pin = prompt('Owner Preview पासवर्ड डालें:');
          if (pin === '{owner_pin}') {{
            __ownerUnlocked = true;
            var wm = document.getElementById('wmLock'); if (wm) wm.style.display = 'none';
            var rb = document.getElementById('demoRibbon'); if (rb) {{ rb.style.background = '#15803d'; rb.style.color = '#fff'; rb.innerText = '🔓 OWNER PREVIEW MODE — सभी बटन टेस्ट के लिए खुले हैं'; }}
            var wa = document.getElementById('waBtn'); if (wa) wa.href = '{real_wa_url}';
            var mp = document.getElementById('mapBtn'); if (mp) mp.href = '{real_maps_url}';
            var qr = document.getElementById('qrLocked'); if (qr) qr.innerHTML = '<strong>काउंटर QR कोड (Owner Preview)</strong><br/><img src="qr.png" alt="QR Code" /><br/><span class="muted">फाइनल होने पर क्लाइंट को ऐसा दिखेगा</span>';
          }} else if (pin !== null) {{
            alert('गलत पासवर्ड!');
          }}
        }}
      </script>
    """

    page_html = f"""<!doctype html>
<html lang="hi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{html.escape(lead.get('name', 'Business'))} — {html.escape(lead.get('city', 'India'))}</title>
  <style>
    body{{margin:0;font-family:system-ui,-apple-system,sans-serif;background:#f0f2f5;color:#111827;}}
    .wrap{{max-width:480px;margin:0 auto;background:#fff;min-height:100vh;position:relative;}}
    .demo-badge{{background:#111827;color:#facc15;text-align:center;font-size:12px;font-weight:700;padding:8px;}}
    .wm{{position:fixed;top:42%;left:50%;transform:translate(-50%,-50%) rotate(-24deg);font-size:28px;font-weight:900;color:rgba(220,38,38,0.22);pointer-events:none;white-space:nowrap;z-index:99;}}
    .hero img{{width:100%;height:210px;object-fit:cover;display:block;}}
    .pad{{padding:18px;}}
    h1{{margin:0 0 6px;font-size:24px;}}
    .muted{{color:#4b5563;font-size:14px;margin:4px 0 12px;}}
    .btn{{display:block;text-align:center;padding:13px 16px;border-radius:10px;font-weight:700;text-decoration:none;margin:10px 0;}}
    .btn-wa{{background:#25D366;color:#fff;}}
    .btn-map{{background:#1877F2;color:#fff;}}
    .card{{border:1px solid #e5e7eb;border-radius:10px;padding:12px;margin:10px 0;background:#f9fafb;}}
    .row{{display:flex;justify-content:space-between;align-items:center;}}
    .price{{color:#1877F2;font-weight:800;}}
    .qr-box{{text-align:center;border:1px dashed #9ca3af;border-radius:12px;padding:14px;margin-top:16px;}}
    .qr-box img{{width:140px;height:140px;}}
    .btn-mail{{background:#111827;color:#fff;border:none;width:100%;padding:12px;border-radius:8px;font-weight:700;display:block;text-align:center;text-decoration:none;box-sizing:border-box;}}
  </style>
</head>
<body>
  <div class="wrap">
    {watermark_div}
    {demo_ribbon}
    <div class="hero"><img src="banner.png" alt="{html.escape(lead.get('name', 'Business'))}" /></div>
    <div class="pad">
      <h1>{html.escape(lead.get('name', 'Business'))}</h1>
      <p class="muted">📍 {html.escape(lead.get('city', 'India'))} • ⏰ {html.escape(copy.get('hours', '10 AM - 8 PM'))}</p>
      <p>{html.escape(copy.get('tagline', ''))}</p>
      <a class="btn btn-wa" id="waBtn" href="{wa_link}"{wa_onclick}>💬 {html.escape(copy.get('ctaLabel', 'WhatsApp पर बात करें'))}</a>
      <a class="btn btn-map" id="mapBtn" href="{maps_link}" target="_blank"{maps_onclick}>📍 Google Maps लोकेशन देखें</a>
      <h3>सेवाएँ और रेट</h3>
      {services_html}
      {qr_section}
      <div class="card" id="contact-box">
        <strong>इस वेबसाइट को अपने नंबर के साथ फाइनल करवाएँ:</strong>
        <p class="muted">मार्केट रेट: {html.escape(str(market_rate))} • हमारा डायरेक्ट सेटअप ऑफर: <strong>₹{offer_inr}</strong> (मोलभाव व अपने नाम के .in डोमेन के लिए बात करें)</p>
        <a class="btn-mail" href="mailto:{html.escape(bot_email)}?subject={urllib.parse.quote('Website Order: ' + lead.get('name', ''))}&body={urllib.parse.quote('Namaste, mujhe apni website (' + demo_url + ') final karwani hai. Mera phone number: ')}">📩 ईमेल से ऑर्डर / बदलाव भेजें</a>
      </div>
      {owner_btn_html}
    </div>
  </div>
</body>
</html>"""
    assert validate_html_gate(page_html, is_final), "HTML quality gate failed!"
    (out_dir / "index.html").write_text(page_html, encoding="utf-8")
    return {"slug": slug, "demoUrl": demo_url, "qrUrl": f"{demo_url}qr.png", "offerPriceInr": offer_inr, "marketRateInr": market_rate}


def build_upi_payment_page(lead: dict, amount_inr: int, upi_id: str, base_pages_url: str) -> str:
    slug = lead.get("slug") or slugify(lead.get("name", "client"))
    upi_uri = f"upi://pay?pa={urllib.parse.quote(upi_id)}&pn={urllib.parse.quote('Bharat Digital')}&am={amount_inr}&cu=INR&tn={urllib.parse.quote('Web Setup ' + slug[:18])}"
    make_qr_png(upi_uri, PAY_DIR / f"{slug}_upi.png")
    pay_html = f"""<!doctype html>
<html lang="hi">
<head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>UPI Payment — ₹{amount_inr}</title>
<style>body{{font-family:system-ui,sans-serif;background:#f0f2f5;text-align:center;padding:24px;}}.box{{max-width:420px;margin:0 auto;background:#fff;padding:24px;border-radius:14px;border:1px solid #e5e7eb;}}img{{width:220px;height:220px;}}.btn{{display:block;background:#1877F2;color:#fff;padding:14px;border-radius:10px;text-decoration:none;font-weight:700;margin-top:14px;}}</style>
</head>
<body><div class="box">
  <h2>{html.escape(lead.get('name', 'Client'))}</h2>
  <p>फाइनल वेबसाइट सेटअप शुल्क: <strong>₹{amount_inr}</strong></p>
  <img src="{slug}_upi.png" alt="UPI QR"/><br/>
  <a class="btn" href="{html.escape(upi_uri)}">📲 किसी भी UPI ऐप से ₹{amount_inr} पे करें</a>
  <p style="font-size:13px;color:#4b5563;">UPI ID: {html.escape(upi_id)}</p>
</div></body></html>"""
    (PAY_DIR / f"{slug}.html").write_text(pay_html, encoding="utf-8")
    return f"{base_pages_url.rstrip('/')}/pay/{slug}.html"


def rebuild_portfolio_index():
    demos = [d.name for d in sorted(DEMOS_DIR.iterdir()) if d.is_dir() and (d / "index.html").exists()]
    items = "\n".join(f'<li><a href="demos/{html.escape(d)}/">{html.escape(d)}</a></li>' for d in demos[-40:])
    (DOCS_DIR / "index.html").write_text(
        f"""<!doctype html><html lang="hi"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Bharat Digital — Live Demos</title>
<style>body{{font-family:system-ui,sans-serif;background:#f0f2f5;padding:20px;}}.card{{max-width:540px;margin:0 auto;background:#fff;padding:20px;border-radius:12px;border:1px solid #e5e7eb;}}li{{margin:8px 0;}}</style>
</head><body><div class="card"><h1>Bharat Digital — Live Business Demos</h1><ul>{items or '<li>No demos yet.</li>'}</ul></div></body></html>""",
        encoding="utf-8",
    )
