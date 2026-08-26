import os
import json
import time
import sys
from playwright.sync_api import sync_playwright

def main():
    print("🚀 Starting FMP Scraper...", flush=True)
    collected_data = {}
    
    try:
        with sync_playwright() as p:
            print("🌐 Launching browser...", flush=True)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # ✅ DEBUG: Response အကုန်လုံးကို စစ်ဆေးမယ်
            def handle_response(response):
                url = response.url
                status = response.status
                content_type = response.headers.get('content-type', '')
                
                # fmp သို့မဟုတ် api ပါတဲ့ URL အကုန်ကို Log ထဲမှာ ပြမယ်
                if 'fmp' in url.lower() or 'api' in url.lower():
                    print(f"🔍 Response: {status} {url} (Type: {content_type})", flush=True)
                
                try:
                    if 'json' in content_type.lower() and 'api.fmp.live/query' in url:
                        data = response.json()
                        print(f"✅ JSON Caught from {url}", flush=True)
                        if 'data' in data:
                            keys = list(data['data'].keys())
                            print(f"   Keys found: {keys[:5]}...", flush=True)
                            for key, value in data['data'].items():
                                collected_data[key] = value
                except Exception as e:
                    print(f"   Error parsing JSON from {url}: {e}", flush=True)

            page.on("response", handle_response)
            
            print("🌐 Navigating to fmp.live...", flush=True)
            page.goto("https://fmp.live/", wait_until="domcontentloaded")
            print("⏳ Waiting 5 seconds for initial load...", flush=True)
            time.sleep(5) 
            
            print("🔄 Reloading to clear cache...", flush=True)
            page.reload(wait_until="domcontentloaded")
            print("⏳ Waiting 10 seconds for data to load...", flush=True)
            time.sleep(10) 
            
            browser.close()
    except Exception as e:
        print(f"❌ Browser Error: {e}", flush=True)

    print(f"📊 Total keys collected: {len(collected_data)}", flush=True)
    if collected_data:
        print(f"   Keys: {list(collected_data.keys())}", flush=True)

    if not collected_data:
        print("❌ No data collected! Skipping file update.", flush=True)
        return

    print("🔄 Formatting data for frontend...", flush=True)
    frontend_matches = {}
    
    # ၁။ liveList (m3u8 Links)
    live_list = collected_data.get('liveList', [])
    if isinstance(live_list, list):
        print(f"   Processing {len(live_list)} live items...", flush=True)
        for live in live_list:
            comp = live.get('competition', {})
            match_id = str(comp.get('id'))
            m3u8_url = live.get('pullUrlM3U8')
            if not m3u8_url and live.get('streams'):
                for stream in live.get('streams', []):
                    if stream.get('m3u8'):
                        m3u8_url = stream.get('m3u8')
                        break
            links = [{"name": live.get('title', 'Live'), "url": m3u8_url}] if m3u8_url else []
            frontend_matches[match_id] = {
                "id": match_id, "home_name": comp.get('homeTeam', {}).get('nameEn', 'Home'),
                "home_img": comp.get('homeTeam', {}).get('logo', ''), "away_name": comp.get('awayTeam', {}).get('nameEn', 'Away'),
                "away_img": comp.get('awayTeam', {}).get('logo', ''), "league": comp.get('contest', {}).get('nameEn', 'League'),
                "match_time": comp.get('matchTime', ''), "match_status": comp.get('status') in ['FIRST_HALF', 'SECOND_HALF', 'LIVE', 'HALF_TIME'],
                "homeScore": comp.get('homeScore', 0), "awayScore": comp.get('awayScore', 0), "status": comp.get('status', 'LIVE'), "links": links
            }

    # ၂။ competitionFilterList
    comp_list = collected_data.get('competitionFilterList', [])
    if isinstance(comp_list, list):
        print(f"   Processing {len(comp_list)} competition items...", flush=True)
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
    print(f"💾 Saving {len(final_data)} matches to file...", flush=True)
    
    with open('fmp_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print("✅ Scraping finished successfully!", flush=True)

if __name__ == "__main__":
    main()
