
import os
import time
import requests

# 建立儲存 HTML 的資料夾（如果不存在的話）
output_dir = "./reports"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 目前網頁上所有有效的成績報告 ID
report_ids = [
84,85,86,87,31,32,33,34,88,89,90,35,36,37,91,92,93,38,39,40,94,95,96,41,42,43,
119,120,121,122,14,15,123,124,125,126,16,17,59,60,61,18,19,62,63,64,97,98,99,100,44,
45,101,102,103,46,47,65,66,67,48,49,
50,72,73,74,27,28,75,76,112,113,114,51,52,135,136,137,53,54,
127,128,129,130,20,21,22,77,
78,79, ]
base_url = "https://dragonboat.utk.com.tw/public/Report_Score_New.aspx"

# 模擬瀏覽器的 Header，讓馬鈴薯伺服器以為是正常人類在瀏覽
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print("開始溫和地下載成績報告，每次請求間隔 4 秒...")

for report_id in report_ids:
    file_path = os.path.getsize = f"{output_dir}/{report_id}.html"
    
    # 組合完整的請求網址
    url = f"{base_url}?id={report_id}"
    print(f"正在發送請求: id {report_id} -> {file_path} ...")
    
    try:
        # 發送 GET 請求，並加上 timeout 防止伺服器卡死沒回應
        response = requests.get(url, headers=headers, timeout=10)
        
        # 確保伺服器回傳 200 OK
        if response.status_code == 200:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"成功儲存 {report_id}.html")
        else:
            print(f"❌ 伺服器回傳錯誤代碼: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 請求失敗 (伺服器可能搞自閉了): {e}")
        
    # 嚴格執行 4 秒 Delay，愛護馬鈴薯
    print("等待 4 秒中...")
    time.sleep(4)

print("\n所有現有的成績報告下載任務已結束！檔案皆儲存在 ./reports 資料夾中。")