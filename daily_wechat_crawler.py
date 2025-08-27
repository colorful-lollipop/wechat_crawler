import requests
import json
import time
import random
import os
import ssl
import urllib3
import logging
import datetime
from pathlib import Path
from notify import send_email_notification, create_notification_for_new_articles
from get_cookie import extract_article_content_from_html, crawl_headers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wechat_crawler.log'),
        logging.StreamHandler()
    ]
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_FILE = 'wechat_crawler_config.json'
DATA_DIR = Path('wechat_daily_articles')
DATA_DIR.mkdir(exist_ok=True)

# 默认配置
DEFAULT_CONFIG = {
    'token': '561895093',
    'last_update': {},  # 格式: {'公众号名称': {'last_time': 时间戳, 'last_aid': '最后一篇文章ID'}}
    'max_articles_per_account': 20,
    'accounts': ['学生清华', '清华紫荆之声']
}

# 请求头
header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    'Connection': 'close',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
}


def load_config():
    """加载配置，如不存在则创建默认配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def update_last_crawl_info(account, latest_aid=None, latest_time=None):
    """更新最后一次抓取信息"""
    config = load_config()
    if account not in config['last_update']:
        config['last_update'][account] = {}

    if latest_aid:
        config['last_update'][account]['last_aid'] = latest_aid
    if latest_time:
        config['last_update'][account]['last_time'] = latest_time

    save_config(config)


def crawl_articles_daily():
    """每日定时抓取公众号文章"""
    config = load_config()
    token = config['token']
    accounts = config['accounts']
    max_articles_per_account = config.get('max_articles_per_account', 20)
    delay_between_articles = config.get('delay_between_articles', [2, 5])
    delay_between_accounts = config.get('delay_between_accounts', [15, 30])
    days_back = config.get('crawl_days_back', 7)
    time_threshold = int(time.time()) - (days_back * 24 * 60 * 60)

    # 确保cookie是最新的
    cookie_input = input("请输入最新的cookie，直接回车使用配置文件中的cookie: ")
    if cookie_input.strip():
        config['cookie'] = cookie_input.strip()
        save_config(config)
    elif 'cookie' not in config:
        config['cookie'] = input("配置中没有cookie，请输入: ")
        save_config(config)

    cookie = {'Cookie': config['cookie']}

    # 创建今日的文件夹
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    today_dir = DATA_DIR / today_str
    today_dir.mkdir(exist_ok=True)

    new_articles_count = 0
    for account in accounts:
        logging.info(f"开始检查公众号: {account}")

        try:
            # 1. 搜索公众号
            search_url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz?'
            query_id = {
                'action': 'search_biz',
                'token': token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': '1',
                'random': random.random(),
                'query': account,
                'begin': 0,
                'count': '5'
            }

            search_response = requests.get(search_url, cookies=cookie, headers=header, params=query_id, verify=False)
            lists = search_response.json().get('list', [])

            if not lists:
                logging.warning(f"未找到公众号: {account}")
                continue

            # 2. 获取公众号fakeid
            fakeid = lists[0].get('fakeid')
            logging.info(f"公众号 [{account}] 的fakeid: {fakeid}")

            # 3. 获取上次抓取信息
            last_aid = config['last_update'].get(account, {}).get('last_aid', '')
            articles_got = 0

            # 4. 开始抓取文章
            account_file = today_dir / f"{account.replace(' ', '_')}.json"
            account_articles = {
                "account": account,
                "fakeid": fakeid,
                "crawl_time": datetime.datetime.now().isoformat(),
                "articles": []
            }

            is_new_article_found = False
            for k in range(0, max_articles_per_account, 5):
                logging.info(f"正在获取第 {k} 到 {k + 4} 条文章")
                url = f'https://mp.weixin.qq.com/cgi-bin/appmsg?token={token}&lang=zh_CN&f=json&ajax=1&random={random.random()}&action=list_ex&begin={k}&count=5&query=&fakeid={fakeid}&type=9'

                r = requests.get(url=url, headers=header, cookies=cookie, verify=False).text
                response_data = json.loads(r)
                app_msg_list = response_data.get("app_msg_list", [])

                if not app_msg_list:
                    logging.info(f"没有更多文章或请求受限")
                    break

                for article in app_msg_list:
                    aid = article.get('aid', '')

                    if articles_got >= max_articles_per_account:
                        logging.info(f"已达到最大抓取数量 {max_articles_per_account}，停止抓取")
                        is_new_article_found = True
                        break

                    # 如果遇到已经抓取过的文章ID，停止抓取（可选）
                    # if aid == last_aid:
                    #     logging.info(f"已到达上次抓取的文章，停止抓取")
                    #     is_new_article_found = True
                    #     break

                    title = article.get("title", "无标题")
                    link = article.get("link", "")
                    create_time = article.get("create_time", 0)
                    create_time_str = time.strftime("%Y-%m-%d %H:%M:%S",
                                                    time.localtime(create_time))

                    # （可选）
                    if articles_got >= max_articles_per_account:
                        logging.info(f"已达到最大抓取数量 {max_articles_per_account}，停止抓取")
                        is_new_article_found = True
                        break

                    # （可选）
                    if create_time < time_threshold:
                        logging.info(f"文章时间超出设定范围（{days_back}天前），停止抓取")
                        is_new_article_found = True
                        break

                    logging.info(f"发现文章: {title}")

                    full_content = "获取内容失败"
                    if link:
                        try:
                            logging.info(f"正在获取文章全文: {link}")
                            content_response = requests.get(link, headers=crawl_headers, timeout=15, verify=False)
                            if content_response.status_code == 200:
                                full_content = extract_article_content_from_html(content_response.text)
                                logging.info(f"成功获取文章全文，长度: {len(full_content)}")
                            else:
                                logging.warning(f"获取文章全文失败，状态码: {content_response.status_code}")
                            # 在每次请求文章详情页后也加入短暂延时
                            time.sleep(random.uniform(1, 3))
                        except Exception as content_e:
                            logging.error(f"获取文章全文时出错: {content_e}")

                    # 添加到文章列表
                    account_articles["articles"].append({
                        "aid": aid,
                        "title": title,
                        "link": link,
                        "create_time": create_time,
                        "create_time_str": create_time_str,
                        "digest": article.get("digest", ""),
                        "cover": article.get("cover", ""),
                        "content": full_content
                    })

                    articles_got += 1
                    new_articles_count += 1

                if is_new_article_found:
                    break

                # 随机延时，避免请求过于频繁
                delay = random.uniform(2, 5)
                logging.info(f"等待 {delay:.2f} 秒...")
                time.sleep(delay)

            # 保存文章信息
            if account_articles["articles"]:
                # 更新最后抓取的文章ID
                latest_article = account_articles["articles"][0]
                update_last_crawl_info(
                    account,
                    latest_aid=latest_article["aid"],
                    latest_time=int(time.time())
                )

                # 保存到JSON
                with open(account_file, 'w', encoding='utf-8') as f:
                    json.dump(account_articles, f, ensure_ascii=False, indent=2)

                logging.info(f"已保存 {len(account_articles['articles'])} 篇来自 {account} 的新文章")
            else:
                logging.info(f"没有发现 {account} 的新文章")

        except Exception as e:
            logging.error(f"处理公众号 {account} 时出错: {str(e)}", exc_info=True)

        # 不同公众号之间休息一下
        if account != accounts[-1]:
            sleep_time = random.randint(10, 20)
            logging.info(f"休息 {sleep_time} 秒后继续...")
            time.sleep(sleep_time)

    logging.info(f"今日抓取完成，共发现 {new_articles_count} 篇新文章")

    if new_articles_count > 0 and os.path.exists('email_config.json'):
        with open('email_config.json', 'r', encoding='utf-8') as f:
            email_config = json.load(f)

        to_email = email_config.get('to_email')
        if to_email:
            # 为每个有新文章的公众号发送通知
            for account in accounts:
                account_file = today_dir / f"{account.replace(' ', '_')}.json"
                if os.path.exists(account_file):
                    with open(account_file, 'r', encoding='utf-8') as f:
                        account_data = json.load(f)

                    if account_data['articles']:
                        subject, body = create_notification_for_new_articles(account_data)
                        send_email_notification(subject, body, to_email)
                        logging.info(f"已发送 {account} 的新文章通知")
    return new_articles_count


if __name__ == "__main__":
    logging.info("开始每日公众号文章抓取任务")
    try:
        new_count = crawl_articles_daily()
        if new_count > 0:
            logging.info(f"成功抓取了 {new_count} 篇新文章")
        else:
            logging.info("今天没有新文章")
    except Exception as e:
        logging.error(f"抓取过程中发生错误: {str(e)}", exc_info=True)
    logging.info("抓取任务结束")
