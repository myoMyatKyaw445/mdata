import os
import json
import time
from playwright.sync_api import sync_playwright

def main():
    print("🚀 Starting FMP Scraper...")
    collected_data = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
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
        page.goto("https://fmp.live/", wait_until="domcontentloaded")
        time.sleep(3) 
        
        # Cache ရှင်းဖို့ တစ်ခေါက် Reload လုပ်မယ်
        page.reload(wait_until="domcontentloaded")
        time.sleep(5) 
        
        browser.close()

    # Data ကို Frontend Format ပြောင်းခြင်း
    frontend_matches = {}
    
    # ၁။ liveList (m3u8 Links)
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

    # ၂။ competitionFilterList
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

    # ရလာတဲ့ Data ကို fmp_data.json အဖြစ် သိမ်းခြင်း
    with open('fmp_data.json', 'w', encoding='utf-8') as f:
        json.dump(list(frontend_matches.values()), f, indent=2, ensure_ascii=False)
    
    print("✅ Scraping finished. Data saved to fmp_data.json")

if __name__ == "__main__":
    main()
