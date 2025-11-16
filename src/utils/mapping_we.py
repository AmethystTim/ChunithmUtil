import requests, re, os, json
from bs4 import BeautifulSoup

url = "https://sdvx.in/chunithm/end.htm"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}

from playwright.sync_api import sync_playwright

def fetch_rendered_html(url):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        # 等待页面加载和脚本执行
        page.wait_for_load_state("networkidle")
        html = page.content()
        browser.close()
        return html

def mapping_we():
    html = fetch_rendered_html(url)
    
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(r"^/chunithm/end/\d+end\d*\.htm$")
    links = []
    print("********************")
    for a in soup.find_all("a", href=pattern):
        # <a href="/chunithm/end/01041end.htm"><img src="/chunithm/chfiles/chlv/star_shou2.png"/></a>
        id_index = a['href']
        endpoint = a.find("img")["src"]
        
        m = re.search(r'/([^/]+)\.htm$', id_index)
        id_index = m.group(1) if m else None
        
        m = re.search(r'/([^/]+)\.png$', endpoint)
        endpoint = m.group(1) if m else None
        
        links.append({id_index: endpoint})
    
    print("匹配到的链接：")
    for l in links:
        print(l)
    
    # 转为dict
    result = {k: v for d in links for k, v in d.items()}

    # 写入映射表
    file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', "chartId2Diff_we.json")
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    mapping_we()