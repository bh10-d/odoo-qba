#!/usr/bin/env bash

# ==============================================================================
# Script Khôi Phục (Restore) Database Odoo từ file dump.sql
# Sử dụng Docker Compose
# ==============================================================================

set -e

# Cấu hình mặc định
DB_NAME="${1:-qba}"
DUMP_FILE="${2:-dump.sql}"
DB_USER="odoo"
COMPOSE_SERVICE="postgres"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "          QBA ODOO - DATABASE RESTORE TOOL"
echo "=========================================================="
echo " - Database target : $DB_NAME"
echo " - Dump file       : $DUMP_FILE"
echo " - Postgres service: $COMPOSE_SERVICE"
echo "=========================================================="

# 1. Kiểm tra file dump tồn tại
if [ ! -f "$DUMP_FILE" ]; then
    echo "Lỗi: Không tìm thấy file dump '$DUMP_FILE' tại: $SCRIPT_DIR"
    echo "Vui lòng đặt file dump.sql vào thư mục environment/ hoặc truyền đường dẫn file:"
    echo "   ./restore.sh [tên_database] [đường_dẫn_file_dump]"
    exit 1
fi

# 2. Kiểm tra container Postgres đang chạy
echo "Đang kiểm tra container Postgres..."
if ! docker compose ps --services --filter "status=running" | grep -q "$COMPOSE_SERVICE"; then
    echo "Container '$COMPOSE_SERVICE' chưa chạy. Đang khởi động..."
    docker compose up -d "$COMPOSE_SERVICE"
    echo "Đang chờ Postgres sẵn sàng..."
    sleep 3
fi

# 3. Ngắt kết nối hiện tại và tái tạo Database sạch
echo "Đang dọn dẹp các kết nối cũ và tạo mới database '$DB_NAME'..."
docker compose exec -T "$COMPOSE_SERVICE" psql -U "$DB_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" > /dev/null 2>&1 || true

docker compose exec -T "$COMPOSE_SERVICE" psql -U "$DB_USER" -d postgres -c \
    "DROP DATABASE IF EXISTS \"$DB_NAME\";"

docker compose exec -T "$COMPOSE_SERVICE" psql -U "$DB_USER" -d postgres -c \
    "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"

# 4. Nạp dữ liệu từ file dump vào Database
echo "Đang nạp dữ liệu từ '$DUMP_FILE' vào database '$DB_NAME' (vui lòng chờ)..."
docker compose exec -T "$COMPOSE_SERVICE" psql -U "$DB_USER" -d "$DB_NAME" < "$DUMP_FILE" > /dev/null

echo "Khôi phục Database '$DB_NAME' thành công!"
echo "Khởi động hoặc khởi động lại Odoo bằng lệnh:"
echo "   docker compose restart odoo"
echo "=========================================================="
