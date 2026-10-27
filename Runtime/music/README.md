# MediaRemote adapter（macOS）

`mediaremote-adapter.pl` + `MediaRemoteAdapter.framework` 来自
[ungive/mediaremote-adapter](https://github.com/ungive/mediaremote-adapter)，**BSD-3-Clause**。

macOS 15.4+ 起，旧的 `MRMediaRemoteGetNowPlayingInfo` C API 对普通进程返回空；
该适配器通过系统自带、带 MediaRemote 权限的 `/usr/bin/perl` 动态加载 framework，
读取系统 Now Playing（Apple Music、网易云音乐、QQ 音乐等），不需要辅助功能/录屏权限。

- 本项目只调用 `get`，不调用 `send/seek` 等控制命令。
- framework 为 universal（arm64 + x86_64），ad-hoc 签名。
- 上游版本：v0.7.7（仓库 master，构建于 2026-10-27）。
- 许可证：`LICENSE-MediaRemoteAdapter.txt`（BSD-3-Clause，保留版权声明）。
- 自检：`/usr/bin/perl mediaremote-adapter.pl MediaRemoteAdapter.framework test`（需测试客户端，未随包）；本项目用 `get` 做真机验收。

重新构建（macOS，Xcode CLT）：

```bash
git clone https://github.com/ungive/mediaremote-adapter.git
cd mediaremote-adapter
# 参考上游 CMakeLists；本项目用 clang 直接编译 framework 的两个 slice 后 lipo
```

Windows 使用同目录的 `media_smtc.ps1`（系统 SMTC，原创脚本），不依赖该 framework。
