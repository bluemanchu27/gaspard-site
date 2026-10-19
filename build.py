#!/usr/bin/env python3
"""Builds the Gaspard & Co Real Estate website.

Reads the content files in content/ and writes the finished site to dist/.
Uses only Python's standard library, so Netlify can run it with no setup.

  python3 build.py              # build for the live site (Netlify runs this)
  python3 build.py --preview    # one-file-per-page preview with photos built in
"""
import base64, html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
STATIC = os.path.join(ROOT, "static")
OUT = os.path.join(ROOT, "dist")
PREVIEW = "--preview" in sys.argv

esc = html.escape


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def last_first(name):
    parts = name.split(" ", 1)
    return (parts[1] if len(parts) > 1 else parts[0], parts[0])


def digits(phone):
    return re.sub(r"\D", "", phone or "")


# ---------------------------------------------------------------- content
SITE = load(os.path.join(CONTENT, "site.json"))
LANDING = load(os.path.join(CONTENT, "gaspard-team-landing.json"))
FAQ_PATH = os.path.join(CONTENT, "faq.json")
FAQ = load(FAQ_PATH) if os.path.exists(FAQ_PATH) else {"groups": []}

AGENTS = []
for fn in sorted(os.listdir(os.path.join(CONTENT, "agents"))):
    if fn.endswith(".json"):
        a = load(os.path.join(CONTENT, "agents", fn))
        if a.get("hidden"):
            continue
        a["slug"] = slugify(a["name"])
        AGENTS.append(a)
AGENTS.sort(key=lambda a: last_first(a["name"]))
BY_SLUG = {a["slug"]: a for a in AGENTS}

TEAMS = []
for fn in sorted(os.listdir(os.path.join(CONTENT, "teams"))):
    if fn.endswith(".json"):
        t = load(os.path.join(CONTENT, "teams", fn))
        t["slug"] = fn[:-5]
        t["members"] = [a for a in AGENTS if a.get("team") == t["slug"]]
        TEAMS.append(t)
TEAMS.sort(key=lambda t: t.get("order", 99))
TEAM_NAME = {t["slug"]: t["name"] for t in TEAMS}

COMPANY = esc(SITE["company"])
OFFICE = esc(SITE["office_phone"])
FULL_ADDRESS = SITE["address"] + (" " + SITE["postal_code"] if SITE.get("postal_code") else "")
CSS = open(os.path.join(STATIC, "style.css"), encoding="utf-8").read()
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Charis+SIL:ital,wght@0,400;0,700;1,400&amp;family=Inter:wght@300;400;500;600&amp;display=swap">')


# ---------------------------------------------------------------- links
def url(path):
    """Site link. Live site: clean /agents/name/ style. Preview: relative file links."""
    return "/" + path if not PREVIEW else path


def page_url(path):
    if PREVIEW:  # preview pages are flat files side by side
        return "index.html" if path == "" else path.replace("/", "--") + ".html"
    return url("") if path == "" else url(path + "/")


def img(src):
    return src if not PREVIEW else src.lstrip("/")


# ---------------------------------------------------------------- shared parts
BASE = (SITE.get("site_url") or "https://gaspardandcorealestate.com").rstrip("/")
ORG_ID = BASE + "/#organization"


