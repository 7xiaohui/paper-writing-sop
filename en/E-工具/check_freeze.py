#!/usr/bin/env python3
"""冻结前清稿检查：六类"写给自己看的话"是否清零。

用法：
    python E-工具/check_freeze.py 07-清稿/中文-v1.md

退出码：0 = 六类 0 命中，可以冻结；1 = 有命中，需先处理。
"""

import re
import sys
from pathlib import Path

PATTERNS = [
    ("待定/中间态", r"待补|待定|待核|待确认|待填|TODO|TBD|XXX|【待|？？|\?\?"),
    ("内部工作语", r"\[P\d+\]|见上表|如前述|本表所示|第\s*\d+\s*步|按锚点"),
    ("投稿策略", r"这本刊|该刊偏好|审稿人可能|为迎合|迎合[，。]|字数快超|投稿策略"),
    ("版本尾注", r"\bv[1-9]\b|第[一二三四五]稿|改于|上一版|修订版"),
    ("回迁语", r"回到前面|如前所述|前面提到|上文已述|前文已述"),
    ("审稿痕迹", r"审稿意见|返修|response to reviewer|reviewer|编辑建议|已按意见"),
]


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python E-工具/check_freeze.py <中文稿路径>")
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"找不到文件：{path}")
        return 2

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    total = 0
    print(f"检查对象：{path}")
    for label, pattern in PATTERNS:
        hits = []
        for no, line in enumerate(lines, 1):
            for m in re.finditer(pattern, line):
                snippet = line.strip()
                if len(snippet) > 60:
                    start = max(0, m.start() - 20)
                    snippet = "…" + line[start:start + 50].strip() + "…"
                hits.append((no, snippet))
        if hits:
            print(f"\n[{label}] {len(hits)} 处")
            for no, snippet in hits[:20]:
                print(f"  L{no}: {snippet}")
            if len(hits) > 20:
                print(f"  …另有 {len(hits) - 20} 处")
            total += len(hits)
        else:
            print(f"[{label}] 0")

    body_chars = len(re.sub(r"\s", "", text))
    print(f"\n字数（去空白）：{body_chars}")

    if total:
        print(f"\n合计 {total} 处命中；冻结前必须清零。")
        return 1

    print("\n六类 0 命中，可以冻结。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
