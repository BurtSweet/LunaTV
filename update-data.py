import os
import sys
import json
import requests
import based58


def fetch_and_parse_subscription(url):
    """
    从URL获取内容，尝试Base58解码，然后进行M3U解析。
    如果网络请求或解析失败，则返回 None。
    """
    print(f"正在尝试获取订阅链接内容: {url}")
    try:
        # 增加超时和用户代理，以模拟浏览器请求并避免挂起
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        # 检查HTTP状态码，如果不是200，则抛出HTTPError异常
        response.raise_for_status()

        # 获取原始内容，类型为字符串
        content_str = response.text

        # 尝试对内容进行Base58解码
        try:
            # based58库要求输入字节串，所以先编码
            content_bytes = content_str.encode('ascii')
            decoded_bytes = based58.b58decode(content_bytes)
            # 解码后的字节串可能需要转换为UTF-8字符串
            decoded_content = decoded_bytes.decode('utf-8')
            print(f"内容已成功进行Base58解码。")
        except ValueError:
            # 如果解码失败，说明内容不是Base58编码，将使用原始内容
            print(f"警告：内容不是有效的Base58格式，将尝试直接解析原始内容。", file=sys.stderr)
            decoded_content = content_str
        except UnicodeDecodeError:
            # 如果解码后的字节串不是有效的UTF-8，也使用原始内容
            print(f"警告：Base58解码成功，但内容不是有效的UTF-8，将尝试直接解析原始内容。", file=sys.stderr)
            decoded_content = content_str
        if decoded_content is None:
            return None
        else:
            return decoded_content
    except Exception as e:
        print('get url error:', e, file=sys.stderr)


def main():
    """主函数，负责处理多个URL并追加到config.json。"""
    # 获取环境变量中的订阅链接
    url_list = [r'https://gist.githubusercontent.com/senshinya/5a5cb900dfa888fd61d767530f00fc48/raw/gistfile1.txt',
                r'https://raw.githubusercontent.com/hafrey1/LunaTV-config/main/LunaTV-config.txt']

    # 1. 读取现有的 config.json 文件
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except FileNotFoundError:
        # 如果文件不存在，则创建空的JSON结构
        config_data = {}
        print("config.json 文件未找到，将创建新文件。")
    except json.JSONDecodeError as e:
        print(f"错误：无法解析 config.json 文件: {e}", file=sys.stderr)
        sys.exit(1)

    # 确保 api_site 字段存在且是字典类型
    if "api_site" not in config_data or not isinstance(config_data["api_site"], dict):
        config_data["api_site"] = {}

    existing_sources = config_data["api_site"]

    # 2. 从订阅链接获取新的频道数据
    all_new_channels = {}
    for url in url_list:
        all_new_channels = {**all_new_channels, **json.loads(fetch_and_parse_subscription(url))}

    # 3. 将新数据追加到现有配置中
    for key in all_new_channels['api_site']:
        if key not in existing_sources:
            existing_sources[key] = all_new_channels['api_site'][key]
            print(
                f"成功追加新源: {all_new_channels['api_site'][key]['name']} ({all_new_channels['api_site'][key]['api']})")

    # 5. 将更新后的JSON结构写入 config.json
    try:
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        print("config.json 文件已成功更新。")
    except Exception as e:
        print(f"写入文件时发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
