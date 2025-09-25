import os
import sys
import json
import requests
import based58
from typing import Dict, Any

# 增加全局常量来管理超时时间和文件名，便于维护
REQUEST_TIMEOUT = 10
CONFIG_FILE = "config.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


def fetch_and_parse_subscription(url: str) -> Dict[str, Any] | None:
    """
    从URL获取内容，尝试Base58解码，然后解析JSON。
    如果网络请求或解析失败，则返回 None。
    """
    print(f"正在尝试获取订阅链接内容: {url}")
    try:
        # 使用统一的请求配置
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()

        content_str = response.text

        # 尝试 Base58 解码
        try:
            content_bytes = content_str.encode('ascii')
            decoded_bytes = based58.b58decode(content_bytes)
            # 解码后的字节串可能需要转换为 UTF-8 字符串
            content_to_parse = decoded_bytes.decode('utf-8')
            print("内容已成功进行 Base58 解码。")
        except (ValueError, UnicodeDecodeError):
            # 解码失败或内容不是有效的 UTF-8，则使用原始内容
            print("警告：内容不是有效的 Base58 或 UTF-8 格式，将尝试直接解析原始内容。", file=sys.stderr)
            content_to_parse = content_str

        # 解析 JSON 数据
        return json.loads(content_to_parse)

    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"发生未知错误: {e}", file=sys.stderr)
        return None


def validate_video_source(url: str) -> bool:
    """
    通过发送HEAD请求检查视频源URL的有效性。
    """
    print(f"正在检查URL: {url}")
    try:
        # 使用统一的请求配置
        response = requests.head(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})

        # 优化：response.ok 属性检查所有 2xx 状态码
        if response.ok:
            print(f"✅ URL有效。状态码：{response.status_code}")
            return True
        else:
            print(f"❌ URL无效。状态码：{response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False


def main():
    """主函数，负责处理多个URL并追加到config.json。"""
    # 使用列表推导式或元组来存储订阅链接，更简洁
    url_list = [
        r'https://gist.githubusercontent.com/senshinya/5a5cb900dfa888fd61d767530f00fc48/raw/gistfile1.txt',
        r'https://raw.githubusercontent.com/hafrey1/LunaTV-config/main/LunaTV-config.txt'
    ]

    # 1. 读取现有的 config.json 文件
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = {"api_site": {}}
        print(f"{CONFIG_FILE} 文件未找到，将创建新文件。")
    except json.JSONDecodeError as e:
        print(f"错误：无法解析 {CONFIG_FILE} 文件: {e}", file=sys.stderr)
        sys.exit(1)

    # 确保 api_site 字段存在且是字典类型
    config_data.setdefault("api_site", {})
    existing_sources = config_data["api_site"]

    # 2. 从订阅链接获取新的频道数据并合并
    for url in url_list:
        new_data = fetch_and_parse_subscription(url)
        if new_data and "api_site" in new_data:
            # 使用 update() 方法合并字典，更简洁高效
            existing_sources.update(new_data["api_site"])

    # 3. 源的有效性检查与删除
    # 核心优化点：在迭代字典的副本时修改原字典，避免 RuntimeError
    sources_to_check = list(existing_sources.keys())
    for key in sources_to_check:
        # 在删除前检查键是否存在，以防并发修改或上游数据源有重复键
        if key in existing_sources:
            is_valid = validate_video_source(existing_sources[key]['api'])
            if not is_valid:
                print(
                    f"警告：源 {existing_sources[key]['name']} ({existing_sources[key]['api']}) 可能无效，进行删除操作。")
                del existing_sources[key]

    # 4. 将更新后的JSON结构写入 config.json
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        print(f"{CONFIG_FILE} 文件已成功更新。")
    except Exception as e:
        print(f"写入文件时发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()