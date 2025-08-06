import json
import getpass
import os

def create_email_config():
    """创建邮箱配置文件"""
    config = {}
    
    print("请设置邮件通知的邮箱信息")
    config['from_email'] = input("发送邮箱地址: ")
    config['password'] = getpass.getpass("邮箱密码或应用密码: ")
    config['smtp_server'] = input("SMTP服务器地址 (例如 smtp.gmail.com): ")
    config['smtp_port'] = int(input("SMTP端口 (通常是587): ") or "587")
    config['to_email'] = input("接收通知的邮箱地址: ")
    
    with open('email_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"邮箱配置已保存到 {os.path.abspath('email_config.json')}")

if __name__ == "__main__":
    create_email_config()