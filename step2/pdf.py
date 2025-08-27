import re
from pathlib import Path

from playwright.sync_api import sync_playwright
import time
import json

from step2.convent import convent

global_dir = ''

def js_webpage_to_pdf(url, output_path, wait_time=5):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 设置为非无头模式
        page = browser.new_page()
        page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        try:
            page.goto(url, wait_until='domcontentloaded', timeout=6000)
            page.wait_for_timeout(3000)  # 等待3秒
            # 其余代码...
        except Exception as e:
            print(f"访问失败: {e}")

        # 等待特定元素加载完成
        try:
            page.wait_for_selector('#js_content', timeout=3000)  # 等待 id 为 js_content 的 div
        except:
            pass

        try:
            page.wait_for_load_state('networkidle', timeout=3000)  # 等待网络空闲
        except:
            print("继续执行...")

        page.evaluate("""
            async () => {
                const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

                // 获取页面总高度
                let totalHeight = document.body.scrollHeight;
                let currentHeight = 0;
                let step = 500; // 每次滚动500px

                while (currentHeight < totalHeight) {
                    window.scrollBy(0, step);
                    currentHeight += step;
                    await delay(200); // 每次滚动后等待200ms

                    // 重新获取页面高度，因为可能有新内容加载
                    totalHeight = document.body.scrollHeight;
                }

                // 确保滚动到最底部
                window.scrollTo(0, document.body.scrollHeight);
            }
        """)
        # 额外等待时间确保 JS 执行完成
        page.wait_for_timeout(wait_time * 1000)

        # 生成 PDF
        page.pdf(
            path=output_path,
            format='A4',
            print_background=True,
            margin={'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'}
        )

        browser.close()


i = 0


def process(fname):
    global i
    global global_dir
    f = open(fname, encoding='utf8')
    j = json.load(f)
    f.close()
    art = j['articles']

    for a in art:
        a = convent(a)
        content = a['content']
        content = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', content)
        if len(content) >= 200:
            continue
        output_path = Path(f'../out/{global_dir}/pdf/{a["id"]}.pdf')
        # 确保父目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # 如果文件存在， continue
        name = output_path
        js_webpage_to_pdf(a['url'], name)
        url = a['url']
        print(f'{i} down: {url}')
        i += 1
        a['pdf'] = name
        time.sleep(1)
    print(art)


def toPdf(files, dir):
    global global_dir
    global_dir = dir
    for fn in files:
        process(fn)
