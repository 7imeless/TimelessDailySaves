# 个人账本

入口 `/money`，登录后使用。人民币、单账本、手动录入；共用原有账号。首页提供“记账”入口。

- 新增、编辑、删除收入和支出；分类按收入/支出区分。
- 日期、金额、分类必填，备注最多 300 字。
- 金额存为整数分，只接受大于零且小于 1 亿元的金额，最多两位小数。
- 月份与分类筛选、每页 30 条明细。
- 月度收入、支出、结余、支出分类比例始终统计整月；分类筛选仅作用于明细及 CSV 导出。
- CSV 导出包含筛选结果的全部记录，UTF-8 BOM，备注公式前缀转义。
- 每个请求都校验登录用户归属；写入要求 CSRF。删除账号时同步删除账本记录。
- 数据保存在现有 `timeless.db` 的 `money_entries` 表，服务启动自动建表；备份博客数据库也会备份账本。
- 不包含银行卡连接、自动对账、支付账户余额、多币种或预算。

检查：`python -m py_compile app.py money.py`、`node --check money.js`、`python -W ignore::ResourceWarning -m unittest discover -s tests -p test_money.py`、`git diff --check`。

测试使用临时数据库和本机临时端口，覆盖实际登录、增删改、账号隔离、CSRF、金额校验、月份/分类范围、错误表单保留、CSV 及备注转义。ResourceWarning 来自项目既有 SQLite 连接上下文用法；测试结束执行 GC 释放临时数据库句柄。
