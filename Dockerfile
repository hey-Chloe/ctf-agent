FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

# 常用 CTF 工具。部分工具在不同 Debian 源中名称可能变化，构建失败时可按 README 调整。
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    wget \
    git \
    file \
    binutils \
    nmap \
    sqlmap \
    binwalk \
    steghide \
    tshark \
    john \
    hashcat \
    ruby-full \
    build-essential \
    libimage-exiftool-perl \
    openssh-client \
    netcat-openbsd \
    unzip \
    p7zip-full \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install pwntools requests pycryptodome dirsearch \
    && gem install zsteg

WORKDIR /work
CMD ["sleep", "infinity"]
