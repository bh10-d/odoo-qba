# ========================================================
# STAGE 1: BUILDER (Nơi cài compiler và build Python venv)
# ========================================================
FROM python:3.12-slim-bookworm AS builder

COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

ENV PIP_NO_CACHE_DIR=1
WORKDIR /app

# Chỉ cài các gói phục vụ biên dịch (Build-essential và các gói -dev)
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install \
        build-essential \
        libfreetype6-dev \
        libharfbuzz-dev \
        libfribidi-dev \
        libjpeg62-turbo-dev \
        liblcms2-dev \
        libldap2-dev \
        libsasl2-dev \
        libopenjp2-7-dev \
        libpq-dev \
        libssl-dev \
        libtiff5-dev \
        libwebp-dev \
        libxcb1-dev \
        libxml2-dev \
        libxslt1-dev; \
    rm -rf /var/lib/apt/lists/*

RUN uv venv /app/.venv

# Tận dụng Cache của Docker cho dependencies
COPY requirements.txt /app/
RUN uv pip install --python /app/.venv/bin/python -r /app/requirements.txt


# ========================================================
# STAGE 2: RUNNER (Image thực tế chạy - Siêu nhẹ)
# ========================================================
FROM python:3.12-slim-bookworm AS runner

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

ENV LANG=en_US.UTF-8 \
    PATH="/app/.venv/bin:${PATH}" \
    ODOO_RC=/app/debian/odoo.conf

ARG TARGETARCH
WORKDIR /app

RUN set -eux; \
    useradd -ms /bin/bash odoo; \
    mkdir -p /var/lib/odoo ; \
    chown -R odoo:odoo /var/lib/odoo /app

# Chỉ cài các Runtime Libs cần thiết để chạy Odoo (Không có build-essential, không có gói -dev)
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install \
        ca-certificates \
        curl \
        dirmngr \
        fonts-noto-cjk \
        git \
        gnupg \
        node-less \
        npm \
        xz-utils \
        # Các thư viện liên kết động thay thế cho bản -dev ở trên
        libldap-2.5-0 \
        libsasl2-2 \
        libpq5 \
        libxml2 \
        libxslt1.1 \
        libjpeg62-turbo; \
    rm -rf /var/lib/apt/lists/*

# WKHTMLTOPDF
RUN set -eux; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64)   f="wkhtmltox_0.12.6.1-3.bookworm_amd64.deb" ;; \
      arm64)   f="wkhtmltox_0.12.6.1-3.bookworm_arm64.deb" ;; \
      ppc64el) f="wkhtmltox_0.12.6.1-3.bookworm_ppc64el.deb" ;; \
      i386)    f="wkhtmltox_0.12.6.1-3.bookworm_i386.deb" ;; \
      *) echo "Unsupported arch: $arch"; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/wkhtmltox.deb \
      "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/${f}"; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb; \
    rm -rf /var/lib/apt/lists/* /tmp/wkhtmltox.deb

# Postgres Client
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main' \
    > /etc/apt/sources.list.d/pgdg.list \
    && GNUPGHOME="$(mktemp -d)" \
    && export GNUPGHOME \
    && repokey='B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8' \
    && gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "${repokey}" \
    && gpg --batch --armor --export "${repokey}" > /etc/apt/trusted.gpg.d/pgdg.gpg.asc \
    && gpgconf --kill all \
    && rm -rf "$GNUPGHOME" \
    && apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# [BƯỚC QUAN TRỌNG 1]: Chỉ lấy folder môi trường ảo đã build sạch từ Stage Builder
COPY --from=builder --chown=odoo:odoo /app/.venv /app/.venv

# [BƯỚC QUAN TRỌNG 2]: Copy source code (Hãy nhớ tạo .dockerignore như hướng dẫn trước để chặn folder .venv ở ngoài máy host nhảy vào)
COPY --chown=odoo:odoo . /app

EXPOSE 8069 8071 8072
USER odoo

CMD ["python", "odoo-bin", "-c", "/app/debian/odoo.conf"]

