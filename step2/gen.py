# 获取./wechat_daily_articles/ 下面的所有目录， 其中格式都是 2025-08-27 这样的日期， 排序获取最新的， 将该目录名（如2025-08-27）保存为dir
# 获取该目录下面的所有文件， 保存在files

import os
from datetime import datetime
import json
from pathlib import Path

from step2.convent import convent
from step2.pdf import toPdf


def getFilesArray() -> tuple[list, str]:
    # 获取./wechat_daily_articles/ 下面的所有目录
    base_path = "../wechat_daily_articles/"
    # 获取所有目录并筛选出符合日期格式的目录
    date_dirs = []
    if os.path.exists(base_path):
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                try:
                    # 尝试解析目录名为日期格式
                    datetime.strptime(item, "%Y-%m-%d")
                    date_dirs.append(item)
                except ValueError:
                    # 如果不是日期格式，跳过
                    continue

    # 按日期排序，获取最新的目录
    if date_dirs:
        date_dirs.sort(reverse=True)  # 降序排列，最新的在前面
        dir = date_dirs[0]  # 获取最新的目录名

        # 获取该目录下面的所有文件
        latest_dir_path = os.path.join(base_path, dir)
        files = []

        for item in os.listdir(latest_dir_path):
            item_path = os.path.join(latest_dir_path, item)
            if os.path.isfile(item_path):
                files.append(item_path)

        print(f"最新目录: {dir}")
        print(f"文件列表: {files}")
        return files, dir
    else:
        dir = None
        files = []
        print("未找到符合日期格式的目录")
        return files, dir





def write_to_one_file(files: list, dir: str):
    sep = '------'
    items = []
    for file in files:
        with open(file, encoding='utf8') as f:
            data = json.load(f)

            for item in data['articles']:
                items.append(json.dumps(convent(item), ensure_ascii=False))

    output = ('\n' + sep + '\n').join(items)

    output_path = Path(f'../out/{dir}/output.txt')
    # 确保父目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf8') as f:
        f.write(output)
    return output_path


def genTxt(files: list, dir: str) -> list[str]:
    return write_to_one_file(files, dir)


def genPdf(files: list, dir: str) -> None:
    toPdf(files, dir)


files, dir = getFilesArray()
genTxt(files, dir)
genPdf(files, dir)