def ld_script(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + '</script>'


def org_ld():
    street, _, rest = SITE["address"].partition(",")
    parts = [x.strip() for x in rest.split(",")]
    addr = {"@type": "PostalAddress", "streetAddress": street.strip(),
            "addressLocality": parts[0] if parts else "", "addressRegion": parts[1] if len(parts) > 1 else "LA",
            "addressCountry": "US"}
    if SITE.get("postal_code"):
        addr["postalCode"] = SITE["postal_code"]
    org = {"@context": "https://schema.org", "@type": "RealEstateAgent", "@id": ORG_ID,
           "name": SITE["company"], "legalName": SITE.get("legal_name", ""), "url": BASE + "/",
           "logo": BASE + "/img/logo.svg", "image": BASE + "/img/office-sketch.jpg",
           "telephone": "+1-" + SITE["office_phone"], "email": SITE["office_email"], "address": addr,
           "foundingDate": "1979",
           "identifier": {"@type": "PropertyValue", "propertyID": "Louisiana Real Estate Commission brokerage license",
                          "value": SITE.get("brokerage_license", "")},
           "areaServed": [{"@type": "AdministrativeArea", "name": n} for n in SITE.get("area_served", [])]}
    if SITE.get("opening_hours"):
        org["openingHours"] = SITE["opening_hours"]
    if SITE.get("same_as"):
        org["sameAs"] = SITE["same_as"]
    return ld_script(org)


def agent_ld(a):
    slug = a["slug"]
    p = {"@context": "https://schema.org", "@type": "Person", "name": a["name"],
         "jobTitle": "Owner and REALTOR®" if slug == "scott-gaspard" else "REALTOR®",
         "url": f"{BASE}/agents/{slug}/", "image": BASE + (a.get("page_photo") or a["photo"]),
         "worksFor": {"@type": "RealEstateAgent", "@id": ORG_ID, "name": SITE["company"]},
         "telephone": "+1-" + (a.get("mobile") or SITE["office_phone"])}
    if a.get("email"):
        p["email"] = a["email"]
    links = [l["url"] for l in a.get("review_links", []) if l.get("url", "").strip()]
    if links:
        p["sameAs"] = links
    return ld_script(p)


def head(title, desc):
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{title}</title>\n<meta name="description" content="{desc}">\n'
            f'<link rel="icon" href="{img("/img/logo.svg")}">\n{FONTS}\n'
            f'<link rel="stylesheet" href="{url("style.css")}">\n</head>\n<body>\n')


def header(current):
    def nav(path, label, key):
        cur = ' aria-current="page"' if key == current else ''
        return f'<a href="{page_url(path)}"{cur}>{label}</a>'
    search = nav("search", "Search", "search") if SITE.get("idx_embed", "").strip() else ""
    return (f'<header class="site"><div class="wrap"><a class="logo" href="{page_url("")}">'
            f'<img src="{img("/img/logo.svg")}" alt="{COMPANY}" width="360" height="223"></a>'
            f'<nav aria-label="Main">{search}{nav("agents", "Agents", "agents")}{nav("about", "About", "about")}'
            f'<a href="tel:{digits(SITE["office_phone"])}">Call</a></nav></div></header>\n')


def footer():
    email = esc(SITE["office_email"])
    return (f'<footer class="site"><div class="wrap"><img src="{img("/img/logo.svg")}" alt="{COMPANY}" width="360" height="223" loading="lazy">'
            f'<div class="cols"><div><strong style="font-weight:600;color:var(--ink)">Office</strong><a href="tel:{digits(SITE["office_phone"])}">{OFFICE}</a></div>'
            f'<div><strong style="font-weight:600;color:var(--ink)">Email</strong><a href="mailto:{email}" style="overflow-wrap:anywhere">{email}</a></div>'
            f'<div><strong style="font-weight:600;color:var(--ink)">Address</strong><span>{esc(FULL_ADDRESS)}</span></div></div>'
            f'<p class="fine">{esc(SITE["legal_name"])}. Licensed by the Louisiana Real Estate Commission, brokerage license {esc(SITE["brokerage_license"])}. '
            'Equal Housing Opportunity.</p></div></footer>\n')


def tail():
    return "</body>\n</html>\n"


def card(a, sub=""):
    rl = f'<span class="rl">{esc(sub)}</span>' if sub else ''
    return (f'<a class="person" href="{page_url("agents/" + a["slug"])}"><span class="ph">'
            f'<img src="{img(a["photo"])}" alt="{esc(a["name"])}" loading="lazy" width="400" height="500"></span>'
            f'<span class="nm">{esc(a["name"])}</span>{rl}</a>')


def paragraphs(text):
    return "".join(f"<p>{esc(p.strip())}</p>" for p in re.split(r"\n\s*\n", text or "") if p.strip())


