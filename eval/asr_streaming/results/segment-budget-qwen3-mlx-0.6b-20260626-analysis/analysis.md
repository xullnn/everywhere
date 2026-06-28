# Segment Budget ASR Analysis

## Metric Notes

- `wall_ms`: 墙钟耗时，单位毫秒；这里近似等于本次 final 文件级识别真实等待时间。
- `rtf`: 实时因子，等于墙钟耗时除以音频时长；小于 1 表示处理速度快于实时播放。
- `cer`: 字符错误率，越低越好；中文主要看这个。
- `wer`: 词/token 错误率，越低越好；中英混合时辅助观察英文和技术词。
- `expected_chars`: 标准答案归一化后的字符数量，可粗略代表这段音频里需要转写的文字内容量。
- `final_chars`: 模型输出归一化后的字符数量。

## Case Results

| case | axis | audio sec | expected chars | final chars | wall ms | RTF | CER | WER | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| budget_repeat_2x_66s | more_text_longer_audio | 65.835 | 244 | 244 | 1184.0 | 0.018 | 0.008 | 0.008 | ok |
| budget_repeat_3x_99s | more_text_longer_audio | 98.752 | 366 | 366 | 1860.1 | 0.019 | 0.008 | 0.008 | ok |
| budget_same_text_base_33s | same_text_base | 32.917 | 122 | 122 | 1246.4 | 0.038 | 0.008 | 0.008 | ok |
| budget_same_text_pad_60s | same_text_longer_audio | 60.000 | 122 | 122 | 786.0 | 0.013 | 0.008 | 0.008 | ok |
| budget_same_text_pad_120s | same_text_longer_audio | 120.000 | 122 | 122 | 1249.1 | 0.010 | 0.008 | 0.008 | ok |
| budget_silence_33s | silence_duration_only | 32.917 | 0 | 1 | 255.1 | 0.008 | - | - | ok |
| budget_silence_60s | silence_duration_only | 60.000 | 0 | 1 | 424.0 | 0.007 | - | - | ok |
| budget_silence_120s | silence_duration_only | 120.000 | 0 | 0 | 770.9 | 0.006 | 0.000 | 0.000 | no_text |

## Comparisons

- `same_text_base`: {"case_count": 1, "duration_to_wall_ms_slope_ms_per_audio_sec": null, "max_duration_seconds": 32.917, "max_wall_ms": 1246.3525426532735, "min_duration_seconds": 32.917, "min_wall_ms": 1246.3525426532735}
- `same_text_longer_audio`: {"case_count": 2, "duration_to_wall_ms_slope_ms_per_audio_sec": 7.719798597584789, "max_duration_seconds": 120.0, "max_wall_ms": 1249.145207926631, "min_duration_seconds": 60.0, "min_wall_ms": 785.9572920715436}
- `silence_duration_only`: {"case_count": 3, "duration_to_wall_ms_slope_ms_per_audio_sec": 5.899583643496786, "max_duration_seconds": 120.0, "max_wall_ms": 770.860041026026, "min_duration_seconds": 32.917, "min_wall_ms": 255.0584590062499}
- `more_text_longer_audio`: {"case_count": 2, "duration_to_wall_ms_slope_ms_per_audio_sec": 20.53965576664375, "max_duration_seconds": 98.752, "max_wall_ms": 1860.1429682194648, "min_duration_seconds": 65.835, "min_wall_ms": 1184.0391193488524}
- `overall`: {"duration_to_wall_ms_slope_ms_per_audio_sec": 6.015665039942991, "text_length_to_wall_ms_slope_ms_per_char": 3.5393626769707627}

## Recommendation

- 同样文字后面补静音仍然会增加处理耗时，所以不能只按已转写文字长度切段。
- 纯静音随时长变长也有可见成本，说明音频时长本身就是必须受控的资源。
- 重复内容组的耗时增长高于补静音组，说明文字/内容量也会带来额外成本。
- 建议后续分段采用混合预算：硬性音频时长上限 + 软性文字长度上限 + 静音/标点边界优先切分，而不是只用两分钟或只用字数。
- 这组是 compute-isolation pilot；最终产品阈值还需要至少重复跑 2-3 次，并加入自然长语音样本。
