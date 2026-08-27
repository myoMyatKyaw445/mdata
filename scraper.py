import os
import json
import time
from playwright.sync_api import sync_playwright
from pymongo import MongoClient, ReplaceOne

MONGO_URI = os.environ.get("MONGODB_URI")

def scrape_and_update():
    print("🚀 Starting FMP Scraper on GitHub Actions...", flush=True)
    collected_data = {}
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # ✅ Real User လို ပြသဖို့ Context ထည့်သွင်းခြင်း
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            def handle_response(response):
                try:
                    if 'json' in response.headers.get('content-type', '') and 'api.fmp.live/query' in response.url:
                        data = response.json()
                        if 'data' in data:
                            for key, value in data['data'].items():
                                collected_data[key] = value
                except:
                    pass

            page.on("response", handle_response)
            
            # ✅ Extra Headers ထည့်သွင်းခြင်း
            page.set_extra_http_headers({
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://fmp.live/"
            })
            
            page.goto("https://fmp.live/", wait_until="domcontentloaded")
            time.sleep(4)
            page.reload(wait_until="domcontentloaded")
            time.sleep(6)
            browser.close()
            
    except Exception as e:
        print(f"❌ Browser Error: {e}", flush=True)
        return

    if not collected_data:
        print("❌ No data collected! (Likely blocked by Cloudflare)", flush=True)
        return

    print(f"🔄 Processing {len(collected_data)} keys...", flush=True)
    frontend_matches = {}
    
    live_list = collected_data.get('liveList', [])
    if isinstance(live_list, list):
        for live in live_list:
            comp = live.get('competition', {})
            match_id = str(comp.get('id'))
            m3u8_url = live.get('pullUrlM3U8')
            if not m3u8_url and live.get('streams'):
                for stream in live.get('streams', []):
                    if stream.get('m3u8'): m3u8_url = stream.get('m3u8'); break
            links = [{"name": live.get('title', 'Live'), "url": m3u8_url}] if m3u8_url else []
            frontend_matches[match_id] = {
                "id": match_id, "home_name": comp.get('homeTeam', {}).get('nameEn', 'Home'),
                "home_img": comp.get('homeTeam', {}).get('logo', ''), "away_name": comp.get('awayTeam', {}).get('nameEn', 'Away'),
                "away_img": comp.get('awayTeam', {}).get('logo', ''), "league": comp.get('contest', {}).get('nameEn', 'League'),
                "match_time": comp.get('matchTime', ''), "match_status": comp.get('status') in ['FIRST_HALF', 'SECOND_HALF', 'LIVE', 'HALF_TIME'],
                "homeScore": comp.get('homeScore', 0), "awayScore": comp.get('awayScore', 0), "status": comp.get('status', 'LIVE'), "links": links
            }

    comp_list = collected_data.get('competitionFilterList', [])
    if isinstance(comp_list, list):
        for comp in comp_list:
            match_id = str(comp.get('id'))
            if match_id not in frontend_matches:
                frontend_matches[match_id] = {
                    "id": match_id, "home_name": comp.get('homeTeam', {}).get('nameEn', 'Home'),
                    "home_img": comp.get('homeTeam', {}).get('logo', ''), "away_name": comp.get('awayTeam', {}).get('nameEn', 'Away'),
                    "away_img": comp.get('awayTeam', {}).get('logo', ''), "league": comp.get('contest', {}).get('nameEn', 'League'),
                    "match_time": comp.get('matchTime', ''), "match_status": comp.get('status') in ['FIRST_HALF', 'SECOND_HALF', 'LIVE', 'HALF_TIME'],
                    "homeScore": comp.get('homeScore', 0), "awayScore": comp.get('awayScore', 0), "status": comp.get('status', 'SCHEDULED'), "links": []
                }

    final_data = list(frontend_matches.values())
    
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client["fmp_database"]
        collection = db["matches"]
        operations = [ReplaceOne({"id": match["id"]}, match, upsert=True) for match in final_data]
        result = collection.bulk_write(operations)
        print(f"☁️ Successfully updated {result.upserted_count + result.modified_count} matches in MongoDB!", flush=True)
        client.close()
    except Exception as e:
        print(f"❌ MongoDB Error: {e}", flush=True)
    
    with open('fmp_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    print("💾 Saved to fmp_data.json", flush=True)

if __name__ == "__main__":
    scrape_and_update()
