import csv, hashlib, html, json, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
CFG = json.loads((ROOT / "config.json").read_text())
GH_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
HEADERS = {"User-Agent": "AI-Internship-Discovery/1.1 (student career research)", "Accept": "application/vnd.github+json"}
if GH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GH_TOKEN}"

FIELDS = ["id","title","company","location","source","url","posted_at","description","score","matched_terms","discovered_at"]
REF_FIELDS = ["company","github_org","name","login","profile_url","bio","company_text","location","followers","public_repos","technical_signal","reason","source"]

def clean(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", value).strip()

def get(url, params=None, headers=None):
    h = dict(HEADERS)
    if headers: h.update(headers)
    try:
        r = requests.get(url, params=params, headers=h, timeout=25)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[WARN] {url}: {e}", file=sys.stderr)
        return None

def add(rows, title, company, location, source, url, posted="", description=""):
    title, company, location = clean(title), clean(company), clean(location)
    description = clean(description)[:5000]
    if not title or not url: return
    text = f"{title} {description}".lower()
    kws = [k for k in CFG["keywords"] if k.lower() in text]
    role = any(t in title.lower() for t in CFG["role_terms"])
    if not kws or not role: return
    if any(x in f"{title} {description}".lower() for x in CFG["exclude_terms"]): return
    loc = location.lower()
    india = any(x in loc for x in ["india","bengaluru","bangalore","chennai","hyderabad","pune","mumbai","delhi","noida","gurugram","gurgaon"])
    remote = any(x in loc for x in ["remote","worldwide","anywhere","distributed","work from home"])
    if not (india or remote): return
    score = 20 + min(30, len(kws) * 5)
    if india: score += 15
    if remote: score += 15
    if "research" in title.lower(): score += 10
    if any(x in title.lower() for x in ["machine learning","artificial intelligence","computer vision","genai","llm","ml "]): score += 10
    uid = hashlib.sha1((source + "|" + url).encode()).hexdigest()[:16]
    rows.append({"id":uid,"title":title,"company":company,"location":location,"source":source,"url":url,"posted_at":clean(posted),"description":description,"score":score,"matched_terms":", ".join(kws),"discovered_at":datetime.now(timezone.utc).isoformat()})

def greenhouse(rows):
    for board in CFG.get("greenhouse_boards", []):
        data = get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", {"content":"true"})
        if not data: continue
        for j in data.get("jobs", []):
            add(rows,j.get("title"),board,(j.get("location") or {}).get("name",""),"Greenhouse",j.get("absolute_url"),j.get("updated_at"),j.get("content",""))

def lever(rows):
    for site in CFG.get("lever_sites", []):
        data = get(f"https://api.lever.co/v0/postings/{site}", {"mode":"json"})
        if not isinstance(data,list): continue
        for j in data:
            cats = j.get("categories") or {}
            add(rows,j.get("text"),site,cats.get("location") or "","Lever",j.get("hostedUrl"),j.get("createdAt"),j.get("descriptionPlain") or j.get("description",""))

def ashby(rows):
    for board in CFG.get("ashby_boards", []):
        data = get(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
        if not data: continue
        for j in data.get("jobs", []):
            loc = j.get("location") or ""
            if j.get("isRemote"): loc = f"{loc} Remote"
            add(rows,j.get("title"),board,loc,"Ashby",j.get("jobUrl"),j.get("publishedAt"),j.get("descriptionPlain") or j.get("descriptionHtml",""))

def remoteok(rows):
    data = get("https://remoteok.com/api")
    if not isinstance(data,list): return
    for j in data:
        if not isinstance(j,dict) or not j.get("position"): continue
        tags = " ".join(j.get("tags") or [])
        add(rows,j.get("position"),j.get("company"),"Remote worldwide","RemoteOK",j.get("url"),j.get("date"),f"{j.get('description','')} {tags}")

def arbeitnow(rows):
    for page in range(1,int(CFG.get("max_pages_arbeitnow",3))+1):
        data = get("https://www.arbeitnow.com/api/job-board-api", {"page":page})
        if not data: break
        jobs = data.get("data",[])
        if not jobs: break
        for j in jobs:
            loc = j.get("location","")
            if j.get("remote"): loc += " Remote"
            add(rows,j.get("title"),j.get("company_name"),loc,"Arbeitnow",j.get("url"),j.get("created_at"),j.get("description",""))

def github_referrals():
    targets = CFG.get("referral_targets", [])
    if not targets:
        print("[INFO] No referral_targets configured; skipping referrals.")
        return
    out_rows = []
    cache_dir = DATA / ".github_cache"
    cache_dir.mkdir(exist_ok=True)
    keywords = [k.lower() for k in CFG.get("referral_keywords", [])]
    for target in targets:
        company, org = target.get("company",""), target.get("github_org","")
        if not org: continue
        data = get(f"https://api.github.com/orgs/{org}/public_members", {"per_page": min(int(CFG.get("github_members_per_org",100)),100)})
        if not isinstance(data,list): continue
        for m in data:
            login = m.get("login")
            if not login: continue
            pf = cache_dir / f"{org}__{login}.json"
            profile = None
            if pf.exists():
                try: profile = json.loads(pf.read_text())
                except Exception: profile = None
            if profile is None:
                profile = get(f"https://api.github.com/users/{login}")
                if profile: pf.write_text(json.dumps(profile))
                time.sleep(0.10)
            if not profile: continue
            blob = " ".join([clean(profile.get("name")),clean(profile.get("bio")),clean(profile.get("company")),clean(profile.get("location"))]).lower()
            hits = [k for k in keywords if k in blob]
            if not hits: continue
            technical_signal = min(100, len(hits)*12 + min(30,int(profile.get("public_repos") or 0)//3) + (15 if "engineer" in blob or "developer" in blob else 0) + (15 if "research" in blob or "scientist" in blob else 0))
            out_rows.append({"company":company,"github_org":org,"name":clean(profile.get("name")) or login,"login":login,"profile_url":profile.get("html_url") or f"https://github.com/{login}","bio":clean(profile.get("bio")),"company_text":clean(profile.get("company")),"location":clean(profile.get("location")),"followers":profile.get("followers",0),"public_repos":profile.get("public_repos",0),"technical_signal":technical_signal,"reason":"Public GitHub profile matches: " + ", ".join(hits[:6]),"source":"Public GitHub profile / org membership"})
    out_rows.sort(key=lambda x:x["technical_signal"],reverse=True)
    out = DATA / "referral_targets.csv"
    with out.open("w",newline="",encoding="utf-8-sig") as f:
        w = csv.DictWriter(f,fieldnames=REF_FIELDS); w.writeheader(); w.writerows(out_rows)
    md = ["# Referral targets","",f"Found **{len(out_rows)}** public GitHub profiles associated with configured organizations.","","> This is a public-profile technical relevance signal. It is not a claim that someone is a recruiter, hiring manager, or willing to refer you.",""]
    for r in out_rows[:75]:
        md += [f"## [{r['name']}]({r['profile_url']}) — {r['company']}",f"**Signal:** {r['technical_signal']} · **GitHub:** `{r['login']}` · **Location:** {r['location'] or 'not listed'}",f"**Bio:** {r['bio'] or 'not listed'}",f"**Why surfaced:** {r['reason']}",""]
    (DATA / "referral_targets.md").write_text("\n".join(md),encoding="utf-8")

def main():
    rows=[]
    greenhouse(rows); lever(rows); ashby(rows); remoteok(rows); arbeitnow(rows)
    unique={r["url"].split("?")[0]:r for r in rows}
    rows=sorted(unique.values(),key=lambda x:(int(x["score"]),x["posted_at"]),reverse=True)[:int(CFG.get("max_results",250))]
    out=DATA/"opportunities.csv"
    with out.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    today=datetime.now().strftime("%Y-%m-%d")
    md=[f"# AI internship opportunities — {today}","",f"Found **{len(rows)}** matching listings.","","> Verify eligibility, location, pay and deadline on the employer's official page.",""]
    for r in rows[:60]: md += [f"## [{r['title']}]({r['url']})",f"**{r['company']}** · {r['location']} · {r['source']} · Relevance score: {r['score']}",f"Matched: {r['matched_terms']}",""]
    (DATA/"daily_digest.md").write_text("\n".join(md),encoding="utf-8")
    github_referrals()
    print(f"Saved {len(rows)} opportunities and referral intelligence outputs.")

if __name__ == "__main__": main()
