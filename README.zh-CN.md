# SAP BAPI Guard

SAP BAPI Guard 是一个 Codex 插件，用来防止 AI 在生成 ABAP 时凭记忆猜测 BAPI 名称或参数。它提供一个可复用的 Skill，用 SAP ADT 对真实系统进行核验，并提供一个 Git pre-commit hook，用于阻止未核验的 `BAPI_*` 调用进入提交。

## 功能

- 核验 BAPI 或函数模块是否存在于当前连接的 SAP 系统。
- 在可能的情况下，通过 ADT 对象搜索解析函数组。
- 读取函数模块源码并提取接口参数提示。
- 将函数模块定义方向映射到 `CALL FUNCTION` 调用方向。
- 扫描 ABAP 文件中的 `CALL FUNCTION 'BAPI_*'`。
- 安装仓库级 Git hook，在提交前检查 staged ABAP 内容。

## 目录结构

```text
sap-bapi-guard/
  .codex-plugin/plugin.json
  skills/sap-bapi-verifier/
    SKILL.md
    agents/openai.yaml
    scripts/
      verify_bapi.py
      scan_abap_bapi_calls.py
      install_git_hook.py
```

## 前置条件

- Python 3.10 或更高版本。
- Git。
- 配套的 `sap-adt-cli` skill，或等价的 `sap_adt_cli.py`。
- 目标 SAP 系统已启用 ADT 服务。
- 已在 `sap-adt-cli` 中配置 SAP 连接凭据；本插件不会保存凭据。

`verify_bapi.py` 会按以下顺序查找 `sap_adt_cli.py`：

1. `--sap-cli path/to/sap_adt_cli.py`
2. `SAP_ADT_CLI` 环境变量
3. `~/.codex/skills/sap-adt-cli/scripts/sap_adt_cli.py`
4. `~/.agents/skills/sap-adt-cli/scripts/sap_adt_cli.py`

## 作为 Codex 插件安装

将本仓库 clone 或复制到本地 plugins 目录，然后通过 Codex plugin marketplace 流程添加。插件 manifest 位于：

```text
.codex-plugin/plugin.json
```

如果使用 personal marketplace，可以添加类似条目：

```json
{
  "name": "sap-bapi-guard",
  "source": {
    "source": "local",
    "path": "./plugins/sap-bapi-guard"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

## 只安装 Skill

如果不想安装整个插件，也可以只安装可复用的 Skill：

```powershell
python scripts\install_skill.py
```

安装到自定义 skills 目录：

```powershell
python scripts\install_skill.py --target path\to\skills
```

覆盖已有安装：

```powershell
python scripts\install_skill.py --force
```

## 配置 SAP 访问

先配置配套的 SAP ADT CLI：

```powershell
python path\to\sap_adt_cli.py configure
python path\to\sap_adt_cli.py status
```

本插件只执行读取操作，不需要 SAP 写入权限或传输权限。

## 核验 BAPI

```powershell
python skills\sap-bapi-verifier\scripts\verify_bapi.py BAPI_TRANSACTION_COMMIT
```

如果已知函数组：

```powershell
python skills\sap-bapi-verifier\scripts\verify_bapi.py BAPI_TRANSACTION_COMMIT --group BAPT
```

输出 JSON：

```powershell
python skills\sap-bapi-verifier\scripts\verify_bapi.py BAPI_TRANSACTION_COMMIT --json
```

## 扫描 ABAP 文件

```powershell
python skills\sap-bapi-verifier\scripts\scan_abap_bapi_calls.py path\to\repo
```

发现未核验 BAPI 调用时返回失败：

```powershell
python skills\sap-bapi-verifier\scripts\scan_abap_bapi_calls.py path\to\file.abap --fail-on-unverified-bapi
```

扫描器会把附近的如下注释识别为核验证据：

```abap
" Verified by ADT get-function BAPI_TRANSACTION_COMMIT --group BAPT.
CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'
  EXPORTING
    wait = abap_true.
```

## 安装 Git Hook

在本仓库目录下执行：

```powershell
python skills\sap-bapi-verifier\scripts\install_git_hook.py path\to\abap-repo
```

安装器会创建：

```text
path/to/abap-repo/.githooks/pre-commit
```

并执行：

```powershell
git config core.hooksPath .githooks
```

生成的 hook 会检查每个已暂存的 `.abap`、`.inc` 和 `.txt` 文件。它检查的是 Git staged 内容，而不是工作区当前文件内容，这样才能准确验证“即将被提交”的版本。

## Codex 使用方式

可以这样要求 Codex：

```text
Use $sap-bapi-verifier to verify BAPI_ACC_DOCUMENT_POST before writing ABAP.
```

也可以这样：

```text
Use $sap-bapi-verifier to scan this ABAP repository and install the safety hook.
```

Codex 最终回答中应包含核验证据，例如：

```text
Verification:
- Checked BAPI_TRANSACTION_COMMIT in function group BAPT with ADT get-function.
- Caller EXPORTING parameter WAIT and caller IMPORTING parameter RETURN were confirmed.
```

## 本地测试

运行：

```powershell
python tests\run_tests.py
```

测试覆盖扫描器行为，以及 Git hook 对 staged 内容的检查。

## 安全说明

- 不要提交 SAP 凭据。
- 不要在公开测试数据中包含 SAP 主机名、client、用户名、密码或内部对象细节。
- Hook 不会连接 SAP；它只检查本地是否存在核验证据。
- 真实 SAP 核验需要显式运行 `verify_bapi.py`。

## 许可证

MIT
