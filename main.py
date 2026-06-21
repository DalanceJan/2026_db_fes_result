import os
import glob
from bs4 import BeautifulSoup
import re

def parse_report_to_metadata_old(html_content):
    """
    解析單一成績報告 HTML，提取出結構化的 Meta Data
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. 抓取上方賽事基本資訊
    # 網頁結構通常是用文字直接寫在特定標籤或強烈特徵的文字後
    page_text = soup.get_text()
    
    # 預設解析邏輯（根據畫面的文字特徵抓取）
    # 實務上也可以找特定的 <h2> 或 <span>，以下採用文字切分做示範
    try:
        match_no = page_text.split("場次：")[1].split()[0].strip()
        match_time = page_text.split("時間：")[1].split("項目：")[0].strip()
        # match_item = page_text.split("項目：")[1].split("\n")[0].strip()
        match_item = page_text.split("項目：")[1].split("水道")[0]
        print(match_item)
    except IndexError:
        # 容錯機制，若切分失敗則給預設值
        match_no, match_time, match_item = "未知", "未知", "未知"

    # 2. 抓取下方表格成績
    teams_data = []
    table = soup.find('table')
    if table:
        rows = table.find_all('tr')[1:] # 跳過表頭
        for row in rows:
            cols = [cfg.text.strip() for cfg in row.find_all(['td', 'th'])]
            if len(cols) >= 4:
                # 欄位順序：水道 | 單位 | 比賽成績 | 名次 | (備註)
                try:
                    rank = int(cols[3])
                except ValueError:
                    rank = 999 # 若未完賽或無名次給予大數值排序
                
                teams_data.append({
                    "lane": cols[0],
                    "team_name": cols[1],
                    "result_time": cols[2],
                    "rank": rank,
                    "note": cols[4] if len(cols) > 4 else ""
                })
    
    # 依名次排序 (1排到前)
    teams_data.sort(key=lambda x: x['rank'])

    # 回傳結構化 Meta Data
    return {
        "match_no": match_no,
        "time": match_time,
        "item": match_item,
        "results": teams_data
    }

def parse_report_to_metadata(html_content):
    """
    解析單一成績報告 HTML，提取出結構化的 Meta Data（更具彈性的欄位對應）
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    page_text = soup.get_text(separator="\n")

    # 先用正規表達式嘗試抓取場次、時間、項目（容錯並移除多餘字串）
    match_no = match_time = match_item = "未知"
    m = re.search(r'場次[:：]\s*([\dA-Za-z\-]+)', page_text)
    if m:
        match_no = m.group(1).strip()
    m = re.search(r'時間[:：]\s*([^\n項：]+)', page_text)
    if m:
        match_time = m.group(1).strip()
    m = re.search(r'項目[:：]\s*([^\n]+)', page_text)
    if m:
        match_item = m.group(1).strip()
        # 若項目文字包含「水道」或其他後續描述，去掉之
        match_item = re.sub(r'\s*水道.*$', '', match_item).strip()

    # 解析表格：嘗試找出有「水道 / 名次 / 單位 / 成績」字樣的表格並對應欄位
    teams_data = []
    tables = soup.find_all('table')
    table = None
    for t in tables:
        header_text = " ".join([c.get_text(strip=True) for c in t.find_all(['th', 'td'])[:10]])
        if any(k in header_text for k in ("水道", "名次", "成績", "單位", "隊伍")):
            table = t
            break
    if table is None and tables:
        table = tables[0]

    if table:
        # 嘗試找出表頭列（第一個 tr 含 th 或明顯的標題）
        header_row = None
        for tr in table.find_all('tr'):
            cells = [c.get_text(strip=True) for c in tr.find_all(['th', 'td'])]
            if any(h for h in cells if any(k in h for k in ("水道", "名次", "成績", "單位", "隊伍"))):
                header_row = cells
                break
        # 若沒找到明確表頭，就用第一列作為表頭嘗試
        if header_row is None:
            first_tr = table.find('tr')
            header_row = [c.get_text(strip=True) for c in first_tr.find_all(['th', 'td'])] if first_tr else []

        # 建立欄位索引對應函式
        def find_index(possible):
            for i, h in enumerate(header_row):
                if any(p in h for p in possible):
                    return i
            return None

        lane_idx = find_index(["水道", "道", "lane"])
        team_idx = find_index(["單位", "隊伍", "隊名", "隊"])
        result_idx = find_index(["成績", "時間", "Result", "成績/時間"])
        rank_idx = find_index(["名次", "排名", "名次/排名"])

        # 若找不到就回退到常見的位置假設：水道0、隊伍1、成績2、名次3
        if lane_idx is None: lane_idx = 0
        if team_idx is None: team_idx = 1
        if result_idx is None: result_idx = 2
        if rank_idx is None: rank_idx = 3

        # 真正解析資料列（跳過表頭行）
        rows = table.find_all('tr')
        # 如果 header_row 是第一個 tr，從第二列開始；否則從所有 tr 中排除 header_row 那一列
        start_index = 1 if rows and [c.get_text(strip=True) for c in rows[0].find_all(['th','td'])] == header_row else 0
        for tr in rows[start_index:]:
            cols = [c.get_text(strip=True) for c in tr.find_all(['td', 'th'])]
            if len(cols) == 0:
                continue
            # 防止索引超出範圍
            def get_col(idx):
                return cols[idx].strip() if idx is not None and idx < len(cols) else ""

            lane = get_col(lane_idx)
            team_name = get_col(team_idx)
            result_time = get_col(result_idx)
            rank_text = get_col(rank_idx)

            # 解析名次為整數，若無法解析設定為 999（代表未完賽或無名次）
            rank = 999
            if rank_text:
                mnum = re.search(r'(\d+)', rank_text)
                if mnum:
                    try:
                        rank = int(mnum.group(1))
                    except ValueError:
                        rank = 999
                else:
                    # 若文字包含 常見詞例如 冠軍、亞軍，做簡單映射（選擇性）
                    txt = rank_text.replace(" ", "")
                    if "冠軍" in txt:
                        rank = 1
                    elif "亞軍" in txt:
                        rank = 2
                    elif "季軍" in txt:
                        rank = 3
                    else:
                        rank = 999

            note = ""
            # 如果該列有多於 4 個欄位，把多餘欄位拼成備註
            if len(cols) > max(lane_idx, team_idx, result_idx, rank_idx) + 1:
                extras = [c for i, c in enumerate(cols) if i not in (lane_idx, team_idx, result_idx, rank_idx)]
                note = " | ".join([e for e in extras if e])

            teams_data.append({
                "lane": lane,
                "team_name": team_name,
                "result_time": result_time,
                "rank": rank,
                "note": note
            })

    # 依名次排序 (1排到前)，未解析出的名次（999）會排到後面
    teams_data.sort(key=lambda x: x['rank'])
    return {
        "match_no": match_no,
        "time": match_time,
        "item": match_item,
        "results": teams_data
    }
