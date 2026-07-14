#!/bin/bash
# =========================================================================
# VM 端到端验证脚本
# 运行方式: bash scripts/vm_test.sh
# =========================================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }

PROJECT_DIR="/home/alistair/projects/health-portal"
cd "$PROJECT_DIR"

echo "============================================================"
echo "  VM 端到端验证 — 健康大数据门户"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"

# ── Step 1: Git 拉取最新 ──────────────────────────────────
echo; echo "━━━ Step 1: 拉取最新代码 ━━━"
info "当前 HEAD: $(git log --oneline -1)"
info "执行 git pull..."
git pull origin main
info "最新 HEAD: $(git log --oneline -1)"

# ── Step 2: Python 语法检查 ────────────────────────────────
echo; echo "━━━ Step 2: Python 语法检查 ━━━"
for f in \
    blueprints/portal.py \
    blueprints/admin.py \
    blueprints/resource.py \
    blueprints/analysis.py \
    scripts/data_bridge.py \
    app.py; do
    if python3 -m py_compile "$f" 2>/dev/null; then
        pass "$f"
    else
        fail "$f → 检查错误信息"
        python3 -c "import ast; ast.parse(open('$f').read())" 2>&1 | tail -3
    fi
done

# ── Step 3: 关键文件存在性检查 ─────────────────────────────
echo; echo "━━━ Step 3: 文件完整性检查 ━━━"
check_file() {
    if [ -f "$1" ]; then pass "$1"; else fail "缺失: $1"; fi
}

check_file "templates/portal/news.html"
check_file "templates/portal/policy.html"
check_file "templates/portal/knowledge.html"
check_file "templates/portal/apps.html"
check_file "templates/portal/resources.html"
check_file "templates/portal/index.html"
check_file "templates/portal/dashboard.html"
check_file "data/analysis/institution_type.csv"
check_file "data/analysis/content_trend.csv"
check_file "data/analysis/medical_resources.csv"

