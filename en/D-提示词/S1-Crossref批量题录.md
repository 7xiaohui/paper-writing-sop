# S1 专卡 · Crossref 批量题录

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

*配合 D3 用：S1 负责拉，D3 负责筛*
