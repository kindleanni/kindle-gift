# PW3 纪念日副屏：越狱与每小时自动更新手册

> 适用设备：序列号前缀 `G090 KB` 的 Kindle Paperwhite 3（PW3 / 第 7 代），固件 `5.13.6 (3731990038)`，屏幕 `1072 × 1448`。
>
> 本手册按 2026-08-14 可获得的工具与资料编写。请**逐阶段完成并验收**，不要一次把所有文件都放进 Kindle，更不要跳过“成功判据”。

这不是 Amazon 官方功能。越狱会降低设备的可维护性、可能影响保修；固件升级、恢复出厂或装错 `.bin` 都可能让这条路线失效。好消息是：你的 5.13.6 是旧版 soft-float 固件，正是 `linkss` 自定义锁屏可用的范围；它低于 WinterBreak 的 `5.18.1` 上限。

本项目不需要在 Kindle 上跑 Python，也不需要 SSH 或 USBNetwork。目标是让 Kindle 在正常“休眠锁屏”状态下保留仪表盘，按小时短暂唤醒、连接已保存的 Wi-Fi、下载一张新 PNG，再回到休眠。

```text
GitHub Actions（每小时生成图片）
             │
             └─ GitHub Pages /anniversary-dashboard.png
                              │  Wi-Fi，约每小时
WinterBreak → MRPI + KUAL → linkss/bg_ss00.png ← Online Screensaver
                              │
                         Kindle 休眠锁屏
```

## 先读这五条：不要做什么

1. **不要运行或安装 Amazon 固件更新。** 本机目前已确认根目录没有 Amazon 的 `update*.bin` / `update.bin.tmp.partial`。以后也不要在 Kindle 根目录保留这类文件，更不要下载书伴文章中的“等于或高于当前版本”的官方固件。
2. **不要随意点 Kindle 设置里的“更新您的 Kindle”。** 当前 WinterBreak / `jb.sh` 会为了阻断 OTA 而禁用系统更新组件；因此该菜单变灰通常是预期结果，绝不应为了让它可点而恢复或手工改动系统文件。第三方 `.bin` 默认只通过 MRPI 安装，放在 `mrpackages` 文件夹。普通 KUAL 包、linkss 包或任何 Amazon 固件都绝不能走系统更新菜单。
3. **不要在连接电脑 USB 数据线时重启 Kindle 或重启 linkss。** 改完屏保后必须安全弹出、拔掉数据线，再在 Kindle 上重启。普通墙充只供电，不算 USB 数据模式，可以使用。
4. **越狱成功后不要注销 Amazon 账号或恢复出厂。** 注销会删掉 `documents` 中的启动器；如果已启用 OTA 阻断就恢复出厂，还可能造成恢复更新困难。
5. **不要混用旧教程的 Hotfix / `emergency.sh` / PEKI 路径。** 本机是新版 WinterBreak / `jb.sh`；PEKI 自己声明的兼容上限是旧 Universal Hotfix 2.3.7，不能把它当作本机 `jb.sh v1.3.5` 的已验证安装方式。不要把旧 Universal Hotfix、书伴的 `emergency.sh`、PEKI 或其他人的修改版叠加进去。

只要某一步的成功判据没有满足，就停在该步，不要用“恢复出厂试试”来解决。

## 阶段 0：准备、备份、下载（尚不越狱）

### 0.1 准备清单

- Kindle 电量至少 50%，一根可靠的 USB 数据线。
- 一台 Windows 电脑、7-Zip（需要解压 `.tar.gz` / `.tar.xz`）。
- 一个可以登录的 Amazon 账号；WinterBreak 要求 Kindle 已注册，并保存一个可联网的 Wi-Fi。
- 一个可登录的 GitHub 账号；后面会用公开 GitHub Pages 托管图片。
- Kindle 不是“特惠广告 / Special Offers”锁屏机。若锁屏会显示 Amazon 广告，先通过 Amazon 正规渠道取消该服务；`linkss` 不会绕过已购买的锁屏广告。

### 0.2 先做 PC 备份

