from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import time

app = Flask(__name__)
CORS(app)

SEARCHAPI = "https://www.searchapi.io/api/v1/search"

def api(params):
    try:
        r = requests.get(SEARCHAPI, params=params, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/verify", methods=["POST"])
def verify():
    b = request.json
    domain = b.get("domain", "").strip()
    brand  = b.get("brand", "").strip()
    key    = b.get("key", "").strip()
    results = {}

    # GOOGLE
    go = api({"engine": "google_ads_transparency_center_advertiser_search", "q": domain, "api_key": key})
    go_opts = []
    for a in go.get("advertisers", [])[:5]:
        go_opts.append({
            "name": a.get("name", domain),
            "url": f"https://adstransparency.google.com/advertiser/{a.get('id')}?region=US",
            "verified": a.get("is_verified", False),
            "api_params": {"engine": "google_ads_transparency_center", "advertiser_id": a.get("id"), "region": "US", "num": 100, "time_period": "last_30_days"}
        })
    go_opts.append({
        "name": f"{domain} (by domain)",
        "url": f"https://adstransparency.google.com/?region=US&domain={domain}",
        "api_params": {"engine": "google_ads_transparency_center", "domain": domain, "region": "US", "num": 100, "time_period": "last_30_days"}
    })
    results["google"] = go_opts

    # META
    me = api({"engine": "meta_ad_library_page_search", "q": brand, "country": "us", "api_key": key})
    me_opts = []
    for p in me.get("pages", me.get("results", []))[:6]:
        pid = p.get("id") or p.get("page_id")
        me_opts.append({
            "name": p.get("name") or p.get("page_name") or brand,
            "url": f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&view_all_page_id={pid}&search_type=page",
            "likes": p.get("likes") or p.get("fan_count"),
            "category": p.get("category", ""),
            "verified": p.get("is_verified", False),
            "api_params": {"engine": "meta_ad_library", "page_id": pid, "ad_type": "all", "country": "US"}
        })
    me_opts.append({
        "name": f'"{brand}" keyword search',
        "url": f"https://www.facebook.com/ads/library/?q={brand}&ad_type=all&country=US",
        "api_params": {"engine": "meta_ad_library", "q": brand, "country": "US", "ad_type": "all"}
    })
    results["meta"] = me_opts

    # TIKTOK
    tt = api({"engine": "tiktok_ads_library_advertiser_search", "q": brand, "api_key": key})
    tt_opts = []
    for a in tt.get("advertisers", [])[:5]:
        tt_opts.append({
            "name": a.get("name", brand),
            "url": f"https://library.tiktok.com/ads?region=US&adv_name={a.get('name', brand)}",
            "api_params": {"engine": "tiktok_ads_library", "adv_biz_ids": a.get("id")}
        })
    tt_opts.append({
        "name": f'"{brand}" keyword search',
        "url": f"https://library.tiktok.com/ads?adv_name={brand}",
        "api_params": {"engine": "tiktok_ads_library", "q": brand}
    })
    results["tiktok"] = tt_opts
    return jsonify(results)

@app.route("/api/analyze", methods=["POST"])
def analyze():
    b = request.json
    key = b.get("key", "").strip()
    platforms = b.get("platforms", {})
    results = {}
    for plat, params in platforms.items():
        if params:
            params["api_key"] = key
            results[plat] = api(params)
            time.sleep(0.3)
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
