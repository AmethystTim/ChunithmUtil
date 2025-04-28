import requests, re, os, json
from bs4 import BeautifulSoup

base_url = "https://sdvx.in/chunithm/sort/$$.htm"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}
json_path1 = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'chartId2Name.json')
json_path2 = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'chartId2Gen.json')
chartid2name = {}   # 存放id和歌曲名的映射表
chartid2gen = {}    # 存放id和版本号的映射表
level_list = [
    '11',
    '11+',
    '12',
    '12+',
    '13',
    '13+',
    '14',
    '14+',
    '15',
    '15+',
]

def mapping():
    for level in level_list:
        url = base_url.replace('$$', level)
        print('正在爬取', level, '级曲目...')
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response.encoding = 'utf-8'
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            tds = soup.find_all('td', class_='tbg')
            for td in tds:
                strings = str(td).split('\n')
                for string in strings:
                    if not string.startswith('<script'):
                        continue
                    pattern1 = r'<script\s+src="/chunithm/(\d+)/js/(\d{5})sort\.js">' # id
                    pattern2 = r'<!--(.+)-->'   # 歌曲名
                    m1 = re.search(pattern1, string)
                    m2 = re.search(pattern2, string)
                    if m1 and m2:
                        chartid2name[m1.group(2)] = m2.group(1).strip()
                        chartid2gen[m1.group(2)] = m1.group(1)
                        
    with open(json_path1, 'w', encoding='utf-8') as f:
        write_str = json.dumps(chartid2name, ensure_ascii=False, indent=4)
        f.write(write_str)
        print('写入chartId2Name.json文件成功')
    with open(json_path2, 'w', encoding='utf-8') as f:
        write_str = json.dumps(chartid2gen, ensure_ascii=False, indent=4)
        f.write(write_str)
        print('写入chartId2Gen.json文件成功')

if __name__ == '__main__':
    mapping()