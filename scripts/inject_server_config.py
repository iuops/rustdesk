import os
import re
import sys

def main():
    server = os.environ.get("RENDEZVOUS_SERVER", "").strip()
    key = os.environ.get("RS_PUB_KEY", "").strip()
    api_server = os.environ.get("API_SERVER", "").strip()

    if not server and not key and not api_server:
        print("::warning::RENDEZVOUS_SERVER, RS_PUB_KEY and API_SERVER secrets not set, skipping config injection.")
        return

    # 1. 注入 libs/hbb_common/src/config.rs (ID 服务器与 Key)
    config_path = os.path.join("libs", "hbb_common", "src", "config.rs")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        if server:
            content = re.sub(
                r'pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[.*?\];',
                f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{server}"];',
                content
            )
            print(f"Successfully injected RENDEZVOUS_SERVERS = {server}")

        if key:
            content = re.sub(
                r'pub const RS_PUB_KEY: &str = .*?;',
                f'pub const RS_PUB_KEY: &str = "{key}";',
                content
            )
            print(f"Successfully injected RS_PUB_KEY (len={len(key)})")

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        print(f"::warning::{config_path} not found!")

    # 2. 注入 src/common.rs (API 服务器地址)
    common_path = os.path.join("src", "common.rs")
    if api_server and os.path.exists(common_path):
        with open(common_path, "r", encoding="utf-8") as f:
            common_content = f.read()

        # 匹配并将默认兜底的 admin.rustdesk.com 替换为自定义的 API 服务器地址
        common_content = re.sub(
            r'"https://admin\.rustdesk\.com"\.to_owned\(\)',
            f'"{api_server}".to_owned()',
            common_content
        )
        with open(common_path, "w", encoding="utf-8") as f:
            f.write(common_content)
        print(f"Successfully injected default API_SERVER = {api_server}")

    print("Custom server configuration injection finished.")

if __name__ == "__main__":
    main()
