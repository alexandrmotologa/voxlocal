FROM python:3.12-slim

# Install system audio dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    libasound2-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY pyproject.toml .
COPY README.md .
COPY LICENSE .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Copy application source code
COPY src/ src/
COPY docs/ docs/

ENTRYPOINT ["voxlocal"]
CMD ["--help"]
