# Catalog Guard：数据目录发布前检查

适合维护公共资源、门店、图书馆等 CSV / JSON 目录的人。更新脚本运行成功，不代表生成的数据正确；本工具在发布前检查重复记录、字段缺失、验证状态冲突和大量记录消失。

## 马上运行

需要 Python 3.10 或以上。打开终端，进入解压后的项目目录：

```sh
python3 -m catalog_guard examples/good.csv --config examples/rules.json --today 2026-10-23
```

应显示 2 条记录、0 个错误、0 个警告。示例日期固定是为了以后仍可复现；检查自己的数据时移除 `--today`，按当天检查。

```sh
python3 -m catalog_guard examples/broken.json --config examples/rules.json --today 2026-10-23
```

这份故意出错的示例应失败，显示 5 个错误和 1 个警告。它演示“仍有 HTTP 402 错误，却标为 verified”等问题。

生成可双击查看的报告：

```sh
python3 -m catalog_guard examples/good.csv --config examples/rules.json --today 2026-10-23 --format html --output report.html
```

已有报告不会被覆盖，请删除旧报告或换新文件名后重跑。

## 换成你的数据

1. 复制 `examples/rules.json`，把字段名改为你的导出文件对应字段。
2. 每条记录必须有稳定、唯一的字符串 ID；邮编等有前导零的字段也建议保持字符串。
3. 运行时把示例文件路径换成你的数据路径。
4. 加 `--baseline 上次数据.json` 比较增删和字段变化；阈值在配置里修改。
5. 修复问题后重新运行，再发布数据。

退出码 0 表示通过，1 表示检查发现问题，2 表示文件或配置不能处理。陈旧数据默认只警告，加 `--strict` 后也阻止通过。程序不上传文件、不调用收费 API、不修改源数据。

“检查通过”只代表满足你配置的规则，不代表地址真实、网址可访问或验证证据可信。示例都是虚构数据。当前版本是可运行初版，真实用户和采用量仍需后续建立。

完整配置见 [RULES.md](RULES.md)，上传方法见 [RELEASE.md](RELEASE.md)，参与开发见 [CONTRIBUTING.md](../CONTRIBUTING.md)。
