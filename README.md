# Naipei 1.0 — 桌面宠物

一只基于 Python 的互动桌面宠物，以你的照片为原型生成 Naipei 精灵形象，漂浮在桌面上与你互动。

## 预览

桌面右下角会出现一只可爱的 Naipei 精灵，它会自动走动、跳跃，并对你的操作做出反应。

## 功能

### 基础交互
| 操作 | 效果 |
|------|------|
| 左键单击 | 弹跳 |
| 左键拖拽 | 移动精灵（松手后掉落回屏幕底部，带弹跳物理） |
| 左键双击 | 开心蹦跳 |
| 滚轮键（中键） | 发出狗叫声 |
| 鼠标滚轮 | 缩放大小（0.4x ~ 2.5x） |
| 右键单击 | 语音对话 |

### 红温系统
3 秒内连续快速点击 ≥ 8 次，精灵会：
- 全身变红
- 用男声喊出"别再搞我了！"
- 持续 3.5 秒后自动恢复

### 语音对话
右键点击 → 录音 3 秒 → Google 语音识别 → DeepSeek API 回复 → TTS 语音朗读

精灵会以小狗的口吻回答你的问题，比如询问天气、讲笑话等。

### 自动行为
- 每隔 2~5 秒随机跳跃
- 每隔 2~5 秒随机走动
- 走动时自动切换左右朝向

### 退出
将精灵拖拽到屏幕顶部松开即可退出。

## 安装与运行

### 依赖
```bash
pip install pillow pyttsx3 SpeechRecognition pyaudio pygame requests
```

### 运行
```bash
python desktop_pet.pyw
```

或直接双击 `desktop_pet.pyw`。

### 配置 DeepSeek API Key（语音对话必需）
设置环境变量 `DEEPSEEK_API_KEY`：
```powershell
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "sk-你的key", "User")
```
设置后重启终端/程序即可生效。未设置则语音对话功能不可用。

## 文件结构
```
naipei1.0/
  desktop_pet.pyw    # 主程序
  assets/
    pet.png          # 精灵图片（192x208）
    dog.mp3          # 狗叫声
  README.md
```

## 自定义精灵
替换 `assets/pet.png` 为你自己的 Naipei 角色图片，推荐 192x208 像素、透明背景。

替换 `assets/dog.mp3` 为你喜欢的声音效果。

## 技术栈
- Python 3.10+
- tkinter — 窗口 & 透明叠加
- PIL/Pillow — 图像处理
- pygame — 音频播放
- pyttsx3 — TTS 语音合成
- SpeechRecognition — 语音识别
- DeepSeek API — AI 对话

## License
MIT
