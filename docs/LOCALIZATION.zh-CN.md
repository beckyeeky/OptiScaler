# OptiScaler v0.9.5 简体中文界面（第三方、未签名）

## 来源与范围

基于官方提交 `90d9568d576d93ebb2d6c1c207596d21e9900651`，通过 GitHub fork 后 clone 编辑。此分支不是官方签名发布，不声称与官方二进制逐字节相同。

本补丁只翻译 `OptiScaler/menu/menu_common.cpp` 的用户可见文字，并添加显示所需的中文字体支持和 MSVC `/utf-8` 编译选项。未修改 Config 默认值、INI 文件、渲染算法、shader、upscaler、hook、proxy、厂商依赖库或子模块版本。其他 menu 实现经扫描没有独立的待翻译界面自然语言，保持原样。

覆盖 1026 个字符串字面量出现位置（包含相邻字面量组成的提示、组合项标签、间接变量、启动趣味提示及辅助窗口），不等于 1026 个控件。覆盖主菜单、超分辨率/DLSS/DLSSD/FSR/XeSS、FG 输入输出与高级设置、帧率、锐化、倍率、初始化、兼容性、外观、日志设置、快捷键、性能叠加层、Mipmap 计算器与 HUDless 资源窗口。

保留品牌、API、模型代号、资源状态枚举、技术缩写、后端 token、路径、URL、纯隐藏 ID 和窄按钮 `R`。不翻译日志格式、第三方 ImGui、运行库返回的动态版本/错误信息、外部 Quirks 名称，以及由 Windows 返回的本地化按键名。已有 `##`/`###` 后缀逐项保留；没有给无隐藏 ID 的标签新增 ID，因此这类标签的 ImGui 哈希随显示文字改变。上游已禁用 ImGui ini 持久化。

## 字体

- 仍优先使用 `UseHQFont` 启用时的自定义 `TTFFontPath`；通过 `std::filesystem::path` 和文件内存加载支持 Unicode 路径。
- 保留有效自定义字体，并合并系统中文字体以补足缺失字形。没有自定义字体或加载失败时，依次尝试 Windows Fonts 下的 `msyh.ttc`、`simhei.ttf`、`simsun.ttc`。
- ImGui 1.92+ 按需加载字形；同时提供覆盖汉字及中文标点的静态 ranges。无需调用本版本不存在的 `GetGlyphRangesChineseFull()`。
- 读取失败、空文件、超过 64 MiB 的文件、无效字体会返回空指针并尝试下一回退。所有中文字体均不可用时，仍回退原嵌入 Hack 或 ImGui 默认字体，避免空默认字体；此时中文可能显示缺字，并不保证可读。
- 为保证汉化界面可读，即使 `UseHQFont=false` 也尝试系统中文字体；不改变该配置项的存储值或默认值。其他字号/缩放逻辑保持上游行为，非正字号在显示层回退为 14。
- 不打包或分发任何 Windows 字体。

## 可复现静态验证

需要 Python 3、Git，以及本地可解析的基线提交：

```sh
python tools/validate_zh_cn.py --inventory > menu-baseline-inventory.json
python tools/validate_zh_cn.py
```

`tools/l10n/zh-CN.json` 记录每个翻译的原始字面量编号、基线行号、源文、译文及字体补丁。`--apply` 只接受原始基线或已经与预期完全一致的 menu/project 文件，拒绝覆盖其他更改。它可从固定基线重现补丁，不应使用优化模式 `python -O` 运行（检查使用 assert）。

校验内容：原文和定位不漂移；printf 格式符顺序一致；`{}` 格式字段一致；隐藏 ID 后缀一致；翻译不进入 include/直接日志格式；源码严格等于“固定基线 + 已登记字符串替换 + 已审阅字体块 + 一处既存尾随空白清理”；工程只新增 UTF-8 选项；字体辅助文件哈希一致；受版本控制和非忽略的新增文件均在白名单内；所有 INI 逐字节不变（因此有效键值、注释和默认值也均不变）。

这些检查证明补丁边界，不证明运行画质、游戏兼容性或注入稳定性。

## Windows 构建与字体冒烟测试

需要 VS2022、MSVC v143 x64、Windows SDK、固定版本的七个子模块。不要使用 `git submodule update --remote`。

```powershell
git submodule update --init --recursive
msbuild OptiScaler.sln /m /p:Configuration=Release /p:Platform=x64 /verbosity:minimal
./tools/l10n/test-font.ps1
```

字体测试在 `x64/font-smoke` 构建独立控制台程序，不加载 OptiScaler DLL、不启动游戏、不创建图形设备。测试全部译文非 ASCII 字符的真实 FreeType 字形、缺失/无效字体、Unicode 字体路径以及系统字体合并。测试机器须有微软雅黑用于 Unicode 路径复制测试；字体临时副本仅在本地测试目录存在，测试成功后删除。

本次机器检测到 VS2022 17.14.45、MSVC 14.44.35207、Windows SDK 10.0.22621.0/10.0.26100.0。官方未改基线和最终汉化版均实际完成 Release x64 编译与链接，退出码 0。字体测试通过，共 741 个不同的非 ASCII 字符。

上游构建警告包括弃用的 FidelityFX API、静态/动态 CRT 链接冲突；开启 `/utf-8` 后上游某些含非 UTF-8 字节的头文件出现 C4828 警告，本补丁不为清理警告而修改这些范围外文件。原构建后步骤还会报告旧版 `external/FidelityFX-SDK` 的两个复制源不存在；后续命令使构建整体返回成功。故成功产出 DLL 不等于完整运行依赖分发包齐全，不要将构建后目录当作经过审核的完整安装包。

## 手动 Actions

`.github/workflows/build-zh-cn.yml` 只有 `workflow_dispatch`，`contents: read`，Windows 2022、递归固定子模块、Release x64，无签名、release、部署、推送或游戏目录写入操作。仅上传供审核的 DLL、LICENSE、汉化说明、映射、来源提交、子模块记录、SHA-256 和构建日志，不重新分发厂商运行库或字体。

推送与触发由维护者另行授权；本次没有推送或运行 Actions。不要运行上游有发布写入的 `build.yml` 来替代此流程。

## 验收与限制

仍须在隔离环境人工检查窗口宽度、长提示换行、DPI/菜单缩放、不同 `UseHQFont` 值与自定义字体、快捷键捕获、控件状态和设置保存。未进行游戏内注入、画质 A/B 或性能测试。本次未读写游戏安装目录。发布修改后二进制前，应保留 GPL 许可、版权、修改说明并提供对应源码，同时逐项核查厂商运行库的再分发许可。
