# Chroma Embedding 模型预置目录

构建镜像前，把 Chroma 默认 embedding 模型包（all-MiniLM-L6-v2，约 83MB）放到本目录：

```
.chroma-model/onnx.tar.gz
```

获取方式（任选其一）：
1. 从本地机器上传（本地首次运行 RAG 后会自动下载到 `%USERPROFILE%\.cache\chroma\onnx_models\all-MiniLM-L6-v2\onnx.tar.gz`）：
   `scp "$env:USERPROFILE\.cache\chroma\onnx_models\all-MiniLM-L6-v2\onnx.tar.gz" <user>@<server>:/opt/my-agent/my-agent/.chroma-model/onnx.tar.gz`
2. 服务器能联网时，构建阶段会自动从 S3 下载，此文件可省略。

onnx.tar.gz 不进 git（见 .gitignore）。
