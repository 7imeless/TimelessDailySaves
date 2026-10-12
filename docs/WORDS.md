# 英语词库与部署可行性

评估日期：2026-10-12（Asia/Hong_Kong）。

## 当前成果

`data/english-core.json` 是 ECDICT 的高频基础子集，目标 2,000 条。筛选小写英文词条且含中文释义，优先按 frq 排序，缺失时使用 bnc。它不是 CEFR 分级词表，也不是经过人工校对的 2,000 个词族；屈折变化可能独立出现，释义可能含过时或不常用的义项。

保留音标、英文定义、中文释义、考试标签、词频来源和词形变化。未提供例句或音频，也不生成未经验证的等级。数据文件记录源 CSV 的 SHA-256，许可证原文保存在 `data/ECDICT-LICENSE.txt`。

来源：https://github.com/skywind3000/ECDICT 。上游仓库声明 MIT；README 描述了混合资料来源，因此该声明不等同于逐项核实所有第三方内容权利。正式扩展内容时仍需记录更细的来源和质量审核。

## 导入

```bash
python tools/build_word_library.py
```

默认读取 JSON，写入独立 `words.db`。不会修改博客 `timeless.db`。重复执行会替换词典表；用户学习状态必须存入另一张业务表/数据库，不能放在该生成库中。

重新筛选本地 ECDICT CSV：

```bash
python tools/build_word_library.py --csv /path/to/ecdict.csv --limit 2000
```

当前阶段仅建立词库基础，还没有学习页面、公共接口、账号同步或复习调度。

## TypeWords 复用方向

https://github.com/zyronon/TypeWords/tree/master

实际核对的 package.json 使用 Nuxt 4、Vue 3、Pinia、idb-keyval 与 ts-fsrs，提供 `nuxt generate`。nuxt.config.ts 支持 `NUXT_APP_BASE_URL`，可考虑挂载 `/words/`。README 提示考试词库仅官方网站提供，不能把开源代码与官网数据视为一份可移植包。

推荐下一阶段先验证 TypeWords 静态构建及自定义词库导入，复用它的练习界面；用现有 Python/SQLite 接入账号和学习记录。其 GPL-3.0 声明需要随实际复用代码保留，并检查文件及依赖许可。FSRS 优先复用独立库，避免重写成熟调度算法。尚未实际构建 TypeWords，不能保证所有官网功能离线可用；需核对音频、翻译、云服务和资源路径。

## 服务器评估

用户配置：2 核 CPU、2 GiB 内存、40 GiB 系统盘。实际 `free -m` 可见总内存 1,613 MiB、available 1,140 MiB、无 swap；系统盘剩余约 35 GiB。现有博客 systemd 内存计数约 70 MiB。

结论：词典查询、个人学习记录和静态练习界面适合此配置。使用索引和分页查询，不把完整词库载入每次请求。静态前端构建安排在本地，服务器只交付生成文件；无需常驻 Node 或新增数据库服务。

容量预估：2,000 条词典通常为数 MiB，数万条词典和个人复习记录通常仍为数十至数百 MiB；实际以生成文件大小为准。音频应按需加载，避免预下载整库。CPU/RAM 可行性不等于并发能力保证，公开多用户上线前再进行负载测试。
