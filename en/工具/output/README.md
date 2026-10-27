# output：报告输出

脚本运行时把五份报告写在这里：

- `report_counts_<稿名>.md`
- `report_terms_<稿名>.md`
- `report_refs_<稿名>.md`
- `report_consistency_<稿名>.md`
- `report_clean_<稿名>.md`
- `run_log.txt`（整次运行的日志）

每份报告最后一行是 `PASS n/n` 或 `FAIL n/n`，看这一行就够了。

**本目录内容不入库**（`.gitignore` 已排除），可以随时清空重跑。
