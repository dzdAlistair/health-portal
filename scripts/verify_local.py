"""本地验证脚本 — 检查 Python 语法、CSV 数据完整性"""
import os
import sys
import ast

REF = r'D:\health-portal-reference'

print('=' * 60)
print('1. Python 语法检查')
print('=' * 60)

py_files = [
    os.path.join(REF, 'blueprints', 'portal.py'),
    os.path.join(REF, 'scripts', 'data_bridge.py'),
    os.path.join(REF, 'app.py'),
    os.path.join(REF, 'blueprints', 'resource.py'),
    os.path.join(REF, 'blueprints', 'analysis.py'),
    os.path.join(REF, 'blueprints', 'admin.py'),
]

for f in py_files:
    if not os.path.exists(f):
        print(f'  ❌ MISSING: {f}')
        continue
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            source = fh.read()
        ast.parse(source)
        rel = os.path.relpath(f, REF)
        print(f'  ✅ {rel}')
    except SyntaxError as e:
        print(f'  ❌ SYNTAX ERROR {os.path.relpath(f, REF)}: {e}')

print()
print('=' * 60)
print('2. 桥接 CSV 数据验证')
print('=' * 60)

analysis_dir = os.path.join(REF, 'data', 'analysis')
required = [
    'institution_by_region.csv',
    'institution_type.csv',
    'medical_resources.csv',
    'content_trend.csv',
    'resource_category.csv',
]

import pandas as pd
for csv_name in required:
    path = os.path.join(analysis_dir, csv_name)
    if not os.path.exists(path):
        print(f'  ❌ {csv_name}: MISSING')
        continue
    df = pd.read_csv(path)
    print(f'  ✅ {csv_name}: {len(df)} rows, cols={list(df.columns)}')
    if csv_name == 'institution_type.csv':
        print(f'     data: {df.to_dict("records")}')
        total = int(df['value'].sum())
        print(f'     total: {total:,}')

print()
print('=' * 60)
print('3. 门户模板文件')
print('=' * 60)

templates_dir = os.path.join(REF, 'templates', 'portal')
expected = ['index.html', 'news.html', 'policy.html', 'knowledge.html',
            'apps.html', 'resources.html', 'dashboard.html']
for tpl in expected:
    path = os.path.join(templates_dir, tpl)
    exists = os.path.exists(path)
    status = '✅' if exists else '❌'
    print(f'  {status} {tpl}')

print()
print('=' * 60)
print('4. Hive DDL 文件')
print('=' * 60)

hive_dir = os.path.join(REF, 'sql', 'hive')
if os.path.exists(hive_dir):
    files = sorted(os.listdir(hive_dir))
    ods = [f for f in files if f.startswith('ods_')]
    dwd = [f for f in files if f.startswith('dwd_')]
    ads = [f for f in files if f.startswith('ads_')]
    print(f'  ODS: {len(ods)} files — {ods}')
    print(f'  DWD: {len(dwd)} files — {dwd}')
    print(f'  ADS: {len(ads)} files — {ads}')
    print(f'  Total: {len(files)} files')

    # Check each has CREATE TABLE
    for f in sorted(files):
        path = os.path.join(hive_dir, f)
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        has_create = 'CREATE' in content
        has_insert = 'INSERT' in content if not f.startswith('ods_') else True
        print(f'  {"✅" if has_create else "❌"} {f}: CREATE={has_create}, INSERT={has_insert}')
else:
    print('  ❌ sql/hive/ directory missing')

print()
print('=' * 60)
print('5. portal.py 路由数验证')
print('=' * 60)

portal_py = os.path.join(REF, 'blueprints', 'portal.py')
with open(portal_py, 'r', encoding='utf-8') as f:
    content = f.read()
route_count = content.count('@portal_bp.route(')
print(f'  Routes defined: {route_count}')
print(f'  Expected: 7 (/, /news, /policy, /knowledge, /apps, /resources, /dashboard)')

print()
print('Done.')
