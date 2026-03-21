import requests
import json
import socket
import os
import time

# 1. Trả về đúng 1 LIST các base_url y hệt Kotlin
def get_dynamic_base_urls():
    default_url = "https://de1.api.radio-browser.info/"
    active_servers = []
    
    try:
        # Quét DNS lấy IP
        ips = socket.gethostbyname_ex('all.api.radio-browser.info')[2]
        for ip in ips:
            try:
                host = socket.gethostbyaddr(ip)[0]
                # Check nếu hostname có chứa chữ cái và không có ':'
                if any(char.isalpha() for char in host) and ':' not in host:
                    active_servers.append(f"https://{host}/")
            except:
                continue
    except Exception as e:
        print(f"Lỗi phân giải DNS: {e}")
    
    # Cộng thêm link default ở cuối list (Y hệt activeServers + listOf(DEFAULT_URL))
    active_servers.append(default_url)
    
    print(f"🔍 Danh sách Server thu được: {active_servers}")
    return active_servers

# 2. Vòng lặp "Thử vận may" qua list URL
def fetch_and_process_stations(list_base_url, country_code=""):
    params = {
        "limit": 200 if country_code else 300,
        "hidebroken": "true",
        "order": "votes",
        "reverse": "true",
    }
    if country_code:
        params["countrycode"] = country_code

    headers = {'User-Agent': 'AuraClockApp-GitHubAction/1.0'}
    
    # Lặp qua từng server trong danh sách
    for base_url in list_base_url:
        search_url = f"{base_url}json/stations/search"
        try:
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                stations = response.json()
                mapped_list = []
                excluded_tags = ["adult", "sex", "nsfw", "porn", "erotica", "violence", "politics"]
                
                for dto in stations:
                    tags = dto.get("tags", "").lower()
                    if any(bad_tag in tags for bad_tag in excluded_tags):
                        continue

                    stream_url = dto.get("url_resolved", "")
                    if stream_url.lower().startswith("https://"):
                        mapped_list.append({
                            "stationuuid": dto.get("stationuuid"),
                            "name": dto.get("name", "").strip(),
                            "url_resolved": stream_url,
                            "favicon": dto.get("favicon", "")
                        })
                        
                    if len(mapped_list) >= 100:
                        break
                
                print(f"✅ Lấy data THÀNH CÔNG từ server: {base_url}")
                # Ăn tiền là ở đây: return luôn để thoát vòng lặp For
                return mapped_list
            else:
                print(f"⚠️ Server {base_url} trả về code {response.status_code}. Thử server tiếp theo...")
                
        except Exception as e:
            # Catch lỗi (như UnknownHostException) và tự động chạy tiếp vòng lặp
            print(f"❌ Server {base_url} lỗi: {e}. Thử server tiếp theo...")
            continue
            
    # Chốt chặn cuối cùng nếu toàn bộ DNS đều sập
    print("🚨 Toàn bộ máy chủ Radio đều không phản hồi!")
    return []

def run_fetcher():
    os.makedirs('data/radio', exist_ok=True)
    
    # Gọi hàm lấy list URL
    list_base_url = get_dynamic_base_urls()

    # Để lấy danh sách quốc gia, ta cũng thử qua các server cho chắc cốp
    valid_countries = []
    for base_url in list_base_url:
        try:
            countries_req = requests.get(f"{base_url}json/countries", headers={'User-Agent': 'AuraApp/1.0'}, timeout=10)
            if countries_req.status_code == 200:
                valid_countries = [c['iso_3166_1'].lower() for c in countries_req.json() if c.get('iso_3166_1')]
                break # Lấy được danh sách nước là thoát vòng lặp ngay
        except:
            continue
    
    print(f"🌍 Tìm thấy {len(valid_countries)} quốc gia.")

    # Lấy dữ liệu cho Từng quốc gia
    for code in valid_countries:
        stations = fetch_and_process_stations(list_base_url, code)
        
        # LOGIC CHUẨN: Trong Python, nếu mảng 'stations' rỗng [], nó sẽ tự động tính là False.
        # Nếu mảng có ít nhất 1 phần tử, nó sẽ là True.
        if stations: 
            with open(f'data/radio/{code}.json', 'w', encoding='utf-8') as f:
                json.dump(stations, f, ensure_ascii=False)
            print(f"✅ Đã cập nhật data cho {code.upper()} ({len(stations)} đài)")
        else:
            # API trả về [] hoặc bị Exception nên trả về rỗng -> Không ghi đè
            print(f"⚠️ API trả về rỗng cho {code.upper()}. GIỮ NGUYÊN FILE CŨ!")
            
        time.sleep(0.2)

    # Lấy danh sách Global Fallback
    global_stations = fetch_and_process_stations(list_base_url, "")
    
    # Tương tự cho bản Global, chỉ cần có đài là lụm
    if global_stations: 
        with open(f'data/radio/global.json', 'w', encoding='utf-8') as f:
            json.dump(global_stations, f, ensure_ascii=False)
        print(f"✅ Đã cập nhật Global Fallback ({len(global_stations)} đài)")
    else:
        print("⚠️ API trả về rỗng cho Global. GIỮ NGUYÊN FILE CŨ!")

if __name__ == "__main__":
    run_fetcher()
