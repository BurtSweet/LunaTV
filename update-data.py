import os
import sys
import json
import requests
import base58
import argparse
from typing import Dict, Any, List, Union

# --- 全局配置常量 ---
REQUEST_TIMEOUT = 10
CONFIG_FILE = "config.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
SUBSCRIPTION_URLS = [
    r'https://raw.githubusercontent.com/hafrey1/LunaTV-config/refs/heads/main/LunaTV-config.txt',

]
# 成人内容过滤关键词,识别源的名称中包含该关键词的源
ADULT_FILTER_KEYWORD = ['AV', '🔞', '成人', '情色', 'H漫', 'H动画', 'H漫画', 'H剧场版', 'H电影', 'H视频', '18禁', 'R18', 'R-18']
#成人内容过滤的默认开关
ENABLE_ADULT_FILTER = True


# --- 辅助函数 (保持不变) ---

def load_config(filename: str) -> Dict[str, Any]:
    """
    从指定文件加载配置数据。
    如果文件不存在，返回默认结构；如果解析失败，则退出程序。
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            print(f"✅ 成功加载现有配置: {filename}")
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ {filename} 文件未找到，将使用默认空配置。")
        return {"api_site": {}}
    except json.JSONDecodeError as e:
        print(f"❌ 错误：无法解析 {filename} 文件: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 读取 {filename} 时发生未知错误: {e}", file=sys.stderr)
        sys.exit(1)


def save_config(filename: str, data: Dict[str, Any]):
    """
    将配置数据写入指定文件。
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ {filename} 文件已成功保存和更新。")
    except Exception as e:
        print(f"❌ 写入文件 {filename} 时发生错误: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_subscription_content(url: str) -> Union[str, None]:
    """
    从URL获取原始内容字符串，并处理网络请求异常。
    """
    print(f"正在尝试获取订阅链接内容: {url}")
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}", file=sys.stderr)
        return None


def parse_content(content: str) -> Dict[str, Any] | None:
    """
    尝试Base58解码内容，然后解析JSON。
    """
    content_to_parse = content

    try:
        content_bytes = content.encode('ascii')
        decoded_bytes = base58.b58decode(content_bytes)
        content_to_parse = decoded_bytes.decode('utf-8')
        print("✅ 内容已成功进行 Base58 解码。")
    except (ValueError, UnicodeDecodeError, AttributeError):
        pass

    try:
        return json.loads(content_to_parse)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败。请检查原始内容或 Base58 解码后的内容: {e}", file=sys.stderr)
        return None


def validate_video_source(url: str) -> bool:
    """
    通过发送HEAD请求检查视频源URL的有效性。
    """
    print(f"-> 正在检查URL: {url}")
    try:
        response = requests.head(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True
        )

        if response.ok:
            print(f"   ✅ URL有效。状态码：{response.status_code}")
            return True
        else:
            print(f"   ❌ URL无效。状态码：{response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 请求失败: {e}")
        return False


def process_subscriptions(urls: List[str], existing_sources: Dict[str, Any]):
    """
    遍历订阅URL，获取内容，解析并合并新的频道数据到现有源中。
    """
    for url in urls:
        content = fetch_subscription_content(url)
        if content is None:
            continue

        new_data = parse_content(content)
        if new_data and "api_site" in new_data:
            print(f"✅ 成功解析并合并 {url} 中的 {len(new_data['api_site'])} 个新源。")
            existing_sources.update(new_data["api_site"])


# --- 核心逻辑函数 (添加了过滤开关) ---

def filter_and_validate_sources(sources: Dict[str, Any], enable_adult_filter: bool):
    """
    对现有源进行成人内容过滤和有效性检查，并原地修改字典。
    根据 enable_adult_filter 的值决定是否进行成人内容过滤。
    """
    print("\n--- 开始执行过滤和有效性检查 ---")
    keys_to_delete = []

    # 1. 成人内容过滤 (AV)
    if enable_adult_filter:
        print(f"ℹ️ 成人内容过滤已启用。关键词: '{ADULT_FILTER_KEYWORD}'")
        for key, source_info in sources.items():
            name = source_info.get('name', '')
            is_adult = source_info.get('is_adult', '')
            if key in keys_to_delete:
                continue
            if is_adult is True:
                print(f"🗑️ 过滤: 源 '{name}' 标记为成人内容，已标记删除。")
                keys_to_delete.append(key)
            for adult in ADULT_FILTER_KEYWORD:
                if adult in name:
                    print(f"🗑️ 过滤: 源 '{name}' 包含成人内容关键词，已标记删除。")
                    keys_to_delete.append(key)
    else:
        print("ℹ️ 成人内容过滤已禁用。")

    # 2. 源的有效性检查 (总是执行)
    print("\n--- 开始检查源的有效性 ---")
    for key, source_info in sources.items():
        # 跳过已被标记删除的源
        if key in keys_to_delete:
            continue

        api_url = source_info.get('api')
        if not api_url:
            print(f"🗑️ 删除: 源 '{source_info.get('name', '未知')}' 缺少 'api' URL。")
            keys_to_delete.append(key)
            continue

        if not validate_video_source(api_url):
            print(f"🗑️ 删除: 源 '{source_info.get('name', '未知')}' ({api_url}) 有效性检查失败。")
            keys_to_delete.append(key)

    # 3. 实际执行删除操作
    deleted_count = 0
    for key in set(keys_to_delete):
        if key in sources:
            del sources[key]
            deleted_count += 1

    print(f"\n✅ 过滤和检查完成。共删除 {deleted_count} 个源。")


def main():
    """主函数，负责控制流程和命令行参数解析。"""

    # --- 0. 解析命令行参数 ---
    parser = argparse.ArgumentParser(description="自动更新配置文件的视频源列表，并执行有效性检查和过滤。")
    parser.add_argument(
        '--no-adult-filter',
        action='store_true',  # 当设置此参数时，值为 True
        default=False,
        help="禁用成人内容过滤。默认是启用的。"
    )
    args = parser.parse_args()

    # 根据命令行参数设置过滤开关
    adult_filter_enabled = ENABLE_ADULT_FILTER and (not args.no_adult_filter)

    print("--- 脚本开始运行 ---")

    # 1. 读取现有的 config.json 文件
    config_data = load_config(CONFIG_FILE)

    if "api_site" not in config_data or not isinstance(config_data["api_site"], dict):
        config_data["api_site"] = {}

    existing_sources = config_data["api_site"]
    initial_count = len(existing_sources)
    print(f"当前配置中共有 {initial_count} 个现有源。")

    # 2. 从订阅链接获取新的频道数据并合并
    process_subscriptions(SUBSCRIPTION_URLS, existing_sources)

    # 3. 过滤和有效性检查
    filter_and_validate_sources(existing_sources, adult_filter_enabled)

    # 4. 将更新后的JSON结构写入 config.json
    final_count = len(existing_sources)
    print(f"\n--- 脚本运行结果 ---")
    print(f"合并前源数量: {initial_count}")
    print(f"合并后剩余源数量: {final_count}")

    save_config(CONFIG_FILE, config_data)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 脚本发生致命错误: {e}", file=sys.stderr)

        sys.exit(1)
