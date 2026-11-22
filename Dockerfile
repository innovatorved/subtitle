# Multi-stage production Dockerfile for subtitle-generator v4.0.0
# Portable binary (-DGGML_NATIVE=OFF), non-root user, ffmpeg + whisper-cli included.

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch develop https://github.com/innovatorved/whisper.cpp.git /tmp/whisper.cpp \
    && cmake -B /tmp/whisper.cpp/build -S /tmp/whisper.cpp \
       -DCMAKE_BUILD_TYPE=Release \
       -DBUILD_SHARED_LIBS=OFF \
       -DGGML_NATIVE=OFF \
       -DWHISPER_BUILD_EXAMPLES=ON \
       -DWHISPER_BUILD_TESTS=OFF \
    && cmake --build /tmp/whisper.cpp/build --config Release -j "$(nproc)"

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 subtitle

COPY --from=builder /tmp/whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper-cli
RUN chmod +x /usr/local/bin/whisper-cli

WORKDIR /app
COPY pyproject.toml PYPI_README.md LICENSE README.md /app/
COPY subtitle_generator /app/subtitle_generator
RUN pip install --no-cache-dir . \
    && mkdir -p /data/models /work \
    && chown -R subtitle:subtitle /data /work

ENV SUBTITLE_WHISPER_BINARY=/usr/local/bin/whisper-cli
ENV SUBTITLE_MODELS_DIR=/data/models

USER subtitle
VOLUME ["/data/models", "/work"]
WORKDIR /work

ENTRYPOINT ["subtitle"]
CMD ["--help"]
