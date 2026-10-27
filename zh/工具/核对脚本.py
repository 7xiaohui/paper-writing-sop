#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文论文校对脚本（配套 0-总体SOP 的“脚本优先”工具）

子命令：
  refs     引用标号双向映射（SOP-6 第二步）
  numbers  正文数字清单 + 与底表比对（SOP-5 第④步）
  mats     【料N】抽取与计数（SOP-5 第①步）
  marks    【…】过程标记扫描（SOP-7 第一步）
  punct    标点与字形归属检查（SOP-7 第二步）
  props    清理 docx 文档属性（SOP-7 第二步）

示例：
  python 核对脚本.py refs 正文.md 参考文献.txt
  python 核对脚本.py numbers 正文.md 资料表.md
  python 核对脚本.py mats 正文.md
  python 核对脚本.py marks 正文.md
  python 核对脚本.py punct 论文.docx
  python 核对脚本.py punct 正文.md --limit 20
  python 核对脚本.py props 论文.docx --dry-run
  python 核对脚本.py props 论文.docx --author 张三 --title 论文标题

退出码：0 = 未发现问题；1 = 发现问题；2 = 参数或环境错误。
"""

import argparse
import os
import re
import sys

CITE_RE = re.compile(r"[\[［]([0-9][0-9,，\-–—~～\s]*)[\]］]")
MARK_RE = re.compile(r"【[^】\n]{1,30}】")
NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")


# ---------- 基础工具 ----------

def read_text(path):
    if not os.path.exists(path):
        sys.exit(f"[错误] 找不到文件：{path}")
    with open(path, "rb") as f:
        data = f.read()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def line_no(text, pos):
    return text.count("\n", 0, pos) + 1


def snippet(text, pos, width=24):
    s = text[max(0, pos - width): min(len(text), pos + width)]
    return re.sub(r"\s+", " ", s).strip()


def expand_citation(content):
    """把 '1' / '1,2' / '1-3' 展开成整数集合。"""
    content = content.replace("，", ",").replace("–", "-").replace("—", "-")
    content = content.replace("~", "-").replace("～", "-")
    nums = set()
    for part in content.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= b and b - a <= 200:
                nums.update(range(a, b + 1))
            else:
                nums.update((a, b))
        elif part.isdigit():
            nums.add(int(part))
    return nums


def print_header(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


# ---------- refs：标号双向映射 ----------

def parse_ref_numbers(text):
    """解析文末参考文献编号，返回 {编号: 原文行}。"""
    refs = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^[\[［](\d+)[\]］]\s*(.*)$", line)
        if not m:
            m = re.match(r"^(\d+)[.、．]\s*(.*)$", line)
        if not m:
            m = re.match(r"^(\d+)\s+(.*)$", line)
        if m:
            n = int(m.group(1))
            if n not in refs:
                refs[n] = m.group(2).strip() or line
    return refs


def cmd_refs(args):
    body = read_text(args.body)
    refs_text = read_text(args.refs)
    refs = parse_ref_numbers(refs_text)

    cited = {}
    for m in CITE_RE.finditer(body):
        for n in expand_citation(m.group(1)):
            cited.setdefault(n, []).append((line_no(body, m.start()), snippet(body, m.start())))

    body_set = set(cited)
    ref_set = set(refs)
    dangling = sorted(body_set - ref_set)
    redundant = sorted(ref_set - body_set)
    dup = {n: v for n, v in cited.items() if len(v) > 1}
    gaps = []
    if ref_set:
        lo, hi = min(ref_set), max(ref_set)
        gaps = [n for n in range(lo, hi + 1) if n not in ref_set]

    print_header("引用标号双向映射（SOP-6 第二步）")
    print(f"正文检出标号：{len(body_set)} 个 -> {sorted(body_set)}")
    print(f"文末文献编号：{len(ref_set)} 条 -> {sorted(ref_set)}")

    print(f"\n[悬空引用（正文有、文末无）] {len(dangling)} 处")
    for n in dangling:
        for ln, ctx in cited[n]:
            print(f"  [{n}] 第{ln}行：…{ctx}…")
    if not dangling:
        print("  无")

    print(f"\n[冗余文献（文末有、正文未引）] {len(redundant)} 条")
    for n in redundant:
        print(f"  [{n}] {refs[n][:60]}")
    if not redundant:
        print("  无")

    print(f"\n[重复标引] {len(dup)} 个编号出现多次")
    for n in sorted(dup):
        locs = "，".join(f"第{ln}行" for ln, _ in cited[n])
        print(f"  [{n}] 共 {len(cited[n])} 次（{locs}）")
    if not dup:
        print("  无")

    print(f"\n[跳号] {len(gaps)} 个空号")
    print("  " + (", ".join(map(str, gaps)) if gaps else "无"))

    issues = len(dangling) + len(redundant) + len(gaps)
    print(f"\n结论：{'发现问题，需处理' if issues else '未发现问题'}")
    print("提示：本步骤只做标号匹配；文献真假看 6-1，语义相关看 6-3。")
    return 1 if issues else 0


# ---------- numbers：数字比对 ----------

def extract_numbers(text):
    masked = CITE_RE.sub(lambda m: " " * len(m.group(0)), text)
    masked = MARK_RE.sub(lambda m: " " * len(m.group(0)), masked)
    out = []
    for m in NUM_RE.finditer(masked):
        raw = m.group(0)
        out.append((raw, line_no(text, m.start()), snippet(text, m.start())))
    return out


def as_key(raw):
    raw = raw.replace("%", "")
    try:
        return float(raw)
    except ValueError:
        return None


def cmd_numbers(args):
    body = read_text(args.body)
    base = read_text(args.base) if args.base else ""

    body_nums = extract_numbers(body)
    base_keys = set()
    for raw, _, _ in extract_numbers(base):
        k = as_key(raw)
        if k is not None:
            base_keys.add(k)

    print_header("正文数字清单与底表比对（SOP-5 第④步）")
    print(f"正文数字共 {len(body_nums)} 处")

    if base:
        missing = []
        for raw, ln, ctx in body_nums:
            k = as_key(raw)
            if k is None or k not in base_keys:
                missing.append((raw, ln, ctx))
        print(f"\n[正文有、底表无] {len(missing)} 处（需逐条判断：引用错误 / 非材料语境）")
        for raw, ln, ctx in missing:
            print(f"  第{ln}行 [{raw}] …{ctx}…")
        if not missing:
            print("  无")
        print("\n提示：年份、章节号、编号也符合“数字”，可能落在本清单里，属正常，逐条确认即可。")
        return 1 if missing else 0

    print("\n[全部数字清单]（未提供底表，仅供人工逐条对照）")
    for raw, ln, ctx in body_nums:
        print(f"  第{ln}行 [{raw}] …{ctx}…")
    return 0


# ---------- mats：【料N】抽取 ----------

def cmd_mats(args):
    text = read_text(args.body)
    found = {}
    for m in re.finditer(r"【料\s*(\d+(?:-\d+)?)】", text):
        found.setdefault(m.group(1), []).append(line_no(text, m.start()))

    print_header("【料N】抽取与计数（SOP-5 第①步）")
    print(f"共 {len(found)} 个材料号被引用：")
    for k in sorted(found, key=lambda s: (int(s.split('-')[0]), s)):
        print(f"  料{k}：{len(found[k])} 次（第 {', '.join(map(str, found[k]))} 行）")
    if not found:
        print("  未发现【料N】标记——检查正文是否漏标。")
    return 0


# ---------- marks：过程标记扫描 ----------

def cmd_marks(args):
    text = read_text(args.body)
    hits = list(MARK_RE.finditer(text))
    print_header("过程标记扫描（SOP-7 第一步）")
    if not hits:
        print("未发现【…】类标记，可以进入下一步。")
        return 0
    counts = {}
    for m in hits:
        counts[m.group(0)] = counts.get(m.group(0), 0) + 1
    print(f"发现 {len(hits)} 处标记：")
    for tok, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {tok} × {c}")
    print("\n逐处位置：")
    for m in hits:
        print(f"  第{line_no(text, m.start())}行：…{snippet(text, m.start())}…")
    print("\n提醒：删标记前确认内容是否已补齐；【待核】【待补出处】不能直接删。")
    return 1


# ---------- props：docx 文档属性 ----------

def cmd_props(args):
    try:
        from docx import Document
    except ImportError:
        print("[错误] 需要 python-docx：pip install python-docx", file=sys.stderr)
        return 2

    if not os.path.exists(args.docx):
        sys.exit(f"[错误] 找不到文件：{args.docx}")

    doc = Document(args.docx)
    cp = doc.core_properties
    fields = ["author", "last_modified_by", "title", "subject", "keywords", "comments", "category", "revision"]
    print_header("docx 文档属性" + ("（dry-run，不写入）" if args.dry_run else ""))
    for f in fields:
        print(f"  {f:16} = {getattr(cp, f, '')!r}")

    updates = {
        "author": args.author,
        "last_modified_by": args.author,
        "title": args.title,
    }
    updates = {k: v for k, v in updates.items() if v}
    if args.clear_meta:
        updates.update({"subject": "", "keywords": "", "comments": "", "category": ""})

    if not updates:
        extra = "（当前仅查看，未指定要改的字段）" if args.dry_run else ""
        print(f"\n未指定要改的字段：加 --author/--title/--clear-meta。{extra}")
        return 0

    print("\n将写入：")
    for k, v in updates.items():
        print(f"  {k} -> {v!r}")
    if args.dry_run:
        print("（dry-run 模式，未写入）")
        return 0

    for k, v in updates.items():
        setattr(cp, k, v)
    doc.save(args.docx)
    print(f"\n已保存：{args.docx}")
    print("提示：Word 打开后如仍显示旧作者，检查“文件→信息”与自定义属性；自定义属性本脚本不处理。")
    return 0


# ---------- punct：标点与字形归属 ----------

CJK = "\u4e00-\u9fff"
HALF_BETWEEN_CJK = re.compile(r"(?<=[%s])[,;:?!()](?=[%s])" % (CJK, CJK))
FENCE_RE = re.compile(r"```.*?```", re.S)
INLINE_RE = re.compile(r"`[^`\n]*`")


def mask_code(text):
    """把代码块与行内代码抹成等长空格，保留换行，使行号不变。"""
    def blank(m):
        return "".join("\n" if ch == "\n" else " " for ch in m.group(0))
    return INLINE_RE.sub(blank, FENCE_RE.sub(blank, text))


def text_quote_stats(text):
    ascii_d = [m.start() for m in re.finditer(r'"', text)]
    ascii_s = [m.start() for m in re.finditer(r"'", text)]
    half = [(m.start(), m.group(0)) for m in HALF_BETWEEN_CJK.finditer(text)]
    oc = (text.count("\u201c"), text.count("\u201d"), text.count("\u2018"), text.count("\u2019"))
    return ascii_d, ascii_s, half, oc


def report_text_layer(text, limit, offset_note=""):
    ascii_d, ascii_s, half, oc = text_quote_stats(text)
    print(f"\n[字符层]")
    print(f'  ASCII 双引号 " ：{len(ascii_d)} 处')
    for pos in ascii_d[:limit]:
        print(f"    第{line_no(text, pos)}行：…{snippet(text, pos)}…")
    print(f"  ASCII 单引号 ' ：{len(ascii_s)} 处")
    for pos in ascii_s[:limit]:
        print(f"    第{line_no(text, pos)}行：…{snippet(text, pos)}…")
    print(f"  半角标点夹在汉字之间：{len(half)} 处")
    for pos, ch in half[:limit]:
        print(f"    第{line_no(text, pos)}行 [{ch}]：…{snippet(text, pos)}…")
    print(f"\n[开合] “{oc[0]} / ”{oc[1]} ｜ ‘{oc[2]} / ’{oc[3]}")
    unbalanced = (oc[0] != oc[1]) or (oc[2] != oc[3])
    if unbalanced:
        print("  不平衡：先修引号，再谈其他")
    return len(ascii_d) + len(ascii_s) + len(half) + (1 if unbalanced else 0)


def cmd_punct(args):
    ext = os.path.splitext(args.file)[1].lower()
    print_header("标点与字形归属检查（SOP-7 第二步）")
    total = 0

    if ext == ".docx":
        try:
            from docx import Document
            from docx.oxml.ns import qn
        except ImportError:
            print("[错误] 需要 python-docx：pip install python-docx", file=sys.stderr)
            return 2
        if not os.path.exists(args.file):
            sys.exit(f"[错误] 找不到文件：{args.file}")
        doc = Document(args.file)

        parts = []
        for p in doc.paragraphs:
            parts.append(p)
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    parts.extend(cell.paragraphs)

        text = "\n".join(p.text for p in parts)
        total += report_text_layer(text, args.limit)

        cjk_runs = no_hint = 0
        punct_no_hint = 0
        for p in parts:
            for r in p.runs:
                if not any("\u4e00" <= c <= "\u9fff" for c in r.text):
                    continue
                cjk_runs += 1
                rpr = r._r.rPr
                rf = rpr.find(qn("w:rFonts")) if rpr is not None else None
                if rf is None or rf.get(qn("w:hint")) != "eastAsia":
                    no_hint += 1
                    if any(ch in r.text for ch in "\u201c\u201d\u2018\u2019\u2014\u2026"):
                        punct_no_hint += 1
        print(f"\n[字形层] 含中文的 run：{cjk_runs} 个")
        print(f'  缺 w:hint="eastAsia"：{no_hint} 个（其中含引号/破折号/省略号的 {punct_no_hint} 个）')
        if no_hint:
            print("  说明：这类 run 里的“”——… 会按西文字体排，占位偏窄，看起来像没改。")
        total += no_hint
    else:
        text = mask_code(read_text(args.file))
        total += report_text_layer(text, args.limit)

    print(f"\n结论：{'发现 %d 处问题，需处理' % total if total else '未发现问题'}")
    print("提示：先在源文件（.md / 生成脚本）里改，再重新导出 docx；在 docx 里手改会把问题留在源里。")
    return 1 if total else 0


# ---------- 入口 ----------

def main():
    parser = argparse.ArgumentParser(
        description="中文论文校对脚本：标号映射 / 数字比对 / 材料抽取 / 标记扫描 / docx 属性清理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("refs", help="引用标号双向映射（SOP-6 第二步）")
    p.add_argument("body", help="正文文件（.md/.txt）")
    p.add_argument("refs", help="文末参考文献文件（.md/.txt）")
    p.set_defaults(func=cmd_refs)

    p = sub.add_parser("numbers", help="正文数字清单与底表比对（SOP-5 第④步）")
    p.add_argument("body", help="正文文件")
    p.add_argument("base", nargs="?", default="", help="资料表/底表文件（可选）")
    p.set_defaults(func=cmd_numbers)

    p = sub.add_parser("mats", help="【料N】抽取与计数（SOP-5 第①步）")
    p.add_argument("body", help="正文文件")
    p.set_defaults(func=cmd_mats)

    p = sub.add_parser("marks", help="【…】过程标记扫描（SOP-7 第一步）")
    p.add_argument("body", help="正文文件")
    p.set_defaults(func=cmd_marks)

    p = sub.add_parser("props", help="清理 docx 文档属性（SOP-7 第二步）")
    p.add_argument("docx", help=".docx 文件")
    p.add_argument("--author", default="", help="作者 / 最后修改者")
    p.add_argument("--title", default="", help="标题")
    p.add_argument("--clear-meta", action="store_true", help="清空 subject/keywords/comments/category")
    p.add_argument("--dry-run", action="store_true", help="只显示，不写入")
    p.set_defaults(func=cmd_props)

    p = sub.add_parser("punct", help="标点与字形归属检查（SOP-7 第二步）")
    p.add_argument("file", help=".docx 或 .md/.txt")
    p.add_argument("--limit", type=int, default=10, help="每类最多列出多少处（默认 10）")
    p.set_defaults(func=cmd_punct)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
