import os
import re
import sys

def main():
    server = os.environ.get("RENDEZVOUS_SERVER", "").strip()
    key = os.environ.get("RS_PUB_KEY", "").strip()

    if not server and not key:
        print("::warning::RENDEZVOUS_SERVER and RS_PUB_KEY secrets not set, skipping config injection.")
        return

    config_path = os.path.join("libs", "hbb_common", "src", "config.rs")
    if not os.path.exists(config_path):
        print(f"::error::{config_path} not found!")
        return

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

    print("Custom server configuration injection finished.")

if __name__ == "__main__":
    main()
