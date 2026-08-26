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
            # ✅ Headless Browser Detection ကို ရှောင်ရှားရန် Args များထည့်သွင်းခြင်း
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            
            # ✅ Realistic User Agent ထည့်သွင်းခြင်း
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            def handle_response(response):
                url = response.url
                content_type = response.headers.get('content-type', '')
                
                if 'fmp' in url.lower() or 'api' in url.lower():
                    print(f"🔍 Response: {response.status} {url} (Type: {content_type})", flush=True)
                
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
                    pass

            page.on("response", handle_response)
            
            print("🌐 Navigating to fmp.live...", flush=True)
            page.goto("https://fmp.live/", wait_until="domcontentloaded")
            time.sleep(5) 
            
            print("🔄 Reloading to clear cache...", flush=True)
            page.reload(wait_until="domcontentloaded")
            time.sleep(10) 
            
            # ✅ DEBUG: Page Title နဲ့ Content အနည်းငယ်ကို ပြမယ် (Cloudflare Block ဖြစ်/မဖြစ် သိရအောင်)
            title = page.title()
            print(f"📄 Page Title: {title}", flush=True)
            
            content_snippet = page.content()[:300]
            print(f"📄 Content Snippet: {content_snippet}...", flush=True)
            
            browser.close()
    except Exception as e:
        print(f"❌ Browser Error: {e}", flush=True)

    print(f"📊 Total keys collected: {len(collected_data)}", flush=True)

    if not collected_data:
        print("❌ No data collected! Skipping file update.", flush=True)
        return

    print("🔄 Formatting data for frontend...", flush=True)
    frontend_matches = {}
    
    live_list = collected_data.get('liveList', [])
    if isinstance(live_list, list):
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
    print(f"💾 Saving {len(final_data)} matches to file...", flush=True)
    
    with open('fmp_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print("✅ Scraping finished successfully!", flush=True)

if __name__ == "__main__":
    main()