在电脑的长期位置（例如 `C:\KindleGiftBackup\2026-08-14\`）分别复制：

```text
F:\documents\
F:\kindle_anniversary_dashboard\
```

第二项很重要：目前项目在 Kindle 的 `F:` 根目录，不应把它当成唯一源码副本。今后发布 GitHub Actions 时，应从电脑上的备份副本操作，不依赖 Kindle 仍插在电脑上。

**成功判据：** 电脑上能看到这两个完整副本，并且 Kindle 原文件仍在。

### 0.3 先下载到电脑，不要直接解压到 Kindle

在电脑上新建一个临时下载目录，下载下表中的文件。只从表中链接的原始项目下载；压缩包不要直接在 `F:` 解压。

| 用途 | 下载位置 | 之后会用到什么 |
| --- | --- | --- |
| WinterBreak | [官方说明](https://kindlemodding.org/jailbreaking/WinterBreak/) 的 Latest release | `WinterBreak.tar.gz` 的**内容** |
| 填充存储 | [Kindle-Filler-Disk](https://github.com/iiroak/Kindle-Filler-Disk) | `Scripts/Filler.ps1` |
| MRPI | [NiLuJe Snapshots](https://www.mobileread.com/forums/showthread.php?t=225030) 的 **MR Package Installer** | `kual-mrinstaller-*.tar.xz` |
| KUAL | 同一 Snapshots 页的 **KUAL (coplate)** | `KUAL-<提交号>-*.tar.xz` |
| 屏保 hack | 同一 Snapshots 页的 **ScreenSavers Hack** | `kindle-linkss-*.tar.xz` |
| 自动联网屏保 | [FalconFour/onlinescreensaverPW2](https://github.com/FalconFour/onlinescreensaverPW2) → Code → Download ZIP | 整个扩展目录 |
| OTA 二次防护（推荐） | [官方 Disable OTA 指南](https://kindlemodding.org/jailbreaking/post-jailbreak/disable-ota.html) 中的 `renameotabin` | 最内层 `renameotabin` 文件夹 |

写本手册时，Snapshots 中的 KUAL coplate 文件名为 `KUAL-c6ac782-20250419.tar.xz`，MRPI 为 `kual-mrinstaller-1.7.N-r19303.tar.xz`，屏保 hack 为 `kindle-linkss-0.25.N-r18981.tar.xz`。版本会变，优先选当前 Snapshots 页的同类项目，不要猜测或混用其他论坛附件。

## 阶段 1：先阻断自动升级

这一步的目的不是“占满空间”，而是在必须临时联网注册、打开商店时，让 Kindle 没有空间下载并安装新固件。官方建议只留下 50–90 MB 可用空间。

### 1.1 开飞行模式、重启、清除待升级文件

1. 拔掉 Kindle。
2. 在 Kindle 顶部设置中打开 **飞行模式**。
3. 在设置的 `⋮` 菜单中选择 **Restart / 重启**，等它完全回到首页。
4. 用 USB 连到电脑，确认资源管理器的盘符仍是 `F:`。
5. 这台设备此前的 Amazon 更新包已经清除；若你没有看到它，不要为了“补齐步骤”再下载它。只需检查 `F:\` 根目录没有 Amazon 的 `update*.bin` 或 `update.bin.tmp.partial`。
6. 若发现这类 Amazon 文件，才在资源管理器中手动删除它们。**不要**删除 `system`、`documents`、`fonts`、`voice`、`kindle_anniversary_dashboard`，也不要删除 `mrpackages` 中的第三方安装包。若根目录已留有 `Update_KUALBooklet_hotfix_...bin`，先保留它，不要运行它；后文 3.3 改用本机已安装的 Scriptlet 启动 MRPI。

**成功判据：** `F:\` 根目录没有 Amazon 的 `update*.bin` / `.partial`，Kindle 仍处于飞行模式。

### 1.2 填充到只余 50 MB

1. 将刚才下载的 `Filler.ps1` 复制到 `F:\Filler.ps1`。
2. 在资源管理器中右键它，选 **使用 PowerShell 运行**。
3. 看到菜单后：

   - 选 `1`：Fill the device；
   - 若它没有自动识别 Kindle，**只选择标为 Kindle 的 `F:`**，绝不能选电脑系统盘；
   - 在“留下多少空间”菜单选 `2`：**50 MB – balanced**；
   - 阅读它显示的目标路径，确认是 `F:\fill_disk` 后再确认。

4. 等脚本完成，再安全弹出 Kindle。
5. 在 Kindle 的设置 → 设备信息中检查可用空间，应该约为 50–90 MB。

脚本只会创建 `F:\fill_disk\` 里的无意义填充文件，后面会用它的“Remove filler files”选项清除。

**成功判据：** Kindle 可用空间约 50–90 MB，`F:\fill_disk\` 存在，飞行模式仍开着。

### 1.3 如果 Kindle 尚未注册

如果设备已经注册且记得目标 Wi-Fi，可以跳过本节。若没有：

1. **保留填充文件**，临时关闭飞行模式，连上可信 Wi-Fi，完成 Amazon 登录/注册。
2. 登录完成、Wi-Fi 已保存后立即重新打开飞行模式。
3. 再次 USB 连接检查根目录有没有新出现的 `update*.bin` / `.partial`；有就删掉。

**成功判据：** Kindle 已注册、目标 Wi-Fi 已保存、重新回到飞行模式、空间仍很少。

## 阶段 2：执行 WinterBreak 越狱

### 2.1 正确复制 WinterBreak

1. 在电脑的临时下载目录用 7-Zip 完整解压 `WinterBreak.tar.gz`。若先得到 `.tar`，再解压一次。
2. 打开解压后的最内层目录，把**里面的内容**复制到 `F:\` 根目录；不要把压缩包或外层文件夹放进去。
3. 其中的隐藏目录 `.active_content_sandbox` 必须一并复制。Windows 资源管理器中可先开启“查看 → 显示 → 隐藏的项目”；若询问替换，允许它替换同名目录。
4. 安全弹出 Kindle，拔掉 USB。

复制后预期根目录会有 WinterBreak 的 `mesquito`、`apps` 等内容以及被替换的 `.active_content_sandbox`。这次替换是本流程的刻意行为，不是误删。

### 2.2 在 Kindle 上触发

1. 回到首页，点击购物车图标打开 Kindle Store。
2. Kindle 询问是否关闭飞行模式时，选 **Yes**。这是本流程唯一需要临时联网的时刻。
3. 商店应打开 Mesquito；点击其中的 **WinterBreak** 图标。
4. 不要按电源键、不要返回、不要插 USB。等至少 2 分钟（通常约 30 秒）。

**成功判据：** 屏幕出现一段调试文字，显示类似 **“You are now ready to install the hotfix”** 的小字，然后 Kindle 图形界面重新启动。回到首页后立刻重新开启飞行模式。随后用 USB 连接电脑，确认存在：

```text
F:\documents\JAILBROKEN.txt
```

其内容应含有 `You are jailbroken!` 和 `Winterbreak Jailbreak`（本机为 `jb.sh v1.3.5`）。这是本机判断 WinterBreak 成功的主判据。

可以额外在搜索框精确输入：

```text
;log
```

按搜索。若出现弹窗或文字，说明旧式调试入口也可用；**但在 5.12.2 及以上固件，完全无反应并不等于越狱失败。** Amazon 可能只封住了搜索栏的 `;log` 入口。只要上面的 `JAILBROKEN.txt` 存在，就直接按 3.3 的 Scriptlet 路径继续。

> 使用当前 WinterBreak 时，**不要**另行下载 `Update_hotfix_universal.bin`，也不要用系统设置安装任何 `.bin`。官方说明是 WinterBreak 已包含所需 Hotfix 与 OTA 防护；上面的文字是成功标志，不是要求你手动安装 Amazon 更新。KUAL 的初装请使用 3.3 的 Scriptlet 路径。

### 2.3 此阶段失败时怎么办

| 现象 | 只做这些检查 |
| --- | --- |
| 打开商店后不是 Mesquito，或点 WinterBreak 没有任何调试文字 | 开飞行模式；检查可用空间是否仍为 50–90 MB、根目录没有更新包、`.active_content_sandbox` 是否确实被替换；重启后重新从 2.1 开始。 |
| 商店只显示首页或报 Unexpected error | 使用 WinterBreak 官方页的 **LocalStorage Replacement** 排障：让 Kindle 在已填充状态下短暂连网浏览商店，再按官方指定路径清理 `LocalStorage` 缓存，重新复制 WinterBreak 文件。不要先恢复出厂。 |
| `;log` 没有反应，但 `F:\documents\JAILBROKEN.txt` 明确写有 `You are jailbroken!` | WinterBreak 已成功；这是 5.12.2+ 常见的搜索入口限制。**不要**按书伴的 `emergency.sh` + 官方固件升级方案，也不要重做越狱；转到 3.3。 |
| `;log` 没有反应，且没有 `JAILBROKEN.txt` | 保持飞行模式，删除新出现的 Amazon 根目录更新文件，回到 2.1 重试；此时才视为 WinterBreak 未完成。 |

## 阶段 3：释放空间，安装 MRPI 与 KUAL coplate

### 3.1 释放填充文件

只要 `F:\documents\JAILBROKEN.txt` 已证明 WinterBreak 成功就可以做：USB 连接 Kindle（保持飞行模式），再次运行 `Filler.ps1`，选：

```text
2 → Remove filler files
```

它只会删除 `F:\fill_disk\`。然后确认 Kindle 至少有 **300 MB** 可用空间；官方最低排障值为 220 MB，300 MB 更稳妥。

**成功判据：** `F:\fill_disk\` 已不存在或已清空，`F:` 有 300 MB 以上可用空间，根目录没有 Amazon 更新包。

### 3.2 放置 MRPI 与 KUAL 安装包

1. 解压 MRPI 的 `.tar.xz`。
2. 将解压出的两个文件夹直接合并到 `F:\`：

   ```text
   F:\extensions\
   F:\mrpackages\
   ```

   不要多嵌一层 `kual-mrinstaller-...` 文件夹。
3. 解压 KUAL **coplate** 的 `.tar.xz`。
4. 只复制不含 `hotfix`、不含 `HDRepack` 的常规安装文件到：

   ```text
   F:\mrpackages\Update_KUALBooklet_c6ac782_install.bin
   ```

   将来版本号可能不同，但文件模式应为 `Update_KUALBooklet_<提交号>_install.bin`。
5. 若 `;log mrpi` **确实有反应**，安全弹出并拔掉 USB，保持飞行模式后输入该命令安装；屏幕可能短暂变白或显示安装文字，期间不要操作。
6. 若 `;log mrpi` **没有反应**（本机就是这种情况），不要重复输入、不要重做 WinterBreak。保留这里的 MRPI 文件夹和普通 KUAL 包，直接进行 3.3。

**传统路径成功判据：** 资料库中出现 `KUAL`，打开它可见菜单。若要核查安装日志，重连 USB 后看：

```text
F:\extensions\MRInstaller\log\mrinstaller.log
```

末尾应有类似 `Success! :)` 的成功记录。

### 3.3 固件 5.12.2+ 且 `;log` 无反应：用 Scriptlet 启动现有 MRPI

这是给本机 `5.13.6` + `WinterBreak Jailbreak (jb.sh v1.3.5)` 的替代路径，**不会**运行 `;log mrpi` 或“更新您的 Kindle”。新版 `jb.sh` 会主动停用并改名 OTA 更新程序，所以系统更新菜单变灰是预期现象，不是你复制的 KUAL hotfix 包损坏。

本机已经满足前提：`JAILBROKEN.txt` 存在、`F:` 有约 1.7 GB 空闲、`F:\extensions\MRInstaller\bin\mrinstaller.sh` 与 `F:\mrpackages\Update_KUALBooklet_c6ac782_install.bin` 已就位。新版越狱同时安装了 Scriptlet：`documents` 中的 `.sh` 文件会出现在资料库，点击后以越狱权限执行。为了先验证这个入口，必须先做 3.3.1，再做真正安装。

#### 3.3.1 无副作用验证 Scriptlet

1. 用 VS Code 或 Notepad++ 新建以下文件，**编码 UTF-8、换行 LF、文件名完全为**：

   ```text
   F:\documents\00 Scriptlet Check.sh
   ```

2. 文件内容只能是以下几行：

   ```sh
   #!/bin/sh
   # Name: Scriptlet Check
   # Author: Kindle Dashboard
   printf 'Scriptlets ready. UID=%s\n' "$(id -u)"
   sleep 5
   ```

3. 安全弹出并拔掉 USB 数据线。回到 Kindle 首页，等最多一分钟让资料库索引；必要时在资料库选择“全部”或“文档”。找到 **Scriptlet Check** 并打开。

**成功判据：** 屏幕显示 `Scriptlets ready. UID=0`。这一步没有安装、删除或改动任何系统组件，只确认新版 Scriptlet 启动器可用。

**停止判据：** 一分钟后仍没有 **Scriptlet Check**，或点击后不显示 `UID=0` 时，先不要执行下节；重新连接 USB，确认文件不叫 `00 Scriptlet Check.sh.txt`、确实直接在 `F:\documents\`、且换行是 LF。

#### 3.3.2 用 Scriptlet 调用 MRPI，安装已放好的 KUAL

只有 3.3.1 成功后才进行：

1. 保留 `F:\mrpackages\Update_KUALBooklet_c6ac782_install.bin`；确认 `mrpackages` 里暂时只有这一枚准备安装的 `.bin`。根目录的 `Update_KUALBooklet_hotfix_c6ac782_install.bin` 不会被 MRPI 读取，可以先留着，但**绝不**通过系统更新菜单运行它。
2. 在 `F:\documents\` 新建以下文件，仍须 **UTF-8、LF 换行、ASCII 文件名**：

   ```text
   F:\documents\01 Install MR Packages.sh
   ```

3. 内容必须完全如下；`# DontUseFBInk` 必须保留在文件开头几行，避免启动器与 MRPI 同时接管电子墨水屏：

   ```sh
   #!/bin/sh
   # Name: Install MR Packages
   # Author: Kindle Dashboard
   # DontUseFBInk
   exec /bin/sh /mnt/us/extensions/MRInstaller/bin/mrinstaller.sh launch_installer
   ```

