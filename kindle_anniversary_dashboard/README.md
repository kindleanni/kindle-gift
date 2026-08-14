# Kindle 纪念日副屏（Paperwhite 3）

本目录是已为你的 Kindle Paperwhite 3（1072×1448）生成的仪表盘项目。

`render_dashboard.py` 会从 Open-Meteo 读取北京实时天气，尝试读取东方财富的一条 A 股资讯，按北京时区计算纪念日（2023-08-21 起），并依小时切换小鸡状态。无网络时会保留明确的降级提示；笑话是内置文案。

## 先生成预览

双击 `update-now.cmd`，仪表盘会生成到 `out/anniversary-dashboard.png`。它不会修改 Kindle 的系统或固件。

## 真正显示为锁屏副屏（一次性设置）

这步需要先越狱；本机为 **PW3 / 固件 5.13.6**。请严格依照项目专用的 [越狱与自动更新手册](JAILBREAK_GUIDE.md) 完成 WinterBreak、MRPI、KUAL（coplate）、ScreenSavers Hack 与 Online Screensaver，旧版的 Legacy Jailbreak 路线不适用于这份手册。

安装完成后，ScreenSavers Hack 会在 Kindle 根目录创建 `linkss/screensavers`。其中只保留一个 `bg_ss00.png`：这是 Online Screensaver 的稳定目标文件名，避免与云端图片轮播。双击 `update-now.cmd` 时，脚本会把本地预览推送到 `F:\linkss\screensavers\bg_ss00.png`，并创建 `linkss\reboot` 标记；安全弹出设备后由屏保扩展重读新图。

## 自动每小时更新：两种方式

Kindle 必须在每次更新时连接 USB；因为 USB 存储模式下 Kindle 本身不会联网刷新。可在 Windows「任务计划程序」创建任务：

- 程序/脚本：`python`
- 参数：`"F:\kindle_anniversary_dashboard\render_dashboard.py" --kindle-root F:\`
- 触发器：每 1 小时一次。

任务只在 Kindle 已挂载为 `F:` 且越狱屏保扩展已装好时才会推送图片。锁屏后的电子墨水画面会一直留在屏幕上，耗电极低；要显示新内容，需要电脑执行更新、再安全弹出 Kindle。

这只是有电脑在旁时的备用方式。若希望礼物断开 USB 后自行更新，请使用 [云端自动更新说明](cloud/README.md)：GitHub Actions 每小时在云端生成图片，Kindle 上的 Online Screensaver 扩展通过 Wi-Fi 下载并刷新。它只需要一次性 USB 安装与配置，之后不需要电脑连接。

## 关于“动画”

电子墨水屏不适合循环动画，且休眠锁屏不能逐帧播放。本项目采用“每小时一个静态状态图标”的方式，更稳定、也更适合常亮纪念屏。