# ---------------------------------------------------------------- pages
def faq_html():
    groups = [g for g in FAQ.get("groups", []) if g.get("items")]
    if not groups:
        return ""
    out = ('<section class="faq" id="faq" aria-labelledby="fq"><div class="wrap"><div class="head"><h2 id="fq">'
           f'{esc(FAQ.get("heading", "Frequently asked questions"))}</h2></div>')
    if FAQ.get("intro"):
        out += f'<p class="lede">{esc(FAQ["intro"])}</p>'
    out += '<div class="faq-groups">'
    ld = []
    for g in groups:
        out += f'<div class="faq-group"><h3>{esc(g["name"])}</h3>'
        for it in g["items"]:
            out += f'<details><summary>{esc(it["q"])}</summary><p>{esc(it["a"])}</p></details>'
            ld.append({"@type": "Question", "name": it["q"], "acceptedAnswer": {"@type": "Answer", "text": it["a"]}})
        out += '</div>'
    out += '</div></div></section>'
    data = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": ld}, ensure_ascii=False).replace("</", "<\\/")
    return out + f'<script type="application/ld+json">{data}</script>'


def home():
    preview = [BY_SLUG[s] for s in SITE.get("home_preview", []) if s in BY_SLUG]
    s = head(COMPANY, f"{COMPANY}, a real estate company with local roots going back to 1979.")
    s += header("home")
    s += ('<main><div class="wrap"><section class="hero">'
          f'<img class="sketch" src="{img("/img/office-sketch.jpg")}" alt="Drawing of the {COMPANY} office on Jones Creek Road" width="948" height="925">'
          f'<div class="copy"><span class="eyebrow">{esc(SITE["home_eyebrow"])}</span>'
          f'<h1>{esc(SITE["home_headline"])}</h1><p>{esc(SITE["home_subline"])}</p>'
          f'<div class="actions"><a class="call" href="tel:{digits(SITE["office_phone"])}">Talk to an agent'
          f'<span style="font-weight:400;font-size:14px;opacity:.9">Call {OFFICE}</span></a>'
          f'<a class="arrow" href="{page_url("agents")}">See our agents</a></div></div></section>'
          f'<section class="block rule" aria-labelledby="ag"><div class="head"><h2 id="ag">Our agents</h2><a class="arrow" href="{page_url("agents")}">See all</a></div>'
          '<div class="grid wide" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr))">'
          + "".join(card(a) for a in preview) +
          f'</div><p style="margin:32px 0 0"><a class="arrow" href="{page_url("agents")}">Meet all of our agents</a></p></section></div>'
          '<section class="about" aria-labelledby="ab"><div class="wrap"><div class="inner"><span class="eyebrow">About the company</span>'
          f'<h2 id="ab">{COMPANY}</h2><p>{esc(SITE["company_story"])}</p></div></div></section>' + faq_html() + org_ld() + '</main>\n')
    return s + footer() + tail()


def agents_page():
    s = head(f"Our Agents | {COMPANY}", f"Meet the agents of {COMPANY}.")
    s += header("agents")
    s += ('<main><div class="wrap"><section class="block"><span class="eyebrow">Our agents</span>'
          '<h1 style="font-size:clamp(40px,6vw,60px);margin-top:12px">Meet our agents</h1>'
          '<div class="grid wide">' + "".join(card(a) for a in AGENTS) + '</div></section>')
    if TEAMS:
        s += '<section class="block rule" aria-labelledby="tt"><div class="head"><h2 id="tt">Our teams</h2></div><div class="teams">'
        for t in TEAMS:
            link = page_url("teams/" + t["slug"])
            pic = (f'<a href="{link}"><img class="group" src="{img(t["photo"])}" alt="{esc(t.get("photo_caption", t["name"]))}" loading="lazy"></a>'
                   if t.get("photo") else '<div class="placeholder">Team photo coming soon</div>')
            s += (f'<div class="team"><h3 class="label">{esc(t["name"])}</h3>{pic}'
                  f'<p style="margin:16px 0 0"><a class="arrow" href="{link}">Meet the team</a></p></div>')
        s += '</div></section>'
    s += '</div></main>\n'
    return s + footer() + tail()