4. 安全弹出、拔线，在资料库中点击 **Install MR Packages** 一次。不要在 USB 数据模式下执行，不要连续点击。

**成功判据：** 几秒内出现 `Launching the MR installer...`，结束显示 `Done, restarting UI...`，Kindle UI 自动重启；回到资料库后出现并能打开 **KUAL**。此时 KUAL 菜单应有：

```text
Helper → Install MR Packages
```

之后回到 4.1，用这个菜单安装 `mrpackages` 中的 linkss 包即可，全程不再需要 `;log mrpi` 或系统更新菜单。

**停止判据：** 出现 `Unprivileged user, aborting`、`Couldn't setup binaries`、安装错误画面、三分钟后仍未回到首页、或没有 KUAL 时，拍下屏幕并重新连接 USB，查看 `F:\extensions\MRInstaller\log\mrinstaller.log`；不要重试、不恢复出厂、不放 `emergency.sh`、不启用 OTA。MRPI 会在处理后移走安装包，因此失败时必须先读日志再决定下一步。

### 3.4 为长期联网加第二层 OTA 防护（推荐）

WinterBreak 已会阻断更新；但这个礼物以后会频繁连 Wi-Fi，建议再用 KUAL 的可见防护作为第二层。

1. 从 [官方 Disable OTA 指南](https://kindlemodding.org/jailbreaking/post-jailbreak/disable-ota.html) 下载 `renameotabin`。
2. 解压后只复制最内层、直接包含 `bin` / `menu.json` 等内容的文件夹，使路径恰好是：

   ```text
   F:\extensions\renameotabin\
   ```

   不能是 `F:\extensions\renameotabin\renameotabin\...`。
3. 删除根目录出现的任何 `update*.bin` / `.partial`，安全弹出并拔线。
4. 在 KUAL 中依次点击：

   ```text
   Rename OTA Binaries → Rename
   ```

5. Kindle 会自动重启，等它回到首页。

**成功判据：** KUAL 菜单此后有 `Restore` 可供未来恢复；你没有放入任何测试固件，但长期连 Wi-Fi 前有明确的 OTA 阻断层。未来若真的要恢复出厂、升级或降级，必须先在同一菜单选 `Restore`。

## 阶段 4：安装 linkss 屏保 hack，并显示本地仪表盘

### 4.1 安装 linkss

本项目使用的是已渲染 PNG，不使用“书籍封面”模式，因此**不要安装 100 MB 的 Kindle Python 包**。

1. 解压 `kindle-linkss-*.tar.xz`。
2. 对 PW3，选择文件名含下面整段设备列表的安装包：

   ```text
   Update_linkss_..._install_pw2_kt2_kv_pw3_koa_kt3_koa2_pw4_kt4.bin
   ```

3. 把它复制到：

   ```text
   F:\mrpackages\
   ```

4. 安全弹出并拔线。
5. 在 KUAL 中选择：

   ```text
   Helper → Install MR Packages
   ```

   若没有该项，不要改回首页搜索 `;log mrpi`（本机入口可能始终被封住）；先停止，检查 `F:\extensions\MRInstaller\config.xml` 与 `menu.json` 是否存在且目录没有多嵌一层。
6. 等 Kindle 重启完成，再按电源键让它进入休眠。

**成功判据：** 根目录出现：

```text
F:\linkss\screensavers\
```

初次休眠会显示 linkss 的专用确认屏，而不是 Amazon 默认屏保。

### 4.2 放入并验证本项目的本地 PNG

1. USB 连接 Kindle。
2. 在 `F:\linkss\screensavers\` 中删除 linkss 附带的示例 PNG；这里最终**只能留一张有效 PNG**，文件名必须是：

   ```text
   bg_ss00.png
   ```

3. 双击：

   ```text
   F:\kindle_anniversary_dashboard\update-now.cmd
   ```

   当前项目已改为把预览图推送到 `F:\linkss\screensavers\bg_ss00.png`。云端文件名仍然会是 `anniversary-dashboard.png`，两者不同是刻意的。
4. 确认命令窗口显示生成成功，并且 `bg_ss00.png` 存在。
5. 安全弹出 Kindle，**拔掉数据线**；在 Kindle 设置的 `⋮` 菜单中选择重启。
6. 回到首页后按电源键休眠。

**成功判据：** 休眠画面显示这份纪念日仪表盘。它应是 `1072 × 1448` 的灰度 PNG；若显示白屏、默认屏保或示例屏，先恢复到只留这张 `bg_ss00.png`，再在拔线状态重启，别加入其他图片。

## 阶段 5：把本项目部署到 GitHub Pages

这个阶段只在电脑上做一次。GitHub Actions 每小时生成最新图；Kindle 之后只下载，不再需要插电脑。

1. 用阶段 0 的电脑备份项目创建一个**公开** GitHub 仓库，例如 `kindle-gift`。上传的是 `kindle_anniversary_dashboard` 文件夹**内部全部内容**，不是外层文件夹；`.github/workflows/publish-dashboard.yml` 必须一并上传。
2. 在仓库的 `Settings → Pages → Build and deployment` 中把 Source 选为 **GitHub Actions**。
3. 打开 `Actions`，手动运行一次 **Publish Kindle dashboard**。
4. 等工作流和 Deploy 都显示成功后，在电脑浏览器打开：

   ```text
   https://<GitHub用户名>.github.io/<仓库名>/anniversary-dashboard.png
   ```

   如果仓库名正好是 `<GitHub用户名>.github.io`，URL 中省略 `/<仓库名>`。
5. 下载或打开该图，确认它不是 404/网页，而是项目最新的 `1072 × 1448` 仪表盘 PNG。

**成功判据：** 浏览器能直接显示最新仪表盘 PNG。工作流现在计划在每小时第 17 分钟运行；GitHub 调度和 Pages 传播会有几分钟延迟，所以这是一套“约每小时”显示，不是精确整点时钟。公开仓库和图片地址任何知道链接的人都可访问，别放真实姓名、照片、token 或其他敏感资料。

## 阶段 6：安装并配置 Online Screensaver

### 6.1 正确的目录结构

1. 在电脑解压 FalconFour 的 ZIP。
2. 复制 ZIP 最内层目录的内容，让 Kindle 上的路径**恰好**为：

   ```text
   F:\extensions\onlinescreensaver\bin\update.sh
   F:\extensions\onlinescreensaver\bin\config.sh
   ```

   不能多一层 `onlinescreensaverPW2-main`。
3. 建议先把 `F:\extensions\onlinescreensaver\` 备份到电脑，便于恢复。

当前 fork 已自行处理脚本工作目录；不要套用旧教程里“四个 `source config.sh` 改绝对路径”的补丁。

### 6.2 用 LF 换行编辑配置

用 VS Code 或 Notepad++ 打开：

```text
F:\extensions\onlinescreensaver\bin\config.sh
```

在 VS Code 右下角确认换行是 **LF**（不是 CRLF），再设置或替换以下变量：

```sh
DEFAULTINTERVAL=60
SCHEDULE="00:00-24:00=60"
IMAGE_URI="https://<GitHub用户名>.github.io/<仓库名>/anniversary-dashboard.png"
SCREENSAVERFOLDER=/mnt/us/linkss/screensavers
SCREENSAVERFILE=$SCREENSAVERFOLDER/bg_ss00.png
LOGGING=1
LOGFILE=/mnt/us/extensions/onlinescreensaver/log/onlinescreensaver.log
TMPFILE=/tmp/tmp.onlinescreensaver.png
```

注意：

- `IMAGE_URI` 填 PNG 的**无 query 参数直链**。扩展会自行追加 `?batteryLevel=...&isCharging=...`；不要自己添加 `?cache=...`。
- Kindle 端仍只留 `bg_ss00.png`；不要把云端同名的 `anniversary-dashboard.png` 再复制进 `linkss/screensavers`，否则 linkss 会轮播两张。
- 该扩展的下载命令使用 `--no-check-certificate`。所以 URL 必须是公开、没有 token/密码的只读图片地址，图片中也不应放敏感信息。

保存后安全弹出、拔线，在 Kindle 设置中重启一次。

### 6.3 先做一次人工联网更新

1. 在 Kindle 中关闭飞行模式，连接阶段 1 保存的可信 Wi-Fi，等状态栏显示已连接。
2. 打开 KUAL → `Online-Screensaver` → **Update now**。

   `Update now` 只负责下载，它不会替你完成首次 Wi-Fi 连接，所以这一步必须先手动连网。
3. 等十几秒，回到休眠画面查看。

**成功判据：** `bg_ss00.png` 被云端 PNG 覆盖，锁屏立即显示 GitHub Pages 的新图。若失败，先在电脑浏览器确认 `IMAGE_URI` 能下载干净的 1072 × 1448 PNG，再检查 `config.sh` 为 LF、目录没有多嵌一层。日志在这里：

```text
F:\extensions\onlinescreensaver\log\onlinescreensaver.log
```

日志会先暂存，刚测试完没有立刻写入不单独构成失败；先以屏幕是否换图为准。

### 6.4 再开启自动更新，并做硬验收

只有 6.3 成功后，才在 KUAL → `Online-Screensaver` 选择：

```text
Enable auto-download
```

它会注册一个 Kindle 系统服务，因此不能把“菜单已经变成 Disable”当成成功。安全弹出状态下重启 Kindle，把它正常按电源键进入休眠（不是长按关机），等待 **65–70 分钟**。

**成功判据必须同时满足：**

1. KUAL 菜单由 `Enable auto-download` 变为 `Disable auto-download`；
2. 等待一个周期后，屏幕仍为云端新图，或因小时状态/日期变化而刷新；
3. 日志出现类似：

   ```text
   Starting event-driven scheduler
   RTC wakeup set
   Screen saver image updated successfully
   ```

调度器会在进入休眠时立即尝试一次更新，此后用 RTC 按计划唤醒；每次成功后会关闭 Wi-Fi。电脑 USB 数据模式接着时它会跳过写入；普通墙充不影响。长按电源彻底关机时，RTC 不会唤醒它。

### 6.5 如果“Update now 成功，但 70 分钟后自动更新没有发生”

先在 KUAL 选择 **Disable auto-download**，确认菜单重新显示 Enable，再重启。不要直接选 Uninstall：该 fork 的 Uninstall 不会清除已注册的系统服务。

先检查：Kindle 时间是否正确、Wi-Fi 是否仍保存、`config.sh` 是否 LF、日志是否有网络错误。当前 fork 的服务配置中有一个未定义 `$SCRIPT` 的保护条件；只有在“手动更新已经成功、自动模式仍完全没有启动日志”的确切症状下，才做下面这个最小修复：

1. USB 连接后打开：

   ```text
   F:\extensions\onlinescreensaver\bin\onlinescreensaver.conf
   ```

2. 找到：

   ```sh
   if [ -e $SCRIPT ]; then
   ```

   改成：

   ```sh
   if [ -x /mnt/base-us/extensions/onlinescreensaver/bin/scheduler.sh ]; then
   ```

3. 保持 LF 保存，安全弹出并拔线。
4. 在 KUAL 中重新执行 **Enable auto-download**（这样才会把修复后的配置写入系统服务），重启、休眠，再等一个周期复测。

如果这次仍没有满足 6.4 的三个判据，关闭自动模式，保留本地 linkss 屏保，不要恢复出厂；带上 `onlinescreensaver.log` 再排查。

## 最终交付验收清单

交给对象前，逐项打勾：

- [ ] `F:\documents\JAILBROKEN.txt` 含 `You are jailbroken!`；`;log` 有无反应都不再作为本机唯一判据。
- [ ] KUAL 可打开，且 `Helper → Install MR Packages` 能运行 MRPI。
- [ ] KUAL 中已执行 `Rename OTA Binaries → Rename`，根目录没有 Amazon `update*.bin`。
- [ ] `F:\linkss\screensavers\` 只有 `bg_ss00.png`，并且 Kindle 休眠时显示仪表盘。
- [ ] 电脑浏览器能打开 GitHub Pages 的 `anniversary-dashboard.png`，且确实是 1072 × 1448 PNG。
- [ ] KUAL 的 **Update now** 能把 GitHub 图刷新到屏幕。
- [ ] 开启自动模式、重启并休眠后，65–70 分钟内至少成功自动刷新一次；日志有成功记录。
- [ ] 拔掉电脑 USB 数据线后依然成立。礼物展示时可接普通墙充，Kindle 保持正常休眠，不要长按关机。

完成这些检查后，电脑不再需要每小时连接 USB。GitHub Actions 负责生成图片，Kindle 负责定时取图；天气或股市源短暂失败时，渲染器会保留降级文案，而不会让屏幕空白。

## 参考资料

- [WinterBreak 官方说明](https://kindlemodding.org/jailbreaking/WinterBreak/)，[自动更新防护](https://kindlemodding.org/jailbreaking/prevent-auto-update/)，[越狱 FAQ](https://kindlemodding.org/jailbreaking/jailbreak-faq.html)
- [NiLuJe ScreenSavers Hack 原始说明](https://www.mobileread.com/forums/showthread.php?t=195474)，[当前 Snapshots](https://www.mobileread.com/forums/showthread.php?t=225030)
- [Scriptlet 官方说明](https://kindlemodding.org/kindle-dev/scriptlets.html)，[MRPI / KUAL 官方安装说明](https://kindlemodding.org/jailbreaking/post-jailbreak/installing-kual-mrpi/)，[jb.sh 源码与 OTA 阻断实现](https://github.com/KindleModding/jb.sh)，[PEKI 自述的兼容上限](https://github.com/KindleTweaks/PEKI)
- [FalconFour Online Screensaver](https://github.com/FalconFour/onlinescreensaverPW2)，[其当前配置文件](https://raw.githubusercontent.com/FalconFour/onlinescreensaverPW2/main/bin/config.sh)
