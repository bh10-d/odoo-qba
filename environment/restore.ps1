<#
.SYNOPSIS
    Script Restore Database Odoo tren Windows PowerShell tu file dump.sql
#>
param(
    [string] = 'qba',
    [string] = 'dump.sql'
)

Continue = 'Stop'
Set-Location -Path 

Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host '          QBA ODOO - DATABASE RESTORE TOOL (PowerShell)' -ForegroundColor Cyan
Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host (' - Database target : ' + )
Write-Host (' - Dump file       : ' + )
Write-Host ' - Postgres service: postgres'
Write-Host '=========================================================='

if (-not (Test-Path -Path )) {
    Write-Host ('Loi: Khong tim thay file dump ' +  + ' tai ' + ) -ForegroundColor Red
    exit 1
}

Write-Host 'Dang kiem tra container Postgres...' -ForegroundColor Yellow
 = docker compose ps --services --filter 'status=running'
if ( -notcontains 'postgres') {
    Write-Host 'Container postgres chua chay. Dang khoi dong...' -ForegroundColor Yellow
    docker compose up -d postgres
    Start-Sleep -Seconds 3
}

Write-Host ('Dang don dep cac ket noi cu va tao moi database ' +  + '...') -ForegroundColor Yellow
docker compose exec -T postgres psql -U odoo -d postgres -c ('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = ''' +  + ''' AND pid <> pg_backend_pid();') 2>$null | Out-Null
docker compose exec -T postgres psql -U odoo -d postgres -c ('DROP DATABASE IF EXISTS "  + $DbName +  \;')
docker compose exec -T postgres psql -U odoo -d postgres -c ('CREATE DATABASE \ + $DbName + \ OWNER \odoo\;')

Write-Host ('Dang nap du lieu tu ' + + ' vao database ' + + ' (vui long cho)...') -ForegroundColor Yellow
Get-Content -Path -Raw | docker compose exec -T postgres psql -U odoo -d 2>$null | Out-Null

Write-Host ('Khoi phuc Database ' + + ' thanh cong!') -ForegroundColor Green
Write-Host 'Khoi dong hoac khoi dong lai Odoo bang lenh:'
Write-Host ' docker compose restart odoo' -ForegroundColor Cyan
Write-Host '=========================================================='