# Hive DDL 文件
hive_count=$(ls sql/hive/*.sql 2>/dev/null | wc -l)
if [ "$hive_count" -eq 15 ]; then
    pass "sql/hive/ → $hive_count files"
else
    fail "sql/hive/ → $hive_count files (expected 15)"
    ls sql/hive/
fi

# ── Step 4: MySQL 数据库连通性 ─────────────────────────────
echo; echo "━━━ Step 4: MySQL 数据库验证 ━━━"
mysql -u portal -pportal123 -h 127.0.0.1 health_portal \
    -e "SELECT 'MySQL OK' AS status; SELECT COUNT(*) AS content_count FROM portal_content WHERE status=1; SELECT COUNT(*) AS resource_count FROM data_resource WHERE resource_status='已发布'; SELECT COUNT(*) AS app_count FROM application_info WHERE status=1; SELECT COUNT(*) AS user_count FROM sys_user;" 2>&1 | grep -v "Warning"

# ── Step 5: Flask 启动测试 ─────────────────────────────────
echo; echo "━━━ Step 5: Flask 导入测试 ━━━"
cd "$PROJECT_DIR"
python3 -c "
from app import create_app
app = create_app()
with app.test_client() as c:
    # 首页
    r = c.get('/')
    assert r.status_code == 200, f'GET / → {r.status_code}'
    print(f'  GET /            → {r.status_code} OK ({len(r.data)} bytes)')

    # 各门户页面
    for path in ['/news', '/policy', '/knowledge', '/apps', '/resources', '/dashboard']:
        r = c.get(path)
        status = 'OK' if r.status_code == 200 else f'FAIL({r.status_code})'
        print(f'  GET {path:15s} → {status} ({len(r.data)} bytes)')

    # API 端点
    for path in ['/api/contents?type=news', '/api/contents?type=policy',
                 '/api/contents?type=knowledge', '/api/resources',
                 '/api/health']:
        r = c.get(path)
        print(f'  GET {path:30s} → {r.status_code}')

    # 分析 API
    for path in ['/api/analysis/institution_by_region',
                 '/api/analysis/institution_type',
                 '/api/analysis/medical_resources',
                 '/api/analysis/content_trend',
                 '/api/analysis/resource_category']:
        r = c.get(path)
        print(f'  GET {path:40s} → {r.status_code}')

    # 后台
    r = c.get('/admin/login')
    print(f'  GET /admin/login  → {r.status_code}')

print()
print('All Flask routes tested.')
" 2>&1

# ── Step 6: API JSON 结构验证 ──────────────────────────────
echo; echo "━━━ Step 6: API JSON 响应结构验证 ━━━"
cd "$PROJECT_DIR"

# 启动临时 Flask 测试
python3 -c "
import json
from app import create_app
app = create_app()
with app.test_client() as c:
    # 6.1 内容 API
    r = c.get('/api/contents?type=news&pageSize=3')
    d = r.get_json()
    print(f'[6.1] /api/contents?type=news')
    print(f'      code={d.get(\"code\")}, total={d.get(\"total\")}')
    if d.get('data') and len(d['data']) > 0:
        item = d['data'][0]
        print(f'      first item keys: {list(item.keys())}')
        has_pub = 'publishing_date' in item
        print(f'      has publishing_date: {has_pub} {\"✅\" if has_pub else \"❌\"}')

    # 6.2 资源 API
    r = c.get('/api/resources')
    d = r.get_json()
    print(f'[6.2] /api/resources')
    print(f'      code={d.get(\"code\")}, total={d.get(\"total\")}')
    if d.get('data') and len(d['data']) > 0:
        print(f'      first item keys: {list(d[\"data\"][0].keys())}')

    # 6.3 分析 API
    for name in ['institution_by_region', 'institution_type', 'medical_resources',
                 'content_trend', 'resource_category']:
        r = c.get(f'/api/analysis/{name}')
        d = r.get_json()
        has_data = d.get('data') is not None
        print(f'[6.3] /api/analysis/{name:30s} code={d.get(\"code\")}, has_data={has_data}')
        if has_data and isinstance(d['data'], dict):
            print(f'      keys: {list(d[\"data\"].keys())[:5]}...')
        elif has_data and isinstance(d['data'], list):
            print(f'      items: {len(d[\"data\"])}')

    # 6.4 institution_type 数据真实性
    r = c.get('/api/analysis/institution_type')
    d = r.get_json()
    if d.get('data'):
        total = sum(item['value'] for item in d['data'])
        print(f'[6.4] institution_type total: {total:,}')
        if total > 1000000:  # 百万级 = 真实数据
            print(f'      ✅ Real data (> 1M)')
        else:
            print(f'      ❌ Looks like placeholder (< 1M)')
" 2>&1

# ── Step 7: CSV 数据验证 ───────────────────────────────────
echo; echo "━━━ Step 7: 分析 CSV 数据验证 ━━━"
python3 -c "
import pandas as pd, os
d = 'data/analysis'

# 7.1 institution_type 必须是真实数据
df = pd.read_csv(os.path.join(d, 'institution_type.csv'))
total = int(df['value'].sum())
print(f'[7.1] institution_type.csv: {len(df)} types, {total:,} total institutions')
print(f'      data: {df.to_dict(\"records\")}')
if total > 1000000:
    print(f'      ✅ Real data (10M+ institutions from DWD)')
else:
    print(f'      ❌ Placeholder?')

# 7.2 content_trend
df = pd.read_csv(os.path.join(d, 'content_trend.csv'))
print(f'[7.2] content_trend.csv: {len(df)} months, date range {df[\"month\"].min()} ~ {df[\"month\"].max()}')

# 7.3 medical_resources
df = pd.read_csv(os.path.join(d, 'medical_resources.csv'))
print(f'[7.3] medical_resources.csv: {len(df)} regions, cols={list(df.columns)}')

# 7.4 institution_by_region
df = pd.read_csv(os.path.join(d, 'institution_by_region.csv'))
print(f'[7.4] institution_by_region.csv: {len(df)} regions, total {int(df[\"count\"].sum()):,} institutions')
" 2>&1

# ── Step 8: Hive DDL 语法验证 (dry-run) ────────────────────
echo; echo "━━━ Step 8: Hive DDL 语法检查 ━━━"
info "检查 15 个 DDL 文件的结构完整性..."

passed=0; failed=0
for f in sql/hive/*.sql; do
    fname=$(basename "$f")
    # check CREATE TABLE exists
    if grep -q "CREATE.*TABLE" "$f"; then
        has_create="CREATE"
    else
        has_create="MISSING_CREATE"
    fi
    # check INSERT or LOCATION (ODS 没有 INSERT)
    if echo "$fname" | grep -q "^ods_"; then
        if grep -q "LOCATION" "$f"; then
            has_insert="LOCATION"
        else
            has_insert="MISSING_LOCATION"
        fi
    else
        if grep -q "INSERT" "$f"; then
            has_insert="INSERT"
        else
            has_insert="MISSING_INSERT"
        fi
    fi
    if [ "$has_create" != "CREATE" ] || echo "$has_insert" | grep -q "MISSING"; then
        fail "$fname ($has_create, $has_insert)"
        ((failed++))
    else
        ((passed++))
    fi
done
pass "$passed/$((passed+failed)) DDL files pass structure check"

# ── Step 9: 数据桥接脚本测试 ───────────────────────────────
echo; echo "━━━ Step 9: data_bridge.py 测试 ━━━"
cd "$PROJECT_DIR"
python3 scripts/data_bridge.py 2>&1

# ── Step 10: 汇总 ──────────────────────────────────────────
echo; echo "============================================================"
echo "  验证完成 — $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo "  检查上面的输出，确认没有 [FAIL] 项目。"
echo "  如有 FAIL，请将对应错误信息发给组长排查。"
echo ""
echo "  如果全部 PASS，执行以下命令重启服务："
echo "    sudo systemctl restart health-portal"
echo "    curl -s http://192.168.132.128/ | head -20"
