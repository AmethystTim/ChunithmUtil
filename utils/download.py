import requests
import os

url = "https://dp4p6x0xfi5o9.cloudfront.net/chunithm/data.json"
response = requests.get(url)
if response.status_code == 200:
    filename = url.split('/')[-1]
    with open(os.path.join(os.getcwd(), '../data', filename), 'wb') as file:
        file.write(response.content)
    print(f"文件已成功下载并保存为 {filename}")
else:
    print(f"下载失败，状态码：{response.status_code}")