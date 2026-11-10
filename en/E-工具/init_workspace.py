#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""初始化论文工作区（英文论文写作 SOP v2 · 第 1 步）

用法：
    python init_workspace.py <工作区目录> [--title "临时题目"]

规则：
    - 只补不改：目录缺就建，文件缺就写模板，已存在的一律跳过。
    - 幂等：可以反复运行，不会覆盖你已经写的内容。
"""

from __future__ import annotations

import argparse
from pathlib import Path

DIRS = [
    "01-起步",
    "02-选题",
    "03-定刊",
    "03-定刊/原文",
    "04-两库",
    "04-两库/学库",
    "04-两库/材库",
    "05-结构",
    "06-初稿",
    "07-清稿",
    "08-英译",
    "09-体检",
    "10-投稿包",
    "11-投递",
    "_来源",
    "_存档",
]

# (相对路径, 步骤号, 步骤名, 对应正文, 判据)
FILES = [
    ("00-锚点.md", 1, "起步", "01-起步.md", "五条铁律齐全，且每条写有本次项目的具体口径"),
    ("01-起步/类型判定.md", 1, "起步", "01-起步.md", "四类只选一类，并写明源语言（中文源 / 直接英文）"),
    ("01-起步/术语表.csv", 1, "起步", "01-起步.md", "≥10 条，每条有来源，同一中文只对应一个英文"),
    ("02-选题/选题卡.md", 2, "选题", "02-选题.md", "四问可答；三句话不含“重要/意义”；双靶有候选并标【待核】"),
    ("02-选题/粗扫记录.md", 2, "选题", "02-选题.md", "记录 10 篇的题名、对象、主张，以及“有没有 3 篇跟我问的一样”"),
    ("03-定刊/筛选前提.md", 3, "定刊", "03-定刊.md", "七项前提逐条有结论（可 / 不可 / 待问）"),
    ("03-定刊/候选池.md", 3, "定刊", "03-定刊.md", "每刊有 Aims 匹配原句与出处；排除的也写理由"),
    ("03-定刊/顺位表.md", 3, "定刊", "03-定刊.md", "A/B/C 三档，并写明为什么 A 在第一位"),
    ("03-定刊/指南硬约束.md", 3, "定刊", "03-定刊.md", "每条能指到作者指南的第几段"),
    ("03-定刊/近刊对标.md", 3, "定刊", "03-定刊.md", "摘要词数、结构惯例、语域、引用条数四项有数据"),
    ("03-定刊/字数契约.md", 3, "定刊", "03-定刊.md", "英文上限倒推中文总量，留 10% 余量"),
    ("04-两库/文献卡.md", 4, "两库", "04-两库.md", "一行一个可引点（文N-M）；英文原句逐字；中文主张句一句；位置写“14页/§4.2”，不写 p."),
    ("04-两库/主张-出处表.md", 4, "两库", "04-两库.md", "每条主张有出处或“推理＋前提”；承接链无断点；无孤儿主张"),
    ("04-两库/材料台账.md", 4, "两库", "04-两库.md", "每条材料有原件全名、文号/页码、时间、用在哪"),
    ("04-两库/四查报告.md", 4, "两库", "04-两库.md", "真 / 对 / 该 / 漏 四查 0 错"),
    ("05-结构/论证表.md", 5, "结构", "05-结构.md", "每节有主张号、结论句、字数，字数合计与契约一致"),
    ("05-结构/句串.md", 5, "结构", "05-结构.md", "不看正文，只读句串能复述完整论证"),
    ("05-结构/命题-反例-回应.md", 5, "结构", "05-结构.md", "每条命题有 2 条反驳，且有处置（改/限定/补/维持）"),
    ("06-初稿/中文-v1.md", 6, "初稿", "06-初稿.md", "段型对；四问过；全量类主张覆盖率 100%；字数 ±5%"),
    ("07-清稿/中文-冻结-v1.md", 7, "清稿", "07-清稿与冻结.md", "六类清零，五类保留，三个脚本 0 命中"),
    ("08-英译/英文-v1.md", 8, "英译", "08-英译.md", "五查全过；10 段回译漂移 0；数字 100% 一致"),
    ("09-体检/体检报告.md", 9, "体检", "09-痕迹与体检.md", "高危句式 0；改写段漂移 0；声明与档位匹配"),
    ("10-投稿包", 10, "投稿件", "10-投稿件.md", "四份 docx 都能打开；元数据 0；匿名 0；十八项终检全过"),
    ("11-投递/投稿记录.md", 11, "投递与返修", "11-投递与返修.md", "四查过；冻结留证；前刊终结才转投"),
]

STUB_MARKER = "<!-- stub: 未填写。填完请删除本行。 -->"

MD_TEMPLATE = """# {title}

> 第 {step} 步「{step_name}」产物 ｜ 填法见 `en-v2/{doc}`（本仓库第 {step} 步正文）
> 判据：{criteria}

{marker}

## 填写区

（直接改这个文件。不要新建“同名最终版”。填完删掉上面那行标记。）
"""

README_TEMPLATE = """# {title}

| 项 | 内容 |
|---|---|
| 题目（临时） |  |
| 目标刊 |  |
| 论文类型 | 概念型 / 比较型 / 对策型 / 小调查型 |
| 源语言 | 中文源 / 直接英文 |
| 现在第几步 | 1 |
| 下一步 | 填 `00-锚点.md` 与 `01-起步/` |
| 卡在哪 |  |

## 进度

{checklist}

> 进度以 `python E-工具/check_workspace.py .` 的输出为准，不靠这张表。
"""


def build_tree(root: Path, title: str) -> tuple[int, int]:
    made_dirs = 0
    made_files = 0

    for d in DIRS:
        p = root / d
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            made_dirs += 1

    for rel, step, step_name, doc, criteria in FILES:
        p = root / rel
        if p.exists():
            continue
        if p.suffix == ".csv":
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("中文,英文,来源,禁用写法\n", encoding="utf-8")
            made_files += 1
        elif p.suffix == ".md":
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                MD_TEMPLATE.format(
                    title=p.stem,
                    step=step,
                    step_name=step_name,
                    doc=doc,
                    criteria=criteria,
                    marker=STUB_MARKER,
                ),
                encoding="utf-8",
            )
            made_files += 1

    readme = root / "README.md"
    if not readme.exists():
        checklist = "\n".join(
            "- [ ] 第 {s} 步 {n}".format(s=s, n=n)
            for s, n in [
                (1, "起步"), (2, "选题"), (3, "定刊"), (4, "两库"),
                (5, "结构"), (6, "初稿"), (7, "清稿"), (8, "英译"),
                (9, "体检"), (10, "投稿件"), (11, "投递与返修"),
            ]
        )
        readme.write_text(
            README_TEMPLATE.format(title=title, checklist=checklist),
            encoding="utf-8",
        )
        made_files += 1

    return made_dirs, made_files


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化论文工作区（只补不改）")
    parser.add_argument("target", help="工作区目录，例如 ..\\paper-01")
    parser.add_argument("--title", default="未命名论文", help="临时题目，可后改")
    args = parser.parse_args()

    root = Path(args.target).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    made_dirs, made_files = build_tree(root, args.title)
    print(f"工作区：{root}")
    print(f"新建目录 {made_dirs} 个，新建文件 {made_files} 个（已存在的已跳过）")
    print("下一步：读 en-v2/01-起步.md，填 00-锚点.md 与 01-起步/ 三件")
    print(f"查进度：python E-工具/check_workspace.py {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
