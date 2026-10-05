import os
import re
import sys

def main():
    server = os.environ.get("RENDEZVOUS_SERVER", "").strip()
    key = os.environ.get("RS_PUB_KEY", "").strip()
    api_server = os.environ.get("API_SERVER", "").strip()
    permanent_password = os.environ.get("PERMANENT_PASSWORD", "").strip()
    hide_server_settings = (os.environ.get("HIDE_SERVER_SETTINGS") or "Y").strip()

    print(f"Inject script started:")
    print(f"  RENDEZVOUS_SERVER set: {bool(server)}")
    print(f"  RS_PUB_KEY set: {bool(key)}")
    print(f"  API_SERVER set: {bool(api_server)}")
    print(f"  PERMANENT_PASSWORD set: {bool(permanent_password)}")
    print(f"  HIDE_SERVER_SETTINGS: {hide_server_settings}")

    if not server and not key and not api_server and not permanent_password and not hide_server_settings:
        print("::warning::No custom variables set, skipping config injection.")
        return

    # 1. 动态注入 libs/hbb_common/src/config.rs (ID 服务器, Key 以及 预设固定密码)
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

        if permanent_password:
            escaped_pass = permanent_password.replace('\\', '\\\\').replace('"', '\\"')
            if 'pub const PRESET_PERMANENT_PASSWORD' not in content:
                content = content.replace(
                    'pub const RS_PUB_KEY: &str =',
                    f'pub const PRESET_PERMANENT_PASSWORD: &str = "{escaped_pass}";\npub const RS_PUB_KEY: &str ='
                )
            else:
                content = re.sub(
                    r'pub const PRESET_PERMANENT_PASSWORD: &str = .*?;',
                    f'pub const PRESET_PERMANENT_PASSWORD: &str = "{escaped_pass}";',
                    content
                )

            old_storage_code = 'let storage = hard_settings.get("password").cloned().unwrap_or_default();'
            new_storage_code = (
                'let mut storage = hard_settings.get("password").cloned().unwrap_or_default();\n'
                '        if storage.is_empty() && !PRESET_PERMANENT_PASSWORD.is_empty() {\n'
                '            storage = PRESET_PERMANENT_PASSWORD.to_string();\n'
                '        }'
            )
            if old_storage_code in content:
                content = content.replace(old_storage_code, new_storage_code)
                print("Successfully injected PRESET_PERMANENT_PASSWORD fallback logic")
            elif 'PRESET_PERMANENT_PASSWORD.to_string()' in content:
                print("PRESET_PERMANENT_PASSWORD fallback logic already present")

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        print(f"::warning::{config_path} not found!")

    # 2. 动态注入 src/common.rs (API 服务器地址 & 隐藏服务器设置选项)
    common_path = os.path.join("src", "common.rs")
    if os.path.exists(common_path):
        with open(common_path, "r", encoding="utf-8") as f:
            common_content = f.read()

        if api_server:
            common_content = re.sub(
                r'"https://admin\.rustdesk\.com"\.to_owned\(\)',
                f'"{api_server}".to_owned()',
                common_content
            )
            print(f"Successfully injected default API_SERVER = {api_server}")

        if hide_server_settings.upper() in ["Y", "YES", "TRUE", "1"]:
            if 'key == "hide-server-settings"' in common_content:
                print("hide-server-settings injection already present in src/common.rs")
            else:
                pat = re.compile(r'(pub fn get_builtin_option\s*\(\s*key:\s*&str\s*\)\s*->\s*String\s*\{\r?\n)')
                m = pat.search(common_content)
                if m:
                    inj = '    if key == "hide-server-settings" {\r\n        return "Y".to_owned();\r\n    }\r\n'
                    common_content = common_content[:m.end()] + inj + common_content[m.end():]
                    print("Successfully injected hide-server-settings = 'Y' into src/common.rs")
                else:
                    print("::error::Could not find pub fn get_builtin_option in src/common.rs!")
                    sys.exit(1)

        with open(common_path, "w", encoding="utf-8") as f:
            f.write(common_content)

    # 3. 动态注入 Flutter UI 前端代码 (双重保证隐藏设置)
    if hide_server_settings.upper() in ["Y", "YES", "TRUE", "1"]:
        ui_files = [
            os.path.join("flutter", "lib", "desktop", "pages", "desktop_setting_page.dart"),
            os.path.join("flutter", "lib", "mobile", "pages", "settings_page.dart"),
        ]
        pat_flutter = re.compile(r'(_?hideServer\s*=\s*)bind\.mainGetBuildinOption\(key:\s*kOptionHideServerSetting\)\s*==\s*[\'"]Y[\'"];')
        for uipath in ui_files:
            if os.path.exists(uipath):
                with open(uipath, "r", encoding="utf-8") as f:
                    uicontent = f.read()
                m = pat_flutter.search(uicontent)
                if m:
                    uicontent_new = pat_flutter.sub(r'\1true; // CI injected', uicontent)
                    with open(uipath, "w", encoding="utf-8") as f:
                        f.write(uicontent_new)
                    print(f"Successfully injected hideServer = true into {uipath}")
                elif "hideServer = true; // CI injected" in uicontent:
                    print(f"hideServer = true already present in {uipath}")
                else:
                    print(f"::warning::Could not match hideServer in {uipath}")

    print("Custom server configuration injection finished.")

if __name__ == "__main__":
    main()
