# -*- coding: utf-8 -*-
"""check_terms.py —— 术语、禁用词、拼写检查
用法：python check_terms.py [输入目录] [输出目录]
术语表：terminology.csv（中文,英文,类型,禁用写法,允许次数）
  · 禁用写法多个用 | 分隔
  · 允许次数：正文里最多允许出现几次（"受限允许"用；默认 0）
  · 文献表（References 之后）里的命中不计入失败，只提示
"""
import csv
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

# 美式拼写检查的误报词
ALLOW = {"size", "sizes", "sized", "prize", "prizes", "seize", "seized",
         "capsize", "maize", "denizen", "citizen", "citizens"}


def read_any(p):
    """读 md / txt / docx。docx 用标准库解压，无需安装 python-docx。"""
    if p.suffix.lower() == ".docx":
        import zipfile
        import html as _html
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        xml = xml.replace("</w:p>", "\n").replace("</w:tr>", "\n").replace("</w:tc>", " ")
        return _html.unescape(re.sub(r"<[^>]+>", "", xml))
    return p.read_text(encoding="utf-8-sig", errors="replace")


def load_terms():
    p = ROOT / "terminology.csv"
    rows = []
    if not p.exists():
        return rows
    with p.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                allow = int((row.get("允许次数") or "0").strip() or 0)
            except ValueError:
                allow = 0
            rows.append({
                "zh": (row.get("中文") or "").strip(),
                "en": (row.get("英文") or "").strip(),
                "type": (row.get("类型") or "").strip(),
                "banned": [x.strip() for x in (row.get("禁用写法") or "").split("|") if x.strip()],
                "allow": allow,
            })
    return rows


def ref_start_line(lines):
    for i, l in enumerate(lines):
        s = l.strip().strip("#").strip()
        if re.fullmatch(r"(references|bibliography|参考文献)", s, re.I):
            return i
    return len(lines)


def findings(text, term_rows):
    lines = text.splitlines()
    ref_at = ref_start_line(lines)

    banned = []          # (line_no, term, snippet, in_refs)
    en_counts, zh_counts = {}, {}

    for row in term_rows:
        if row["en"]:
            en_counts[row["en"]] = len(re.findall(re.escape(row["en"]), text, re.I))
        if row["zh"]:
            zh_counts[row["zh"]] = text.count(row["zh"])
        for b in row["banned"]:
            for i, line in enumerate(lines, 1):
                if re.search(re.escape(b), line, re.I):
                    banned.append((i, b, line.strip()[:90], (i - 1) >= ref_at))

    american = []
    for i, line in enumerate(lines, 1):
        if (i - 1) >= ref_at:
            continue
        for m in re.finditer(r"\b[A-Za-z][A-Za-z\-]*iz(?:e|es|ed|ing|ation)\b", line):
            w = m.group(0)
            segs = re.split(r"[-–]", w.lower())
            if w.lower() in ALLOW or segs[-1] in ALLOW:
                continue
            american.append((i, w, line.strip()[:90]))
    return banned, american, en_counts, zh_counts, ref_at


def main():
    inp = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input"
    outp = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "output"
    outp.mkdir(parents=True, exist_ok=True)
    terms = load_terms()
    files = sorted(list(inp.glob("*.md")) + list(inp.glob("*.txt")) + list(inp.glob("*.docx")))
    files = [f for f in files if not f.name.lower().startswith(("readme", "_", "~$"))]
    if not files:
        print("找不到稿件。请把 .md / .txt / .docx 放进：%s" % inp)
        return 2
    if not terms:
        print("找不到 terminology.csv（或为空）。请放在：%s" % (ROOT / "terminology.csv"))
        return 2

    all_ok = True
    for f in files:
        text = read_any(f)
        banned, american, en, zh, ref_at = findings(text, terms)

        body_banned = [b for b in banned if not b[3]]
        ref_banned = [b for b in banned if b[3]]

        # 受限允许：按词统计正文命中，超过允许次数才算失败
        over = []
        for row in terms:
            for b in row["banned"]:
                n = sum(1 for x in body_banned if x[1] == b)
                if n > row["allow"]:
                    over.append((b, n, row["allow"]))

        ok = (len(over) == 0 and len(american) == 0)
        all_ok = all_ok and ok

        rep = ["# 术语检查报告", "", "文件：`%s`" % f.name, "",
               "## 1 禁用写法（正文）", ""]
        if body_banned:
            rep += ["| 行 | 命中 | 原文 |", "|---|---|---|"]
            rep += ["| %d | %s | %s |" % (i, b, t) for i, b, t, _ in body_banned[:50]]
        else:
            rep.append("无。")

        if over:
            rep += ["", "超限项：", ""]
            rep += ["- `%s` 正文 %d 次（允许 %d）" % (b, n, a) for b, n, a in over]

        if ref_banned:
            rep += ["", "## 2 文献表中的命中（不算失败，保留原文）", ""]
            rep += ["| 行 | 命中 | 原文 |", "|---|---|---|"]
            rep += ["| %d | %s | %s |" % (i, b, t) for i, b, t, _ in ref_banned[:20]]

        rep += ["", "## 3 美式拼写（正文）：%d" % len(american), ""]
        if american:
            rep += ["| 行 | 命中 | 原文 |", "|---|---|---|"]
            rep += ["| %d | %s | %s |" % (i, w, t) for i, w, t in american[:50]]
            rep += ["", "> 他人论文标题/引文中的异体拼写应保留，逐条人工放行。"]
        else:
            rep.append("无。")

        rep += ["", "## 4 术语出现次数", "",
                "| 中文 | 英文 | 中文次数 | 英文次数 | 提示 |", "|---|---|---|---|---|"]
        for row in terms:
            z = zh.get(row["zh"], 0)
            e = en.get(row["en"], 0)
            tip = "中文还在，英文未出现" if (z > 0 and e == 0) else ""
            rep.append("| %s | %s | %d | %d | %s |" % (row["zh"], row["en"], z, e, tip))

        rep += ["", "**%s**" % ("PASS" if ok else "FAIL"), ""]
        (outp / ("report_terms_%s.md" % f.stem)).write_text("\n".join(rep), encoding="utf-8")
        print("\n".join(rep))

    print("\n==== 汇总：%s ====" % ("全部 PASS" if all_ok else "有 FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
