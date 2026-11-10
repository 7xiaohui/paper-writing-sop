#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看论文工作区进度（英文论文写作 SOP v2）

用法：
    python check_workspace.py <工作区目录> [--strict]

输出：
    每一步的产物是否就位，当前停在第几步，下一步该产出哪个文件。

退出码：
    0 始终为 0；加 --strict 时，未跑完 11 步返回 1。
"""

from __future__ import annotations

import argparse
from pathlib import Path

# 步骤号 -> (步骤名, 正文文件名)
STEPS = {
    1: ("起步", "01-起步.md"),
    2: ("选题", "02-选题.md"),
    3: ("定刊", "03-定刊.md"),
    4: ("两库", "04-两库.md"),
    5: ("结构", "05-结构.md"),
    6: ("初稿", "06-初稿.md"),
    7: ("清稿", "07-清稿与冻结.md"),
    8: ("英译", "08-英译.md"),
    9: ("体检", "09-痕迹与体检.md"),
    10: ("投稿件", "10-投稿件.md"),
    11: ("投递与返修", "11-投递与返修.md"),
}

# (步骤号, 相对路径, 类型 file / dir)
PRODUCTS = [
    (1, "00-锚点.md", "file"),
    (1, "01-起步/类型判定.md", "file"),
    (1, "01-起步/术语表.csv", "file"),
    (2, "02-选题/选题卡.md", "file"),
    (2, "02-选题/粗扫记录.md", "file"),
    (3, "03-定刊/筛选前提.md", "file"),
    (3, "03-定刊/候选池.md", "file"),
    (3, "03-定刊/顺位表.md", "file"),
    (3, "03-定刊/指南硬约束.md", "file"),
    (3, "03-定刊/近刊对标.md", "file"),
    (3, "03-定刊/字数契约.md", "file"),
    (4, "04-两库/文献卡.md", "file"),
    (4, "04-两库/主张-出处表.md", "file"),
    (4, "04-两库/材料台账.md", "file"),
    (4, "04-两库/四查报告.md", "file"),
    (4, "04-两库/学库", "dir:*.pdf"),
    (4, "04-两库/材库", "dir"),
    (5, "05-结构/论证表.md", "file"),
    (5, "05-结构/句串.md", "file"),
    (5, "05-结构/命题-反例-回应.md", "file"),
    (6, "06-初稿/中文-v1.md", "file"),
    (7, "07-清稿/中文-冻结-v1.md", "file"),
    (8, "08-英译/英文-v1.md", "file"),
    (9, "09-体检/体检报告.md", "file"),
    (10, "10-投稿包", "dir:*.docx"),
    (11, "11-投递/投稿记录.md", "file"),
]

# 这些文件刚建出来时只是模板，填没填要看标记；这里不猜内容，只区分“有文件”与“填过”。
STUB_MARKER = "stub: 未填写"


def is_dir_nonempty(p: Path, pattern: str = "*", min_files: int = 1) -> bool:
    if not p.is_dir():
        return False
    return sum(1 for x in p.rglob(pattern) if x.is_file()) >= min_files


def file_state(p: Path) -> str:
    """missing / stub / ok"""
    if not p.is_file():
        return "missing"
    try:
        head = p.read_text(encoding="utf-8", errors="ignore")[:2000]
    except OSError:
        return "ok"
    return "stub" if STUB_MARKER in head else "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="查看论文工作区进度")
    parser.add_argument("space", help="工作区目录")
    parser.add_argument("--strict", action="store_true", help="未跑完 11 步时返回 1")
    args = parser.parse_args()

    root = Path(args.space).expanduser().resolve()
    if not root.is_dir():
        print(f"找不到工作区：{root}")
        return 2

    print(f"工作区：{root}\n")

    pending: dict[int, dict[str, list[str]]] = {
        s: {"缺": [], "未填": []} for s in STEPS
    }
    for step, rel, kind in PRODUCTS:
        p = root / rel
        if kind.startswith("dir"):
            pattern = kind.split(":", 1)[1] if ":" in kind else "*"
            if not is_dir_nonempty(p, pattern):
                need = "至少 1 个文件" if pattern == "*" else f"至少 1 个 {pattern}"
                pending[step]["缺"].append(rel + f"/（{need}）")
            continue
        state = file_state(p)
        if state == "missing":
            pending[step]["缺"].append(rel)
        elif state == "stub":
            pending[step]["未填"].append(rel)

    for step in sorted(STEPS):
        name, _doc = STEPS[step]
        miss = pending[step]["缺"]
        stub = pending[step]["未填"]
        if not miss and not stub:
            print(f"[OK] 第 {step:>2} 步 {name}：就位")
        elif miss:
            more = f" 等 {len(miss)} 项" if len(miss) > 1 else ""
            print(f"[  ] 第 {step:>2} 步 {name}：缺 {miss[0]}{more}")
        else:
            more = f" 等 {len(stub)} 项" if len(stub) > 1 else ""
            print(f"[..] 第 {step:>2} 步 {name}：模板未填 {stub[0]}{more}")

    current = next(
        (s for s in sorted(STEPS) if pending[s]["缺"] or pending[s]["未填"]), None
    )
    print()
    if current is None:
        print("11 步产物全部就位。接下来是第 11 步之后的循环：返修 / 转投。")
    else:
        name, doc = STEPS[current]
        print(f"当前进度：第 {current} 步「{name}」")
        if pending[current]["缺"]:
            print(f"下一步：读 en/{doc}，产出 {pending[current]['缺'][0]}")
        else:
            print(f"下一步：读 en/{doc}，填完 {pending[current]['未填'][0]}（并删掉 stub 标记行）")
        print("提醒：文件存在 ≠ 内容合格。每个判据在对应正文的“判据”一节。")

    if args.strict and current is not None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