def team_page(t):
    lead = next((a for a in t["members"] if a.get("team_lead")), None)
    s = head(f"{esc(t['name'])} | {COMPANY}", f"{esc(t['name'])} at {COMPANY}.")
    s += header("agents")
    s += (f'<main><div class="wrap"><p class="back"><a class="arrow" href="{page_url("agents")}" style="font-size:14px">All agents</a></p>'
          f'<section class="block" style="padding-top:24px"><span class="eyebrow">Our teams</span>'
          f'<h1 style="font-size:clamp(40px,6vw,60px);margin-top:12px">{esc(t["name"])}</h1>')
    if lead:
        s += f'<p class="lede">Led by <a href="{page_url("agents/" + lead["slug"])}">{esc(lead["name"])}</a></p>'
    if t.get("photo"):
        cap = esc(t.get("photo_caption", ""))
        s += (f'<div class="team" style="margin-top:28px"><img class="group" src="{img(t["photo"])}" alt="{cap}">'
              + (f'<p class="cap">{cap}, left to right</p>' if cap else '') + '</div>')
    s += '<div class="grid">' + "".join(card(a, "Team lead" if a.get("team_lead") else "") for a in t["members"]) + '</div></section></div></main>\n'
    return s + footer() + tail()


def reviews_html(a):
    quotes = [r for r in a.get("reviews", []) if r.get("quote", "").strip()]
    links = [l for l in a.get("review_links", []) if l.get("url", "").strip()]
    if not quotes and not links:
        return ""
    out = '<section class="reviews" aria-label="Client reviews"><h2>What clients say</h2>'
    for r in quotes:
        who = esc(r.get("client", ""))
        if r.get("detail"):
            who += " · " + esc(r["detail"])
        out += f'<blockquote><p>{esc(r["quote"])}</p><footer>{who}</footer></blockquote>'
    if links:
        out += '<div class="rlinks">' + "".join(
            f'<a class="arrow" href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(l.get("label") or "Read more reviews")}</a>' for l in links) + '</div>'
    return out + '</section>'


def agent_page(a):
    name = esc(a["name"])
    team = TEAM_NAME.get(a.get("team", ""), "")
    bio = paragraphs(a.get("bio", "")) or '<p class="soon">Bio coming soon.</p>'
    photo = a.get("page_photo") or a["photo"]
    mobile = a.get("mobile", "")
    rows = ""
    if mobile:
        rows += f'<div><span>Mobile</span><span>{esc(mobile)}</span></div>'
    if a.get("email"):
        e = esc(a["email"])
        rows += f'<div><span>Email</span><span style="overflow-wrap:anywhere"><a href="mailto:{e}">{e}</a></span></div>'
    rows += f'<div><span>Office</span><span>{OFFICE}</span></div>'
    callnum = mobile or SITE["office_phone"]
    s = head(f"{name} | {COMPANY}", f"{name}, REALTOR® with {COMPANY}.")
    s += header("agents")
    s += (f'<main><div class="wrap"><p class="back"><a class="arrow" href="{page_url("agents")}" style="font-size:14px">All agents</a></p>'
          f'<article class="agent"><div class="photo"><img src="{img(photo)}" alt="{name}"></div>'
          f'<div class="info"><span class="eyebrow">{esc(team) if team else "REALTOR®"}</span><h1>{name}</h1>'
          f'<a class="call" href="tel:{digits(callnum)}">Call {esc(callnum)}</a>'
          f'<div class="meta">{rows}</div><div class="bio">{bio}</div>{reviews_html(a)}</div></article></div>' + agent_ld(a) + '</main>\n')
    return s + footer() + tail()


