# 无电脑自动更新：GitHub Pages 方案

这套文件让 GitHub Actions 每小时在云端运行 `render_dashboard.py`，再由 GitHub Pages 对外提供最新的 `anniversary-dashboard.png`。Kindle 的 Online Screensaver 扩展只下载图片，因此断开 USB 后仍可自动更新。

## 一次性云端部署

1. 在自己的 GitHub 账号新建一个**公开**仓库，例如 `kindle-gift`。公开仓库使免费 GitHub Pages 可用；图片 URL 知道的人都能看到，不要放照片、姓名或敏感内容。
2. 将 `kindle_anniversary_dashboard` **文件夹里的全部内容**上传到仓库根目录（不要多套一层文件夹），并保留 `.github/workflows/publish-dashboard.yml`。GitHub 的网页上传可能不显示以 `.` 开头的目录时，请用 Git 或 GitHub Desktop 上传。
3. 在仓库 Settings → Pages → Build and deployment，将 Source 设为 **GitHub Actions**。
4. 在 Actions 中手动运行一次 `Publish Kindle dashboard`。成功后，部署步骤会显示 Pages 地址；最终图片地址为：

   `https://<你的GitHub用户名>.github.io/<仓库名>/anniversary-dashboard.png`

5. 保留这条地址，填入 Kindle 的 Online Screensaver 配置中的 `IMAGE_URI`。

GitHub 的定时工作流以 UTC 运行；此工作流固定在每小时第 17 分钟执行，并且脚本明确使用北京时间。计划任务可能延迟，因此它适合“约每小时”更新而非准点时钟。公开仓库 60 天没有任何仓库活动时，GitHub 会自动停用计划任务；每两个月手动编辑一次 README 或在 Actions 里重新启用即可。

## Kindle 一次性设置（完成越狱后）

完整的设备端步骤见 [越狱与自动更新手册](../JAILBREAK_GUIDE.md)。WinterBreak 已包含其所需的 Hotfix/OTA 防护；之后安装 MRPI、KUAL（coplate）、K5 ScreenSavers Hack 与 **Online Screensaver** KUAL 扩展。扩展通过 Kindle 的 RTC 定时器唤醒 Wi‑Fi、下载 `IMAGE_URI` 所指向的 PNG 并替换锁屏图。

下载 FalconFour 的当前版 Online Screensaver 后，保留其原有脚本，不要套用旧版 PW3 的相对路径补丁。用支持 LF 换行的编辑器修改 `extensions/onlinescreensaver/bin/config.sh`：

```sh
DEFAULTINTERVAL=60
SCHEDULE="00:00-24:00=60"
IMAGE_URI="https://<你的GitHub用户名>.github.io/<仓库名>/anniversary-dashboard.png"
SCREENSAVERFILE=/mnt/us/linkss/screensavers/bg_ss00.png
LOGGING=1
```

`linkss/screensavers` 中只保留 `bg_ss00.png`，先用 KUAL 的 **Update now** 成功验证一次，再执行 Enable / Auto update。该扩展会把电量参数附加到 URL，并以不校验证书的方式下载图片；因此不要在 URL 或图中放 token、私密照片、姓名等敏感信息。

## 电源与限制

- Kindle 需要连接已保存的 Wi‑Fi，但不需要接电脑。礼物摆放时可接普通 USB 充电器供电；这不启用 USB 数据模式。
- 每小时唤醒无线网络会显著缩短 PW3 的电池寿命；社区经验中高频更新只能维持约数天。若电池供电，建议改为 3 或 4 小时；若插墙充，可用 60 分钟。
- 电子墨水锁屏不会发光，暗处仍需环境光或手动开前光；持续点亮前光会进一步耗电。
- Online Screensaver 拉取失败时会保留上一张成功的图，因此网络暂时不可用不会变成空白屏。
