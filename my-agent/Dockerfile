FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8787 8501

# 合并部署:FastAPI (8787) + Streamlit (8501) 同容器
CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8787 & streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"]