def about_page():
    s = head(f"About | {COMPANY}", f"About {COMPANY}.")
    s += header("about")
    s += ('<main><div class="wrap"><section class="block" style="max-width:720px"><span class="eyebrow">About the company</span>'
          f'<h1 style="font-size:clamp(40px,6vw,60px);margin-top:12px">{COMPANY}</h1>'
          f'<p class="lede" style="font-size:20px;line-height:1.7;margin-top:22px">{esc(SITE["company_story"])}</p></section>'
          '<section class="block rule" style="max-width:720px"><h2 style="font-size:32px">Visit or call</h2>'
          '<div class="agent" style="padding:20px 0 0;display:block"><div class="meta">'
          f'<div><span>Office</span><span>{esc(FULL_ADDRESS)}</span></div>'
          f'<div><span>Phone</span><span><a href="tel:{digits(SITE["office_phone"])}">{OFFICE}</a></span></div>'
          f'<div><span>Email</span><span style="overflow-wrap:anywhere"><a href="mailto:{esc(SITE["office_email"])}">{esc(SITE["office_email"])}</a></span></div>'
          '</div></div></section>'
          '<section class="block rule" style="max-width:720px" id="contact"><h2 style="font-size:32px">Send us a message</h2>'
          '<p class="lede" style="font-size:17px">Tell us what you need and the right agent will get back to you.</p>'
          f'<form class="cform" id="cc" name="company-contact" method="POST" action="{page_url("thanks")}" data-netlify="true" netlify-honeypot="company" novalidate>'
          '<input type="hidden" name="form-name" value="company-contact">'
          '<label class="hp">Leave this empty<input name="company" tabindex="-1" autocomplete="off"></label>'
          '<label for="cc-name">Name<input id="cc-name" name="name" autocomplete="name"></label>'
          '<label for="cc-phone">Phone<input id="cc-phone" name="phone" type="tel" autocomplete="tel"></label>'
          '<label for="cc-email">Email (optional)<input id="cc-email" name="email" type="email" autocomplete="email"></label>'
          '<label for="cc-need">I\'m looking to<select id="cc-need" name="need"><option>Sell</option><option>Buy</option><option>Buy and sell</option><option>Talk about joining Gaspard &amp; Co Real Estate</option><option>Something else</option></select></label>'
          '<label for="cc-msg">Message<textarea id="cc-msg" name="message"></textarea></label>'
          '<p class="err" id="cc-err" hidden>Please add your name and phone number.</p>'
          '<button type="submit">Send message</button></form>'
          '<script>(function(){var f=document.getElementById("cc");f.addEventListener("submit",function(e){var ok=["cc-name","cc-phone"].every(function(i){return document.getElementById(i).value.trim()!==""});document.getElementById("cc-err").hidden=ok;if(!ok)e.preventDefault();});})();</script>'
          '</section></div>' + org_ld() + '</main>\n')
    return s + footer() + tail()


def search_page():
    embed = SITE.get("idx_embed", "").strip()
    s = head(f"Search Homes | {COMPANY}", f"Search homes for sale with {COMPANY}.")
    s += header("search")
    s += '<main><div class="wrap"><section class="block"><span class="eyebrow">Search homes</span>'
    if embed:
        s += f'<h1 style="font-size:clamp(40px,6vw,60px);margin-top:12px">Homes for sale</h1><div style="margin-top:28px">{embed}</div>'
    else:
        s += ('<h1 style="font-size:clamp(40px,6vw,60px);margin-top:12px">Home search is coming soon</h1>'
              '<p class="lede">In the meantime, call the office and an agent will send you homes that fit what you want.</p>'
              f'<p style="margin-top:24px"><a class="call" href="tel:{digits(SITE["office_phone"])}">Call {OFFICE}</a></p>')
    s += '</section></div></main>\n'
    return s + footer() + tail()


def thanks_page():
    s = head(f"Thank you | {COMPANY}", "Thanks for reaching out.")
    s += header("")
    s += ('<main><div class="wrap"><section class="block" style="max-width:640px"><span class="eyebrow">Message received</span>'
          '<h1 style="font-size:clamp(40px,6vw,60px);margin-top:12px">Thank you.</h1>'
          '<p class="lede">We got your message and will be in touch soon. If you need us sooner, give the office a call.</p>'
          f'<p style="margin-top:24px"><a class="call" href="tel:{digits(SITE["office_phone"])}">Call {OFFICE}</a></p>'
          f'<p style="margin-top:28px"><a class="arrow" href="{page_url("")}">Back to the home page</a></p></section></div></main>\n')
    return s + footer() + tail()


