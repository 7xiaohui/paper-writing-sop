# -*- coding: utf-8 -*-
"""check_clean.py —— 净化检查（交稿前两查之一）
查六类工作痕迹 + 三样外观问题：
  1 待定/中间态  2 内部工作语  3 投稿策略  4 版本尾注  5 回迁过程语  6 审稿痕迹
  7 占位符  8 整段加粗  9 假脚注
用法：python check_clean.py [输入目录] [输出目录]
可在 config.txt 里加一行 meta_words=目标刊缩写,项目代号 来查"不许出现的刊名/项目名"。
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

PROCESS = [
    ("待定/中间态", r"回填|待补|待核|待定|待确认|待复核|\bTBD\b|\bXXX\b|未完成|存疑"),
    ("内部工作语", r"本稿暂|另列|以便核对|供核对|供内部|团队内部|投稿时删除"),
    ("投稿策略", r"主攻|备选刊|保底|冲刺"),
    ("版本尾注", r"版本\s*[:：]|(?<![A-Za-z])v\d+\.\d+"),
    ("回迁/编辑过程语", r"已按要求回迁|原附录.{0,8}撤销"),
    ("审稿痕迹", r"审稿人模拟|意见已落地|第[一二三四五六七八九十\d]+批"),
]
PLACEHOLDER = r"_{4,}|【\s*】|\[待|待填"
PSEUDO_FOOTNOTE = r"^\s*(?:>\s*)?\*{0,2}脚注\s*\d*\s*[:：]|^\s*\*{0,2}Note\s+\d+\s*[（(:：]"


def read_cfg():
    cfg = {}
    p = ROOT / "config.txt"
    if p.exists():
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def read_text(p):
    if p.suffix.lower() == ".docx":
        import zipfile
        import html as _html
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        xml = xml.replace("</w:p>", "\n").replace("</w:tr>", "\n").replace("</w:tc>", " ")
        return _html.unescape(re.sub(r"<[^>]+>", "", xml))
    return p.read_text(encoding="utf-8-sig", errors="replace")


def bold_paragraphs(p):
    """返回疑似整段加粗的段落（md 精确；docx 近似）"""
    out = []
    if p.suffix.lower() == ".docx":
        import zipfile
        import html as _html
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        for para in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
            runs = [r for r in re.findall(r"<w:r[ >].*?</w:r>", para, re.S) if "<w:t" in r]
            if not runs:
                continue
            txt = _html.unescape(re.sub(r"<[^>]+>", "", para)).strip()
            # 标题/小标题不是句子（没有 ". "），不算"整段加粗"
            if len(txt) < 120 or ". " not in txt:
                continue
            bold = [r for r in runs if re.search(r"<w:b\s*/>|<w:b\s+w:val=\"(?:1|true|on)\"", r)]
            if len(bold) == len(runs):
                out.append(txt[:70] + "…")
        return out
    for line in read_text(p).splitlines():
        s = line.strip()
        if len(s) > 80 and s.startswith("**") and s.endswith("**"):
            out.append(s[:70] + "…")
    return out


def main():
    inp = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input"
    outp = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "output"
    outp.mkdir(parents=True, exist_ok=True)
    cfg = read_cfg()
    meta = [w.strip() for w in (cfg.get("meta_words") or "").split(",") if w.strip()]

    files = sorted(list(inp.glob("*.md")) + list(inp.glob("*.txt")) + list(inp.glob("*.docx")))
    files = [f for f in files if not f.name.lower().startswith(("readme", "_", "~$"))]
    if not files:
        print("找不到稿件。请把 .md / .txt / .docx 放进：%s" % inp)
        return 2

    all_ok = True
    for f in files:
        text = read_text(f)
        lines = text.splitlines()

        hits = []          # (类别, 行号, 原文)
        counts = {}
        for label, pat in PROCESS:
            for i, line in enumerate(lines, 1):
                if re.search(pat, line):
                    hits.append((label, i, line.strip()[:90]))
                    counts[label] = counts.get(label, 0) + 1
        ph = [(i, l.strip()[:90]) for i, l in enumerate(lines, 1) if re.search(PLACEHOLDER, l)]
        fn = [(i, l.strip()[:90]) for i, l in enumerate(lines, 1) if re.search(PSEUDO_FOOTNOTE, l, re.I)]
        bold = bold_paragraphs(f)
        meta_hits = []
        for w in meta:
            for i, line in enumerate(lines, 1):
                if re.search(re.escape(w), line):
                    meta_hits.append((w, i, line.strip()[:90]))

        ok = (not hits) and (not ph) and (not bold)
        all_ok = all_ok and ok

        rep = ["# 净化检查报告", "", "文件：`%s`" % f.name, "",
               "## 1 工作痕迹", ""]
        if hits:
            rep += ["| 类别 | 行 | 原文 |", "|---|---|---|"]
            rep += ["| %s | %d | %s |" % h for h in hits[:60]]
        else:
            rep.append("无。")

        rep += ["", "## 2 占位符：%d" % len(ph), ""]
        rep += (["- 第 %d 行：%s" % x for x in ph[:30]] or ["无。"])

        rep += ["", "## 3 整段加粗：%d" % len(bold), ""]
        if bold:
            rep.append("> %s" % ("docx 为近似判断：长段落中含加粗即计入，请人工确认" if f.suffix.lower() == ".docx" else "整行加粗"))
            rep += (["- " + b for b in bold[:20]] or ["无。"])
        else:
            rep.append("无。")

        rep += ["", "## 4 假脚注（用正文/引用块模拟）：%d" % len(fn), ""]
        rep += (["- 第 %d 行：%s" % x for x in fn[:10]] or ["无。"])

        if meta:
            rep += ["", "## 5 刊名/项目名残留：%d" % len(meta_hits), ""]
            rep += ([ "- %s（第 %d 行）：%s" % x for x in meta_hits[:20]] or ["无。"])

        rep += ["", "**%s**" % ("PASS" if ok else "FAIL"), ""]
        (outp / ("report_clean_%s.md" % f.stem)).write_text("\n".join(rep), encoding="utf-8")
        print("\n".join(rep))

    print("\n==== 汇总：%s ====" % ("全部 PASS" if all_ok else "有 FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
