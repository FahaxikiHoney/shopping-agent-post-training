# GitHub 首次公开发布步骤

本文面向第一次发布项目的维护者。当前目录是发布候选内容；建议仓库名为 `shopping-agent-post-training`。公开推送前仍应核实所有拟发布数据均可公开再分发。

## 1. 发布前先确认

- 确认公开仓库所有者、仓库名、简介和 README 作者显示名。
- 确认所有训练数据、评估轨迹和数据副本均有公开再分发依据。代码 MIT 许可不会自动覆盖数据、模型输出、商品图文、商标或第三方 fork。
- 检查训练记录、提交历史和当前目录中没有真实地址、个人信息、公司凭据、私有 URL、API key、模型 checkpoint 或不应公开的日志。
- 确认 `LLaMA-Factory/` fork 中保留原许可证和所需声明；其许可证与本项目根目录的 MIT 许可证分别适用。
- README 已添加作者提供的小红书联系链接；公开署名使用项目名，不推断作者真实身份。

## 2. 创建 GitHub 仓库

在 GitHub 选择 **New repository**，选择个人账号或组织，填写仓库名与简介，并设置 **Public**。因为本地目录已有 README、`.gitignore` 和许可证，创建远端仓库时不要再初始化这些文件，以免首次推送产生无关的合并冲突。GitHub 官方说明见[创建新仓库](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)。

简介可以先用：

> A reproducible shopping-agent post-training pipeline: trajectory generation, evaluation, LoRA SFT, and GRPO.

## 3. 检查文件后提交

在 PowerShell 进入 `opensource/`，确认当前位置和待提交内容：

```powershell
Set-Location C:\path\to\opensource
Get-Location
python scripts\scan_sensitive.py
Get-ChildItem -Recurse -File | Sort-Object Length -Descending | Select-Object -First 20 FullName,Length
```

`scan_sensitive.py` 只做启发式检查，不能替代人工检查。特别复核 `sft_data/ready_to_run/`、`LLaMA-Factory/llamafactory/` 中的数据内容，以及根目录 Git 历史是否曾经包含秘密。若秘密曾进入历史，仅从当前文件删除并不能清除历史；先轮换凭据，再按 GitHub 文档清理历史。

确认后，在 `opensource/` 目录初始化独立 Git 仓库，再检查暂存内容并提交：

```powershell
git init -b main
git add .
git status --short
git diff --cached --stat
git commit -m "Initial public release"
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
```

将 `OWNER/REPOSITORY` 替换成实际账号和仓库名。不要在父项目目录执行 `git add .`，以免把开源候选目录以外的私有内容一起推送。

若 Git 提示尚未配置提交者身份，先按你的公开作者署名设置 `git config user.name` 和 `git config user.email`。推送认证请使用 GitHub CLI 登录或系统凭据管理器；不要把 Personal Access Token 写入命令、README 或 remote URL。

## 4. 发布第一个版本

推送完成并在 GitHub 页面检查文件后，创建版本标签：

```powershell
git tag -a v0.1.0 -m "First public release"
git push origin v0.1.0
```

然后在 GitHub 的 Releases 页面基于 `v0.1.0` 创建 Release，粘贴版本说明：包含数据文件概况、可运行模块、已知限制、所需外部模型/硬件和后续改进方向。不要把模型权重或训练 checkpoint 上传到 Git 仓库。

## 5. GitHub 页面设置

- 在 **Settings → General** 确认仓库为 Public，补充描述和 Topics，例如 `llm`, `agent`, `sft`, `grpo`, `llama-factory`。
- 打开 Issues；模板已放在 `.github/ISSUE_TEMPLATE/`，用户可以提问、报告问题或建议功能。GitHub 会识别贡献指南、安全策略和 Issue/PR 模板，见[贡献指南说明](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors)与[模板说明](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates)。
- 在 **Settings → Code security and analysis** 检查 Dependabot alerts、secret scanning 和 push protection 可用项。GitHub 对公共仓库提供 secret scanning 相关保护能力，功能与账号/仓库设置有关；可参考[GitHub secret leak prevention 文档](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/prevent-future-leaks)。
- 在 About 面板添加项目简介、Topics 和 `docs/00-project-overview.md` 作为网站链接（可选）。
- README、数据卡、引用文件和许可证都已放在仓库根目录；补齐作者/主页链接后再公开推送。

## 6. 公开后持续维护

版本更新时维护 CHANGELOG 或 Release notes，记录数据版本、配置变化、复现结果和已知问题。用户反馈集中放在 Issues；有修复时先更新文档和对应脚本，再打新的版本标签。仓库处于第一版，README 已明确欢迎提问和后续优化。