def landing_page():
    L = LANDING
    tpl = open(os.path.join(ROOT, "templates", "gaspard-team.html"), encoding="utf-8").read()
    quotes = [r for r in L.get("reviews", []) if r.get("quote", "").strip()]
    if quotes:
        rv = "".join(f'<blockquote><p>{esc(r["quote"])}</p><footer>{esc(r.get("client", ""))}'
                     + (f' · {esc(r["detail"])}' if r.get("detail") else '') + '</footer></blockquote>' for r in quotes)
    else:
        rv = ""
    video = ""
    if L.get("video_url", "").strip():
        video = (f'<section class="rule" aria-label="Team video"><span class="eyebrow">Get to know us</span>'
                 f'<p style="margin-top:14px"><a class="more" href="{esc(L["video_url"])}" target="_blank" rel="noopener">Watch our team video</a></p></section>')
    team = next((t for t in TEAMS if t["slug"] == "gaspard-team"), None)
    people = ""
    for a in (team["members"] if team else []):
        role = "Team lead" if a.get("team_lead") else "REALTOR®"
        people += (f'<figure><img src="{img(a["photo"])}" alt="{esc(a["name"])}"><figcaption>'
                   f'<div class="nm">{esc(a["name"])}</div><div class="rl">{role}</div></figcaption></figure>')
    rep = {
        "{{CELL}}": digits(L["cell"]),
        "{{RATING}}": esc(L.get("rating_line", "")),
        "{{REVIEWS}}": rv,
        "{{ZILLOW}}": esc(L.get("zillow_url", "")),
        "{{GOOGLE}}": esc(L.get("google_url", "")),
        "{{HEADLINE}}": esc(L.get("headline", "")),
        "{{INTRO}}": esc(L.get("intro", "")),
        "{{VIDEO}}": video,
        "{{PEOPLE}}": people,
        "{{IMG}}": img("/img/").rstrip("/"),
        "{{THANKS}}": page_url("thanks"),
        "{{OFFICE}}": OFFICE,
        "{{ADDRESS}}": esc(FULL_ADDRESS),
        "{{LEGAL}}": esc(SITE["legal_name"]),
        "{{LICENSE}}": esc(SITE["brokerage_license"]),
        "{{HOME}}": page_url(""),
    }
    for k, v in rep.items():
        tpl = tpl.replace(k, v)
    if not quotes:
        tpl = re.sub(r'\s*<div class="reviews">\s*</div>', "", tpl)
    return tpl


# ---------------------------------------------------------------- write
def inline_assets(s):
    def rep(m):
        path = os.path.join(STATIC, m.group(2))
        ext = path.rsplit(".", 1)[1].lower()
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "svg": "image/svg+xml", "webp": "image/webp"}[ext]
        with open(path, "rb") as f:
            return m.group(1) + f"data:{mime};base64," + base64.b64encode(f.read()).decode() + '"'
    s = re.sub(r'((?:src|href)=")(img/[^"]+)"', rep, s)
    s = s.replace('<link rel="stylesheet" href="style.css">', "<style>" + CSS + "</style>")
    return s


def write(path, s):
    if PREVIEW:
        if path.endswith("/index.html"):
            path = path[:-len("/index.html")].replace("/", "--") + ".html"
        s = inline_assets(s)
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(s)


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    if not PREVIEW:
        shutil.copytree(STATIC, OUT, dirs_exist_ok=True)
    write("index.html", home())
    write("agents/index.html", agents_page())
    write("about/index.html", about_page())
    write("search/index.html", search_page())
    write("thanks/index.html", thanks_page())
    write("gaspard-team/index.html", landing_page())
    for t in TEAMS:
        write(f"teams/{t['slug']}/index.html", team_page(t))
    for a in AGENTS:
        write(f"agents/{a['slug']}/index.html", agent_page(a))
    if not PREVIEW:  # help search engines find every page
        base = SITE.get("site_url", "https://gaspardandcorealestate.com").rstrip("/")
        paths = ["", "agents/", "about/", "search/", "gaspard-team/"] + [f"teams/{t['slug']}/" for t in TEAMS] + [f"agents/{a['slug']}/" for a in AGENTS]
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        sm += "".join(f"  <url><loc>{base}/{p}</loc></url>\n" for p in paths) + "</urlset>\n"
        open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(sm)
        open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    if PREVIEW:  # artifact entry page: body only
        s = open(os.path.join(OUT, "index.html"), encoding="utf-8").read()
        s = re.sub(r"^<!doctype html>.*?<head>\s*<meta charset=\"utf-8\">\s*<meta name=\"viewport\"[^>]*>\s*", "", s, flags=re.S)
        s = s.replace("</head>\n<body>\n", "").replace("</body>\n</html>\n", "")
        open(os.path.join(OUT, "_artifact_index.html"), "w", encoding="utf-8").write(s)
    print(f"Built {len(AGENTS)} agents, {len(TEAMS)} teams into {OUT}")


if __name__ == "__main__":
    main()
