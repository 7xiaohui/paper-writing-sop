# -*- coding: utf-8 -*-
"""check_counts.py —— 字数与摘要检查
用法：python check_counts.py [输入目录] [输出目录]
默认：输入 ../input，输出 ../output
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent


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


def normalize(text):
    """把 docx 里的 Abstract / References 变成 markdown 标题，便于切节。"""
    text = re.sub(r"(?im)^[ \t]*(abstract|摘要)[ \t]*[:：]?[ \t]*",
                  lambda m: "\n## " + m.group(1) + "\n", text, count=1)
    text = re.sub(r"(?im)^[ \t]*(references|参考文献)[ \t]*[:：]?[ \t]*$",
                  lambda m: "\n## " + m.group(1) + "\n", text, count=1)
    return text


def read_cfg():
    cfg = {"target_words": "8000", "max_words": "8400",
           "abstract_max": "200", "keywords_min": "3", "keywords_max": "6"}
    p = ROOT / "config.txt"
    if p.exists():
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def sections(text):
    head = re.compile(r"^(#{1,6})\s*(.+?)\s*$", re.M)
    marks = [(m.start(), m.end(), len(m.group(1)), m.group(2)) for m in head.finditer(text)]
    out = []
    for i, (s, e, lvl, title) in enumerate(marks):
        nxt = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out.append((lvl, title, text[e:nxt]))
    return out


def count_words(s):
    return len(re.findall(r"[A-Za-z][A-Za-z'’\-]*", s))


def count_han(s):
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def find_abstract(secs):
    for _, title, body in secs:
        t = title.lower()
        if "abstract" in t or "摘要" in t:
            m = re.search(r"(?im)^[ \t]*\*{0,2}(keywords|key words|关键词)\b.*$", body)
            if m:
                body = body[:m.start()]
            return title, body
    return None, ""


def find_refs_index(secs):
    for i, (_, title, _) in enumerate(secs):
        t = title.lower()
        if "reference" in t or "参考文献" in t:
            return i
    return len(secs)


def find_keywords(text):
    for line in text.splitlines():
        s = line.strip().strip("*# ")
        low = s.lower()
        if low.startswith("keywords") or low.startswith("key words") or s.startswith("关键词"):
            body = s.split(":", 1)[-1] if ":" in s else s.split("：", 1)[-1]
            items = [x for x in re.split(r"[;,；，]", body) if x.strip()]
            return len(items), body.strip()
    return 0, ""


def main():
    inp = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input"
    outp = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "output"
    outp.mkdir(parents=True, exist_ok=True)
    cfg = read_cfg()

    files = sorted(list(inp.glob("*.md")) + list(inp.glob("*.txt")) + list(inp.glob("*.docx")))
    files = [f for f in files if not f.name.lower().startswith(("readme", "_", "~$"))]
    if not files:
        print("找不到稿件。请把 .md 或 .txt 放进：%s" % inp)
        return 2

    all_ok = True
    for f in files:
        checks, infos = [], []
        text = normalize(read_any(f))
        secs = sections(text)
        refs_at = find_refs_index(secs)
        body = "".join(b for _, _, b in secs[:refs_at])
        _, abs_body = find_abstract(secs)
        kw_n, kw_raw = find_keywords(text)

        abs_words = count_words(abs_body)
        body_words = max(0, count_words(body) - abs_words)
        han = count_han(text)

        infos.append((f.name, abs_words, kw_n, body_words, han))

        checks.append(("摘要词数 <= %s" % cfg["abstract_max"], abs_words <= int(cfg["abstract_max"]),
                       "实际 %d 词" % abs_words))
        checks.append(("关键词 %s–%s 个" % (cfg["keywords_min"], cfg["keywords_max"]),
                       int(cfg["keywords_min"]) <= kw_n <= int(cfg["keywords_max"]),
                       "实际 %d 个：%s" % (kw_n, kw_raw or "（未找到 Keywords 行）")))
        checks.append(("正文词数 <= %s" % cfg["max_words"], body_words <= int(cfg["max_words"]),
                       "实际 %d 词（目标 %s）" % (body_words, cfg["target_words"])))

        report = ["# 字数检查报告", "", "文件：`%s`" % f.name, "",
                  "| 项 | 数值 |", "|---|---|",
                  "| 摘要词数 | %d |" % abs_words,
                  "| 关键词数 | %d |" % kw_n,
                  "| 正文词数（不含参考文献） | %d |" % body_words,
                  "| 全文中文字符 | %d |" % han, "",
                  "## 结论", "", "| 检查 | 结果 | 详情 |", "|---|---|---|"]
        for name, ok, detail in checks:
            report.append("| %s | %s | %s |" % (name, "PASS" if ok else "**FAIL**", detail))
        passed = sum(1 for _, ok, _ in checks if ok)
        report += ["", "**%s %d/%d**" % ("PASS" if passed == len(checks) else "FAIL", passed, len(checks)), ""]
        (outp / ("report_counts_%s.md" % f.stem)).write_text("\n".join(report), encoding="utf-8")

        print("\n".join(report))
        all_ok = all_ok and passed == len(checks)

    print("\n==== 汇总：%s ====" % ("全部 PASS" if all_ok else "有 FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