def generate_combined_html(all_matches_metadata, max_teams=4):
    """
    將所有場次的 Meta Data 重新排列，並合併輸出成一個 HTML 表格
    """
    html = []
    html.append("<table border='1' style='border-collapse: collapse; text-align: center;'>")
    
    # 建立動態表頭
    header = ["場次", "時間", "項目"]
    for i in range(1, max_teams + 1):
        header.extend([f"名次{i}", f"名次{i}隊伍", f"時間", f"名次{i}水道"])
    
    html.append("  <tr>")
    for h in header:
        html.append(f"    <th style='padding: 8px; background-color: #f2f2f2;'>{h}</th>")
    html.append("  </tr>")
    
    # 填入每場賽事資料
    for match in all_matches_metadata:
        html.append("  <tr>")
        html.append(f"    <td>{match['match_no']}</td>")
        html.append(f"    <td>{match['time']}</td>")
        html.append(f"    <td>{match['item']}</td>")
        
        # 填入各名次隊伍
        for i in range(max_teams):
            if i < len(match['results']):
                t = match['results'][i]
                rank_str = f"第{t['rank']}名" if t['rank'] != 999 else "未完賽"
                html.extend([
                    f"    <td>{rank_str}</td>",
                    f"    <td>{t['team_name']}</td>",
                    f"    <td>{t['result_time']}</td>",
                    f"    <td>{t['lane']}</td>"
                ])
            else:
                # 若該場次隊伍不足 max_teams，補空欄
                html.extend(["    <td>-</td>", "    <td>-</td>", "    <td>-</td>", "    <td>-</td>"])
        
        html.append("  </tr>")
        
    html.append("</table>")
    return "\n".join(html)

# === 實際執行示範 ===
if __name__ == "__main__":
    # 假設你把下載下來的 html 都放在當前目錄的 reports 資料夾中
    html_files = glob.glob("reports\\*.html")

    all_metadata = []
    
    # 迭代解析所有檔案
    for file_path in html_files:
        with open(file_path, "r", encoding="utf-8") as f:
            meta = parse_report_to_metadata(f.read())
            all_metadata.append(meta)
            
    # 依場次數字排序（選用）
    try:
        all_metadata.sort(key=lambda x: int(x['match_no']))
    except ValueError:
        pass

    # 這裡就是你要保留的完整結構化 Meta Data 陣列
    # print(all_metadata) 
    
    # 轉換並輸出合併後的全新 HTML
    # 目前龍舟賽一般是 4 個水道，如果有 6 水道的場次可以將 max_teams 改為 6
    combined_html_output = generate_combined_html(all_metadata, max_teams=4)
    
    if os.path.exists("result") == False:
        os.makedirs("result")
    with open("result\\combined_report.html", "w", encoding="utf-8") as out_f:
        out_f.write(combined_html_output)

    print(f"成功解析 {len(all_metadata)} 份報告，並已合併輸出至 result\\combined_report.html")