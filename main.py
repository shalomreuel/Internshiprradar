import csv, hashlib, html, json, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
CFG = json.loads((ROOT / "config.json").read_text())
TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {"User-Agent": "AI-Internship-Discovery/1.2", "Accept": "application/vnd.github+json"}
if TOKEN: HEADERS["Authorization"] = f"Bearer {TOKEN}"
FIELDS = ["id","title","company","location","source","url","posted_at","description","score","matched_terms","discovered_at"]
REF_FIELDS = ["company","github_org","name","login","profile_url","bio","company_text","location","followers","public_repos","engineering_signal","reason","source"]
STATS = {}

def clean(v):
    if isinstance(v, (dict, list)): v = json.dumps(v, ensure_ascii=False)
    v = html.unescape(re.sub(r"<[^>]+>", " ", str(v or "")))
    return re.sub(r"\s+", " ", v).strip()

def get_json(url, params=None, source="unknown"):
    STATS.setdefault(source, {"requests":0, "accepted":0, "errors":0})
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status(); STATS[source]["requests"] += 1
        return r.json()
    except Exception as e:
        STATS[source]["errors"] += 1
        print(f"[WARN] {source}: {e}", file=sys.stderr)
        return None

def add(rows, source, title, company, location, url, posted="", description="", remote_hint=False):
    title, company, location, url = clean(title), clean(company), clean(location), clean(url)
    desc = clean(description)[:6000]
    if not title or not url: return
    blob = f"{title} {desc}".lower()
    matched = [k for k in CFG["keywords"] if k in blob]
    student = any(t in blob for t in CFG["role_terms"])
    bad = any(x in blob for x in CFG["exclude_terms"])
    loc = location.lower()
    india = any(x in loc for x in ["india","bengaluru","bangalore","chennai","hyderabad","pune","mumbai","delhi","noida","gurugram","gurgaon","tamil nadu"])
    remote = remote_hint or any(x in loc for x in ["remote","worldwide","anywhere","global","distributed","work from home"]) or any(x in blob for x in ["remote worldwide","work remotely","remote position"])
    if not (matched and student and not bad and (india or remote)): return
    score = 25 + min(35, len(matched)*5) + (15 if india else 0) + (15 if remote else 0)
    if any(x in title.lower() for x in ["research","scientist"]): score += 10
    if any(x in title.lower() for x in ["computer vision","machine learning","ai","ml","genai","llm"]): score += 10
    uid = hashlib.sha1((source+"|"+url).encode()).hexdigest()[:16]
    rows.append({"id":uid,"title":title,"company":company,"location":location or ("Remote" if remote else ""),"source":source,"url":url,"posted_at":clean(posted),"description":desc,"score":score,"matched_terms":", ".join(matched),"discovered_at":datetime.now(timezone.utc).isoformat()})
    STATS[source]["accepted"] += 1

def remoteok(rows):
    data=get_json("https://remoteok.com/api", source="RemoteOK")
    if not isinstance(data,list): return
    for j in data:
        if not isinstance(j,dict): continue
        desc=f"{j.get('description','')} {' '.join(j.get('tags') or [])}"
        add(rows,"RemoteOK",j.get("position") or j.get("title"),j.get("company"),"Remote worldwide",j.get("url"),j.get("date"),desc,True)

def remotive(rows):
    data=get_json("https://remotive.com/api/remote-jobs", source="Remotive")
    for j in (data.get("jobs",[]) if isinstance(data,dict) else []):
        add(rows,"Remotive",j.get("title"),j.get("company_name"),j.get("candidate_required_location") or "Remote",j.get("url"),j.get("publication_date"),j.get("description",""),True)

def arbeitnow(rows):
    for page in range(1,int(CFG.get("max_pages_arbeitnow",3))+1):
        data=get_json("https://www.arbeitnow.com/api/job-board-api",{"page":page},"Arbeitnow")
        if not data: break
        jobs=data.get("data",[])
        if not jobs: break
        for j in jobs:
            add(rows,"Arbeitnow",j.get("title"),j.get("company_name"),j.get("location",""),j.get("url"),j.get("created_at"),j.get("description",""),bool(j.get("remote")))

def greenhouse(rows):
    for board in CFG.get("greenhouse_boards",[]):
        data=get_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",{"content":"true"},f"Greenhouse:{board}")
        if not data: continue
        for j in data.get("jobs",[]): add(rows,f"Greenhouse:{board}",j.get("title"),board,(j.get("location") or {}).get("name",""),j.get("absolute_url"),j.get("updated_at"),j.get("content",""))

def lever(rows):
    for site in CFG.get("lever_sites",[]):
        data=get_json(f"https://api.lever.co/v0/postings/{site}",{"mode":"json"},f"Lever:{site}")
        if not isinstance(data,list): continue
        for j in data:
            c=j.get("categories") or {}
            add(rows,f"Lever:{site}",j.get("text"),site,c.get("location",""),j.get("hostedUrl"),j.get("createdAt"),j.get("descriptionPlain") or j.get("description",""),"remote" in c.get("commitment","").lower())

