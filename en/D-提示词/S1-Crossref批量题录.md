# S1 专卡 · Crossref 批量题录

来源：`03-定刊.md` 第四节、四·补。什么时候用：第 3 步，按 ISSN 拉题录。
前置条件：目标刊 online ISSN（先在官网核对刊名）。
人必须确认：ISSN 是否正确、题名人工过的结果。


```text
任务：按 ISSN 拉近两年题录。
URL 模板：
https://api.crossref.org/journals/{ISSN}/works?filter=from-pub-date:YYYY-01-01&rows=100&select=DOI,title,published,abstract&cursor=*
要点：
- ISSN 用 online ISSN；
- total-results 只看规模，不当同题数；
- 书评 / 综述 / 编辑按排除；
- 翻页用 next-cursor，不用 offset。
输出：题名列表 + 排除项 + 计数。
```

**使用提醒**：`total-results` 只看规模；书评 / 综述 / 社论排除；翻页用 `next-cursor` 不用 `offset`。四源分级与留证见 `S6`。
