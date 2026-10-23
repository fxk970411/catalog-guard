# 发布到 GitHub

当前交付是本地源码初版，尚未创建远程仓库、发布版本或提交任何资助申请。

## 检查并上传

1. 阅读 README，运行示例和全部测试。检查文件内容，确认没有私密数据。
2. 在 GitHub 新建名为 `catalog-guard` 的空仓库；若名称已占用可换名。选择 Public；不要让 GitHub 再创建 README 或许可证。
3. 推荐使用 GitHub Desktop：添加本地项目目录为仓库，检查全部变更，提交初始版本，然后 Publish repository 并取消 Private。也可以用下列命令；将 URL 替换成你自己的真实仓库地址：

```sh
git init -b main
git add .
git commit -m "Initial Catalog Guard implementation"
git remote add origin https://github.com/YOUR_USERNAME/catalog-guard.git
git push -u origin main
```

`YOUR_USERNAME` 是必须替换的占位符。不要直接上传 ZIP 文件作为仓库内容；上传解压后的文件，包含隐藏的 `.github` 文件夹。不要包含虚拟环境或缓存。

4. 查看 Actions，等全部平台任务通过。当前提供的是 CI 配置，不是已完成的远程测试记录。
5. 在仓库设置中启用 private vulnerability reporting；设置议题模板、描述、Topics。建议描述：`Offline quality gates for CSV/JSON catalogs, verification metadata, and snapshot changes.`
6. 用 `v0.1.0` 标签创建 Release，记录功能和已知限制；实际发布后再更新 CHANGELOG 的发布状态及日期。

## 集成到目录发布流水线

在目录仓库中先取得本工具，例如将审核后的源码放入 `tools/catalog-guard/`。在工作流的部署步骤之前添加：

```yaml
- name: Check catalog before publishing
  working-directory: tools/catalog-guard
  run: python -m catalog_guard ../../data/current.json --config ../../rules.json --baseline ../../data/previous.json --strict
```

前提是目录仓库已有上述两个快照和规则，且 Python 3.10+ 可用。首次发布可省略 `--baseline`。不要加 `continue-on-error: true`。同一 job 中后续部署步骤保持默认成功条件，不要使用 `if: always()`；跨 job 发布则必须声明依赖检查 job 并仅在成功时运行。保留上一版成功发布的数据作为 baseline，检查前不要覆盖它。

## 后续发布

每次修复先加入最小复现测试，更新版本号（`pyproject.toml` 和 `catalog_guard/__init__.py`）、CHANGELOG 与说明。测试通过后打新标签。当前没有自动发布到 PyPI；包名需先确认可用性，不能把本地安装当成已公开发行。
