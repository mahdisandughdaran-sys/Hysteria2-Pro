import json
import urllib.parse
import argparse
import qrcode
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Literal

def generate_singbox_config(
    servers: List[Dict[str, str]],
    mode: Literal["urltest", "selector"] = "urltest",
    output_dir: str = "configs"
) -> None:
    """Generator فوق‌بشری Sing-box ۲۰۲۶ — نسخه نهایی و تجاری"""
    Path(output_dir).mkdir(exist_ok=True)
    
    if not servers:
        raise ValueError("❌ لیست سرورها خالی است! فایل servers.json را چک کن.")

    config = {
        "log": {"level": "warn", "timestamp": True},
        "dns": {
            "servers": [
                {"tag": "google", "address": "tls://8.8.8.8", 
                 "detour": "auto" if mode == "urltest" else "selector"},
                {"tag": "local", "address": "local"}
            ],
            "rules": [
                {"outbound": "any", "server": "local"},
                {"geosite": "category-ads-all", "server": "local"},
                {"geosite": "cn", "server": "local"},
                {"geosite": "private", "server": "local"}
            ],
            "final": "google"
        },
        "inbounds": [{
            "type": "tun", "tag": "tun-in", "interface_name": "tun0",
            "stack": "system", "address": ["172.19.0.1/30", "fdfe:dcba:9876::1/126"],
            "mtu": 9000, "auto_route": True, "strict_route": True, "sniff": True
        }],
        "outbounds": [],
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "dns-out"},
                {"geosite": "category-ads-all", "outbound": "block"},
                {"geosite": "cn", "outbound": "direct"},
                {"geosite": "private", "outbound": "direct"}
            ],
            "final": "auto" if mode == "urltest" else "selector",
            "auto_detect_interface": True
        }
    }

    hy_tags = []
    for i, s in enumerate(servers, 1):
        tag = f"hy2-{i}"
        hy_tags.append(tag)
        config["outbounds"].append({
            "type": "hysteria2", "tag": tag,
            "server": s["server"], "server_ports": ["443", "8000:9000"],
            "password": s["password"], "up_mbps": 100, "down_mbps": 100,
            "obfs": {"type": "salamander", "password": s["obfs"]},
            "tls": {"enabled": True, "server_name": s["sni"], "insecure": False}
        })

    if mode == "urltest":
        config["outbounds"].insert(0, {
            "type": "urltest", "tag": "auto", "outbounds": hy_tags,
            "url": "https://www.gstatic.com/generate_204", "interval": "30s", "tolerance": 50
        })
    else:
        config["outbounds"].insert(0, {
            "type": "selector", "tag": "selector", "outbounds": hy_tags, "default": hy_tags[0]
        })

    config["outbounds"].extend([
        {"type": "dns", "tag": "dns-out"},
        {"type": "direct", "tag": "direct"},
        {"type": "block", "tag": "block"}
    ])

    # ذخیره JSON
    json_path = Path(output_dir) / f"sing-box-hysteria2-{mode}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # Subscription + QR کد (اصلاح کامل بک‌اسلش‌ها)
    sub_lines = []
    for s in servers:
        safe_pass = urllib.parse.quote(s['password'], safe="")
        safe_obfs = urllib.parse.quote(s['obfs'], safe="")
        safe_name = urllib.parse.quote(s['name'], safe="\\~()*!.'")
        link = f"hysteria2://{safe_pass}@{s['server']}:443/?obfs=salamander&obfs-password={safe_obfs}&sni={s['sni']}&insecure=0#{safe_name}"
        sub_lines.append(link)

    sub_path = Path(output_dir) / "subscription.txt"
    with open(sub_path, "w", encoding="utf-8") as f:
        # اصلاح: استفاده از \n برای خط جدید استاندارد
        f.write("\n".join(sub_lines) + "\n")   

    # QR کد با لینک raw.githubusercontent و مدیریت اسلش‌های مسیر (as_posix)
    github_raw_url = f"https://raw.githubusercontent.com/mahdisandughdaran-sys/V2ray-sub/main/{sub_path.as_posix()}"
    qr = qrcode.make(github_raw_url)
    qr_path = Path(output_dir) / "subscription-qr.png"
    qr.save(qr_path)

    print(f"🚀 کانفیگ بی‌نقص با {len(servers)} سرور ({mode.upper()}) ساخته شد!")
    print(f"   JSON           : {json_path}")
    print(f"   Subscription   : {sub_path}")
    print(f"   QR Code        : {qr_path}")
    print(f"   لینک سابسکریپشن: {github_raw_url}")
    print(f"   زمان           : {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sing-box Config Generator — نسخه فوق‌بشری")
    parser.add_argument("--mode", choices=["urltest", "selector"], default="urltest", help="حالت خودکار یا دستی")
    parser.add_argument("--output", default="configs", help="مسیر خروجی")
    args = parser.parse_args()

    # لود سرورها از فایل (اگر وجود نداشته باشد، نمونه استفاده می‌شود)
    servers_path = Path("servers.json")
    if servers_path.exists():
        with open(servers_path, "r", encoding="utf-8") as f:
            servers_list = json.load(f)
    else:
        servers_list = [
            {"name": "🇺🇸 آمریکا ۱", "server": "us1.domain.com", "password": "pass1", "obfs": "obfs1", "sni": "www.bing.com"},
            {"name": "🇩🇪 آلمان ۲", "server": "de1.domain.com", "password": "pass2", "obfs": "obfs2", "sni": "www.yahoo.com"}
        ]
        print("⚠️  فایل servers.json پیدا نشد. از لیست نمونه استفاده شد.")

    generate_singbox_config(servers_list, mode=args.mode, output_dir=args.output)
