#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复跑两条产线的正负样本验证。

在仓库根目录执行：

    python tests/verify.py

它做两件事：
  1. 英文线：把 samples/good.md 与 bad.md 分别喂给五个检查脚本，
     断言 good 全部通过、bad 能抓出问题；
  2. 中文线：用 fixtures/zh 下的干净样本与脏样本，断言 refs / marks / punct
     在干净样本上零命中、在脏样本上能报出问题。

退出码：0 全部通过；1 有失败；2 环境错误。

它只依赖 Python 标准库，不需要安装任何包。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PY = sys.executable

EN_TOOLS = ROOT / "en" / "工具"
EN_SCRIPTS = EN_TOOLS / "scripts"
EN_SAMPLES = EN_TOOLS / "samples"
ZH_SCRIPT = ROOT / "zh" / "工具" / "核对脚本.py"
ZH_FIXTURES = HERE / "fixtures" / "zh"

EN_CHECKS = [
    "check_counts.py",
    "check_terms.py",
    "check_refs.py",
    "check_consistency.py",
    "check_clean.py",
]

ENV = dict(os.environ)
ENV["PYTHONIOENCODING"] = "utf-8"
ENV["PYTHONUTF8"] = "1"

results: list[tuple[str, bool, str]] = []


def run(args: list[object]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, *[str(a) for a in args]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ENV,
    )


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(("  PASS  " if ok else "  FAIL  ") + name + ("" if ok else "  <- " + detail))


def tail(text: str, n: int = 240) -> str:
    text = " ".join(text.split())
    return text[-n:]


# ---------- 英文线 ----------

def verify_en() -> None:
    print("\n[英文线] 五个脚本 × 正负样本")
    if not EN_SCRIPTS.exists():
        check("en/工具/scripts 存在", False, str(EN_SCRIPTS))
        return

    for script in EN_CHECKS:
        for sample, expected in (("good.md", 0), ("bad.md", 1)):
            with tempfile.TemporaryDirectory(prefix="sop_en_") as td:
                inp = Path(td) / "in"
                out = Path(td) / "out"
                inp.mkdir()
                shutil.copy(EN_SAMPLES / sample, inp / sample)
                proc = run([EN_SCRIPTS / script, inp, out])
                ok = proc.returncode == expected
                detail = "期望 exit %d，实际 %d：%s" % (
                    expected, proc.returncode, tail(proc.stdout or proc.stderr))
                check("en/%s <- %s" % (script, sample), ok, detail)


# ---------- 中文线 ----------

def verify_zh() -> None:
    print("\n[中文线] refs / marks / punct × 干净样本与脏样本")
    if not ZH_SCRIPT.exists():
        check("zh/工具/核对脚本.py 存在", False, str(ZH_SCRIPT))
        return

    clean = ZH_FIXTURES / "clean.md"
    dirty = ZH_FIXTURES / "dirty.md"
    refs = ZH_FIXTURES / "refs.txt"

    cases = [
        ("refs 干净样本", ["refs", clean, refs], 0),
        ("refs 脏样本（悬空/冗余）", ["refs", dirty, refs], 1),
        ("marks 干净样本", ["marks", clean], 0),
        ("marks 脏样本（残留标记）", ["marks", dirty], 1),
        ("punct 干净样本", ["punct", clean], 0),
        ("punct 脏样本（ASCII 引号）", ["punct", dirty], 1),
    ]
    for name, args, expected in cases:
        proc = run([ZH_SCRIPT, *args])
        ok = proc.returncode == expected
        detail = "期望 exit %d，实际 %d：%s" % (
            expected, proc.returncode, tail(proc.stdout or proc.stderr))
        check("zh/%s" % name, ok, detail)


def main() -> int:
    print("=" * 60)
    print(" 论文写作 SOP · 样本验证")
    print(" 仓库：%s" % ROOT)
    print(" Python：%s" % sys.version.split()[0])
    print("=" * 60)

    for path in (EN_SCRIPTS, EN_SAMPLES, ZH_SCRIPT, ZH_FIXTURES):
        if not path.exists():
            print("[错误] 找不到：%s" % path)
            return 2

    verify_en()
    verify_zh()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    failed = total - passed

    print("\n" + "=" * 60)
    if failed:
        print("==== 失败 %d/%d ====" % (failed, total))
        for name, ok, detail in results:
            if not ok:
                print("  - %s：%s" % (name, detail))
        return 1

    en_total = len(EN_CHECKS) * 2
    zh_total = total - en_total
    print("==== 全部通过：英文线 %d/%d，中文线 %d/%d ====" % (
        en_total, en_total, zh_total, zh_total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
