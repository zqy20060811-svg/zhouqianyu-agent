FROM python:3.12-slim

# 构建时可传入 --build-arg PIP_INDEX_URL 覆盖;默认用清华镜像(国内服务器直连 pypi.org 仅几十 kB/s)
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 预置 Chroma embedding 模型包(约83MB,通过 scp 放到 .chroma-model/ 后构建),
# 有此文件则纯本地解压不联网;缺失时回退为联网下载
COPY .chroma-model/ /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/
RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()(['warmup'])" \
    || echo "WARN: embedding model predownload failed, runtime will retry"

COPY . .

EXPOSE 8787 8501

# 合并部署:FastAPI (8787) + Streamlit (8501) 同容器
CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8787 & streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"]
