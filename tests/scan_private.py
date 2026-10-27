#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描仓库文本文件中的个人信息与常见敏感串。

用途：公开仓库的守门人。CI 在每次 push / PR 时跑一遍，防止把作者信息、
联系方式、身份证号之类的东西带进来。

用法（仓库根目录）：

    python tests/scan_private.py

退出码：0 未发现；1 发现可疑内容；2 路径错误。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# 同 verify.py：避免 Windows 管道下的 cp1252 编码错误
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

# 只看这些后缀，避免扫二进制
EXTS = {".md", ".txt", ".csv", ".py", ".bat", ".yml", ".yaml", ".json"}

# 整行跳过：示例与占位
SKIP_LINE = re.compile(
    r"(0000-0000-0000-0000|example\.(com|org)|your-name|<your|xxx|XXX|示例|占位)"
)

PATTERNS = [
    ("邮箱", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("中国大陆手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("身份证号", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")),
    ("ORCID", re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")),
    ("微信号/QQ 号", re.compile(r"(?:微信|QQ|qq)\s*[:：]?\s*\d{5,12}")),
]

# 本文件自身与测试样本不参与扫描（它们本来就在描述这些模式）
SKIP_FILES = {Path(__file__).resolve()}


def main() -> int:
    if not ROOT.exists():
        print("[错误] 找不到仓库根目录：%s" % ROOT)
        return 2

    hits: list[str] = []
    scanned = 0

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {".git", "__pycache__"} for part in path.parts):
            continue
        if path.resolve() in SKIP_FILES:
            continue
        if path.suffix.lower() not in EXTS:
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print("[警告] 读不了 %s：%s" % (path, exc))
            continue

        for no, line in enumerate(text.splitlines(), 1):
            if SKIP_LINE.search(line):
                continue
            for label, pattern in PATTERNS:
                m = pattern.search(line)
                if m:
                    rel = path.relative_to(ROOT)
                    hits.append("%s:%d  [%s]  %s" % (rel, no, label, m.group(0)))

    print("扫描 %d 个文本文件。" % scanned)
    if hits:
        print("\n发现 %d 处可疑内容（请确认是否应公开）：" % len(hits))
        for h in hits:
            print("  " + h)
        return 1

    print("未发现邮箱、手机号、身份证号、ORCID 或社交账号。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