def ashby(rows):
    for board in CFG.get("ashby_boards",[]):
        data=get_json(f"https://api.ashbyhq.com/posting-api/job-board/{board}",source=f"Ashby:{board}")
        if not data: continue
        for j in data.get("jobs",[]): add(rows,f"Ashby:{board}",j.get("title"),board,j.get("location") or "",j.get("jobUrl"),j.get("publishedAt"),j.get("descriptionPlain") or j.get("descriptionHtml",""),bool(j.get("isRemote")))

def referrals():
    rows=[]; cache=DATA/".github_cache"; cache.mkdir(exist_ok=True)
    keys=["machine learning","artificial intelligence","ai engineer","ml engineer","research scientist","research engineer","computer vision","generative ai","llm","nlp","robotics","software engineer","developer","research"]
    STATS["GitHub referrals"]={"requests":0,"accepted":0,"errors":0}
    for t in CFG.get("referral_targets",[]):
        org,company=t.get("github_org"),t.get("company")
        if not org: continue
        members=get_json(f"https://api.github.com/orgs/{org}/public_members",{"per_page":100},"GitHub referrals")
        if not isinstance(members,list): continue
        for m in members:
            login=m.get("login")
            if not login: continue
            cf=cache/f"{org}__{login}.json"; profile=None
            if cf.exists():
                try: profile=json.loads(cf.read_text())
                except Exception: profile=None
            if profile is None:
                profile=get_json(f"https://api.github.com/users/{login}",source="GitHub referrals")
                if profile: cf.write_text(json.dumps(profile))
                time.sleep(.1)
            if not profile: continue
            blob=" ".join([clean(profile.get("name")),clean(profile.get("bio")),clean(profile.get("company")),clean(profile.get("location"))]).lower()
            hits=[k for k in keys if k in blob]
            if not hits: continue
            signal=min(100,len(hits)*12+min(30,int(profile.get("public_repos") or 0)//3)+(15 if "engineer" in blob or "developer" in blob else 0)+(15 if "research" in blob or "scientist" in blob else 0))
            rows.append({"company":company,"github_org":org,"name":clean(profile.get("name")) or login,"login":login,"profile_url":profile.get("html_url") or f"https://github.com/{login}","bio":clean(profile.get("bio")),"company_text":clean(profile.get("company")),"location":clean(profile.get("location")),"followers":profile.get("followers",0),"public_repos":profile.get("public_repos",0),"engineering_signal":signal,"reason":"Public technical profile matches: "+", ".join(hits[:6]),"source":"Public GitHub profile / org membership"})
    rows.sort(key=lambda x:x["engineering_signal"],reverse=True)
    with (DATA/"referral_targets.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=REF_FIELDS); w.writeheader(); w.writerows(rows)
    with (DATA/"referral_targets.md").open("w",encoding="utf-8") as f:
        f.write(f"# Referral targets\n\nFound **{len(rows)}** public GitHub profiles with technical overlap.\n\n")
        f.write("> These are public-profile relevance signals, not claims that someone recruits or can refer you.\n\n")
        for r in rows[:75]: f.write(f"## [{r['name']}]({r['profile_url']}) — {r['company']}\n**Signal:** {r['engineering_signal']} · **{r['login']}** · **{r['location'] or 'location not listed'}\n**Bio:** {r['bio'] or 'not listed'}\n**Why surfaced:** {r['reason']}\n\n")
    return len(rows)

def main():
    rows=[]
    remoteok(rows); remotive(rows); arbeitnow(rows); greenhouse(rows); lever(rows); ashby(rows)
    uniq={r["url"].split("?")[0]:r for r in rows}
    rows=sorted(uniq.values(),key=lambda x:(int(x["score"]),x["posted_at"]),reverse=True)[:int(CFG.get("max_results",300))]
    with (DATA/"opportunities.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    with (DATA/"daily_digest.md").open("w",encoding="utf-8") as f:
        f.write(f"# AI internship opportunities — {datetime.now():%Y-%m-%d}\n\nFound **{len(rows)}** matching listings.\n\n")
        f.write("Sources scanned: **"+", ".join(STATS.keys())+"**.\n\n> Verify eligibility, location, pay and deadline on the employer's official page.\n\n")
        for r in rows[:100]: f.write(f"## [{r['title']}]({r['url']})\n**{r['company']}** · {r['location']} · {r['source']} · Relevance: {r['score']}\nMatched: {r['matched_terms']}\n\n")
    (DATA/"discovery_debug.json").write_text(json.dumps(STATS,indent=2),encoding="utf-8")
    n=referrals()
    print(json.dumps({"opportunities":len(rows),"referral_targets":n,"stats":STATS},indent=2))

if __name__ == "__main__": main()
