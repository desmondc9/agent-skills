# analyze-dip 参考素材

[analyze-dip](../../analyze-dip/) skill 的原始来源材料。

## 来源视频

- **标题**：AI硬件股暴跌，现在该抄底还是逃命？我的10步判断框架
- **URL**：https://www.youtube.com/watch?v=YexGncrFyRU
- **案例**：以美光（Micron, MU）贯穿讲解 10 步判断框架

视频文件本身不入库（太大）。`transcript.txt` 为完整中文转录稿（含 `[mm:ss]` 时间戳），SKILL.md / REFERENCE.md 的 10 步框架即从该稿提取。

## 转录方式

- 工具：whisperx，模型 `large-v3`，`--language zh --compute_type int8 --batch_size 4 --condition_on_previous_text False`
- 转录日期：2026-07-19
- 原始音频为 16 kHz 单声道 WAV（ffmpeg 从 webm 提取，约 17 分钟）
- 转录稿未经人工校对，个别专有名词可能有误（如 "growth margin" 应为 gross margin）
