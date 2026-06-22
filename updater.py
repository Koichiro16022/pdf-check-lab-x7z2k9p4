# updater.py — 零(ZERO) 自動更新スクリプト
import urllib.request
import urllib.parse
import json
import os

REPO   = "Koichiro16022/pdf-check-lab-x7z2k9p4"
BRANCH = "main"
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, ".zero_version")

FILES_TO_UPDATE = [
    "streamlit_app診断ボタン付き.py",
    "modules/cell_comparator.py",
    "modules/excel_exporter.py",
    "modules/file_loader.py",
    "modules/sheet_comparator.py",
    "modules/image_comparator.py",
]

def get_latest_commit():
    url = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ZERO-updater/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data["sha"]
    except Exception:
        return None

def get_local_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def download_file(path):
    encoded_path = urllib.parse.quote(path)
    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{encoded_path}"
    local_path = os.path.join(BASE_DIR, path.replace("/", os.sep))
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ZERO-updater/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read()
    with open(local_path, "wb") as f:
        f.write(content)

def save_version(sha):
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(sha)

def main():
    print("■ 零(ZERO) 自動更新チェック...")
    latest = get_latest_commit()
    if latest is None:
        print("  ネットワーク未接続のためスキップします")
        print()
        return
    local = get_local_version()
    if latest == local:
        print("  最新版です")
        print()
        return
    print("  新しいバージョンが見つかりました。更新中...")
    success = True
    for file_path in FILES_TO_UPDATE:
        try:
            download_file(file_path)
            print(f"  OK  {file_path}")
        except Exception as e:
            print(f"  NG  {file_path}: {e}")
            success = False
    if success:
        save_version(latest)
        print("  更新完了！")
    else:
        print("  一部ファイルの更新に失敗しました（起動は続行します）")
    print()

if __name__ == "__main__":
    main()
