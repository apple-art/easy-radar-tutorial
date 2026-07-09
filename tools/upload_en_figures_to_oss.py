#!/usr/bin/env python3
"""Upload English textbook figures to pico-tcq OSS under img/en/ without overwriting Chinese assets."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

try:
    import oss2
except ImportError:
    print("oss2 not installed; run: pip install oss2", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parents[1]
EN_FIG_ROOT = REPO / "figures" / "en"
OSS_PREFIX = "img/en/"
PUBLIC_BASE = "https://pico-tcq.oss-cn-shanghai.aliyuncs.com/"


def load_aliyun_config() -> dict:
    candidates = [
        Path(os.environ.get("APPDATA", "")) / "picgo" / "data.json",
        Path.home() / ".picgo" / "config.json",
    ]
    for p in candidates:
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        aliyun = (data.get("picBed") or {}).get("aliyun")
        if aliyun and aliyun.get("accessKeyId") and aliyun.get("accessKeySecret"):
            return aliyun
    raise RuntimeError("No PicGo aliyun credentials found")


def main() -> int:
    conf = load_aliyun_config()
    auth = oss2.Auth(conf["accessKeyId"], conf["accessKeySecret"])
    endpoint = f"https://{conf.get('area', 'oss-cn-shanghai')}.aliyuncs.com"
    bucket = oss2.Bucket(auth, endpoint, conf["bucket"])

    files = sorted(EN_FIG_ROOT.rglob("*.png"))
    if not files:
        print(f"No PNG files under {EN_FIG_ROOT}", file=sys.stderr)
        return 1

    print(f"Uploading {len(files)} files to oss://{conf['bucket']}/{OSS_PREFIX}")
    ok = 0
    fail = []
    urls = []

    for i, path in enumerate(files, 1):
        # Keep basename only under img/en/ to match flat Chinese style, avoid collisions.
        key = OSS_PREFIX + path.name
        try:
            headers = {"Content-Type": "image/png", "Cache-Control": "public, max-age=31536000"}
            result = bucket.put_object_from_file(key, str(path), headers=headers)
            status = getattr(result, "status", None)
            url = PUBLIC_BASE + key
            if status not in (200, 203, None):
                raise RuntimeError(f"unexpected status {status}")
            # quick existence check via OSS API
            if not bucket.object_exists(key):
                raise RuntimeError("object_exists false after put")
            urls.append((path.name, url))
            ok += 1
            print(f"[{i}/{len(files)}] OK {key}")
        except Exception as e:
            fail.append((str(path), str(e)))
            print(f"[{i}/{len(files)}] FAIL {path.name}: {e}", file=sys.stderr)
            time.sleep(0.2)

    print(f"\nDone: ok={ok} fail={len(fail)}")
    if fail:
        for p, err in fail:
            print(f"  - {p}: {err}", file=sys.stderr)
        return 2

    # HTTP spot-check a few public URLs
    print("\nHTTP checks:")
    for name, url in urls[:3] + urls[-2:]:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=20) as resp:
                print(f"  {resp.status} {name}")
        except Exception as e:
            print(f"  FAIL {name}: {e}", file=sys.stderr)

    # write mapping for HTML rewrite
    map_path = REPO / "tools" / "en_figure_oss_map.json"
    mapping = {name: url for name, url in urls}
    map_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {map_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
