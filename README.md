# 百合会论坛图片下载器

从 [百合会论坛](https://bbs.yamibo.com) 按顺序批量下载帖子中的图片。

## 依赖

```bash
pip install requests
```

## 使用方法

### 1. 获取 Cookie（只需一次）

1. 浏览器打开 [百合会](https://bbs.yamibo.com) 并登录
2. 按 `F12` 打开开发者工具
3. 切换到「网络 / Network」标签
4. 刷新页面，点击列表中任意一个请求
5. 在「请求标头 / Request Headers」中找到 `Cookie` 行
6. 复制 `Cookie:` 后面的整行值

### 2. 下载图片

URL 必须用双引号包裹（PowerShell 中 `&` 是特殊字符）：

```powershell
python yamibo_downloader.py "<帖子URL>" [保存目录]
```

示例：

```powershell
# 默认保存到 ~/Downloads
python yamibo_downloader.py "https://bbs.yamibo.com/forum.php?mod=viewthread&tid=568319"

# 指定保存目录
python yamibo_downloader.py "https://bbs.yamibo.com/forum.php?mod=viewthread&tid=568319" "D:\漫画"
```

首次运行会提示粘贴 Cookie，之后自动记住。

### 3. 清除 Cookie

Cookie 过期时执行：

```bash
python yamibo_downloader.py reset
```

然后重新运行下载命令，会提示粘贴新的 Cookie。

## 功能

- 只下载帖子正文中的图片（自动忽略头像、表情等）
- 自动检测并遍历分页（多页帖子）
- 按帖子顺序命名：`001.jpg`, `002.jpg`, ...
- 自动用帖子标题创建文件夹
- Cookie 本地保存，无需重复粘贴
- 超时自动重试（最多 3 次）
- 已存在的文件自动跳过，重跑命令只补下载失败的

## 输出示例

```
时间: 2026-08-02 23:00:00
链接: https://bbs.yamibo.com/forum.php?mod=viewthread&tid=568319
正在获取帖子...
  读取分页...
标题: [くずしろ]雨夜明月/雨夜の月 第46話 対話 - 百合漫画图源区 - 百合会
共 32 张 → D:\漫画\[くずしろ]雨夜明月_雨夜の月 第46話 対話
--------------------------------------------------
[001/32] 001.jpg (699.5 KB)
[002/32] 002.jpg (670.9 KB)
...
[032/32] 032.jpg (596.9 KB)
--------------------------------------------------
完成! 成功 32/32 张 (新下载 32, 已存在 0)
保存位置: D:\漫画\[くずしろ]雨夜明月_雨夜の月 第46話 対話
日志已保存: D:\漫画\[くずしろ]雨夜明月_雨夜の月 第46話 対話\download_log.txt
```

下载完成后会在图片目录生成 `download_log.txt` 日志文件，记录每张图片的下载状态。

## 注意事项

- Cookie 有效期有限，过期后需重新获取
- 配置保存在 `~/.yamibo/config.json`，删除该文件即清除 Cookie
- 下载间隔 0.3 秒，避免请求过快被限制
- 如果部分图片下载失败，重新运行同一命令即可自动跳过已下载的，只补下载失败的
