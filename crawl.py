import re
import os
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote

# 定义请求头，模拟浏览器访问
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 创建保存结果的目录
os.makedirs('wechat_articles', exist_ok=True)

# 解析文章URL的正则表达式
url_pattern = re.compile(r'http://mp\.weixin\.qq\.com/s\?[^"\']+')
# 提取文章标题的正则表达式
title_pattern = re.compile(r'var msg_title = "([^"]+)"')
# 提取发布时间的正则表达式
date_pattern = re.compile(r'var ct = "(\d+)"')
# 提取文章内容的正则表达式
content_pattern = re.compile(r'var content = "([^"]+)"')

def extract_article_info(html):
    """从HTML中提取文章信息"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # 提取标题
    title_match = title_pattern.search(html)
    title = title_match.group(1) if title_match else "未知标题"
    
    # 提取发布时间
    date_match = date_pattern.search(html)
    publish_time = date_match.group(1) if date_match else "未知时间"
    
    # 提取文章内容
    article_content = soup.find(id="js_content")
    if article_content:
        # 清理内容中的样式和属性
        for tag in article_content.find_all(True):
            tag.attrs = {}
        content_text = article_content.get_text().strip()
    else:
        content_text = "无法提取内容"
    
    return {
        "title": title,
        "publish_time": publish_time,
        "content": content_text  # 保存完整内容
    }

def crawl_and_save_articles(articles_info, max_articles=10):
    """爬取文章内容并保存"""
    summary_file = os.path.join('wechat_articles', 'summary.md')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# 微信公众号文章摘要\n\n")
    
    # 创建JSON数据结构
    json_data = {
        "articles": []
    }
    
    count = 0
    for article in articles_info:
        if count >= max_articles:
            break
            
        try:
            print(f"正在爬取: {article['title']}")
            response = requests.get(article['url'], headers=headers, timeout=10)
            if response.status_code == 200:
                # 解析文章内容
                article_info = extract_article_info(response.text)
                
                # 保存文章内容到单独的文件
                safe_title = re.sub(r'[\\/*?:"<>|]', '_', article['title'])
                article_file = os.path.join('wechat_articles', f"{safe_title}.md")
                with open(article_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {article['title']}\n\n")
                    f.write(f"发布日期: {article['publish_date']}\n\n")
                    f.write(f"原文链接: {article['url']}\n\n")
                    f.write("## 文章内容\n\n")
                    f.write(article_info['content'][:500] + "..." if len(article_info['content']) > 500 else article_info['content'])
                
                # 更新摘要文件
                with open(summary_file, 'a', encoding='utf-8') as f:
                    f.write(f"## {article['title']}\n\n")
                    f.write(f"- 发布日期: {article['publish_date']}\n")
                    f.write(f"- [阅读全文]({os.path.basename(article_file)})\n\n")
                    f.write(f"{article_info['content'][:200]}...\n\n")
                    f.write("---\n\n")
                
                # 添加文章数据到JSON结构
                json_data["articles"].append({
                    "id": article['id'],
                    "title": article['title'],
                    "publish_date": article['publish_date'],
                    "url": article['url'],
                    "content": article_info['content'],
                    "raw_publish_time": article_info['publish_time']
                })
                
                count += 1
                # 间隔一下，避免请求过于频繁
                time.sleep(2)
            else:
                print(f"爬取失败: {article['title']}, 状态码: {response.status_code}")
        except Exception as e:
            print(f"处理文章时出错: {article['title']}, 错误: {str(e)}")
    
    # 将JSON数据保存到文件
    json_file_path = os.path.join('wechat_articles', 'articles_data.json')
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=2)
    
    print(f"成功爬取了 {count} 篇文章，结果保存在 wechat_articles 目录")
    print(f"JSON数据已保存到 {json_file_path}")

def parse_and_extract():
    """解析文件并提取文章信息"""
    with open("D:\\twx\\courses\\AIPrinciple\\article.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    articles_info = []
    
    for line in lines:
        # 跳过注释行和空行
        if not line.strip() or line.strip().startswith("//"):
            continue
        
        # 使用制表符(\t)正确分割字段
        parts = line.strip().split('\t')
        
        # 确保至少有4个字段 (id, title, date, url)
        if len(parts) < 4:
            print(f"警告: 行格式不正确: {line[:50]}...")
            continue
        
        article_id = parts[0]
        title = parts[1]
        publish_date = parts[2]
        url = parts[3]
        
        articles_info.append({
            "id": article_id,
            "title": title,
            "publish_date": publish_date,
            "url": url,
        })
    
    return articles_info

if __name__ == "__main__":
    articles_info = parse_and_extract()
    print(f"从文件中解析出 {len(articles_info)} 篇文章")
    crawl_and_save_articles(articles_info)
