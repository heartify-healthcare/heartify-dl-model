# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM python:3.10-slim AS builder

WORKDIR /app

# 1. Cài đặt git và build tools (Cần thiết để compile Fairseq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev python3-dev git build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Clone các Repo hỗ trợ
# Xóa .git ngay lập tức để giảm dung lượng
RUN git clone https://github.com/facebookresearch/fairseq.git && \
    cd fairseq && \
    git checkout v0.12.2 && \
    rm -rf .git && \
    cd .. && \
    git clone https://github.com/Jwoo5/fairseq-signals.git && \
    cd fairseq-signals && \
    rm -rf .git && \
    cd ..

# 3. Tạo venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# --- CHIẾN THUẬT GIẢM SIZE (QUAN TRỌNG) ---

# Bước 4.1: Cài đặt PyTorch CPU-only TRƯỚC TIÊN
# QUAN TRỌNG: Cài đặt pip < 24.1 để tránh lỗi "invalid metadata" của omegaconf/fairseq cũ
RUN pip install --no-cache-dir "pip<24.1" && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Bước 4.2: "Phẫu thuật" file requirements.txt
# Xóa bỏ mọi dòng chứa 'torch' để pip không bao giờ tải lại bản GPU từ PyPI
RUN sed -i '/torch/d' requirements.txt && \
    sed -i '/torchvision/d' requirements.txt && \
    sed -i '/torchaudio/d' requirements.txt

# Bước 4.3: Cài đặt requirements còn lại
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir huggingface_hub python-dotenv

# Bước 4.4: Cài đặt Fairseq (Thủ phạm tiềm ẩn)
# FIX LỖI: Cài đặt Cython và Numpy TRƯỚC khi build Fairseq
# Fairseq cần Cython để generate file .cpp từ .pyx
# Sử dụng cython<3 vì fairseq 0.12.2 thường lỗi với cython 3.x
RUN pip install --no-cache-dir "cython<3" numpy setuptools && \
    cd fairseq && \
    pip install --no-cache-dir --no-build-isolation .

ARG HF_REPO_ID="minhphuc2544/classify-model"
ARG HF_FILENAME="classify_model.pth"

RUN mkdir -p model
RUN python -c "from huggingface_hub import hf_hub_download; \
    hf_hub_download( \
        repo_id='${HF_REPO_ID}', \
        filename='${HF_FILENAME}', \
        local_dir='model', \
        local_dir_use_symlinks=False, \
    )"

# ==========================================
# STAGE 2: RUNNER (Production)
# ==========================================
FROM python:3.10-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Runtime system libs (Chỉ cần lib để chạy, không cần gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 1. Copy Virtual Environment (Lúc này venv sẽ chỉ tầm 1GB)
COPY --from=builder /opt/venv /opt/venv

# 2. Copy Source Code của Repo phụ
# Vì code của bạn dùng sys.path.insert nên vẫn cần giữ folder source này
COPY --from=builder /app/fairseq ./fairseq
COPY --from=builder /app/fairseq-signals ./fairseq-signals

# 3. Copy Source Code chính & Config
COPY wsgi.py .
COPY app ./app

COPY --from=builder /app/model ./model
# COPY .env . (Nếu test local)

RUN adduser --disabled-password --gecos "" aiuser
USER aiuser

EXPOSE 5000

CMD ["python", "wsgi.py"]