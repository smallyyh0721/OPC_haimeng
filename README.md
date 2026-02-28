# Replicate API 测试脚本

该仓库提供 `test_replicate_fullbody.py`，用于按 Replicate 官方流程：
1. 上传参考图到 `POST /v1/files`
2. 调用模型进行图生图
3. 轮询预测结果并输出生成图片 URL

## 使用方式

```bash
export REPLICATE_API_TOKEN='你的 token'
python test_replicate_fullbody.py --reference /path/to/reference.jpg
```

可选参数：
- `--model`：默认 `black-forest-labs/flux-kontext-max`
- `--prompt`：默认提示词会要求生成全身照

## 说明

当前脚本只依赖 Python 标准库（`urllib`），不需要额外安装 `replicate` 包，适用于受限环境。
