"""批量生成剩余代码文件"""
import json, os, ast, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_client import call_ai_json

PROJECT = 'projects/陕西云长科技信息有限公司_运维管理智能问答系统'

with open(f'{PROJECT}/p1_insight.json', 'r') as f:
    p1 = json.load(f)
with open(f'{PROJECT}/p2_architecture.json', 'r') as f:
    p2 = json.load(f)

with open('prompts/coder.txt', 'r') as f:
    p3_system = f.read()

style_seed = json.dumps(p1.get('style_seed', {}), ensure_ascii=False)
terminology = json.dumps(p1.get('terminology_map', {}), ensure_ascii=False)
mock_schema = json.dumps(p1.get('mock_data_schema', {}), ensure_ascii=False)

files = p2.get('file_tree', [])
code_dir = f'{PROJECT}/code'

# 加载已生成的
generated = []
existing_paths = set()
for root, dirs, fnames in os.walk(code_dir):
    for fn in sorted(fnames):
        if fn.endswith('.py'):
            fp = os.path.join(root, fn)
            with open(fp, 'r') as f:
                content = f.read()
            rel = os.path.relpath(fp, code_dir)
            lines = len([l for l in content.split('\n') if l.strip()])
            generated.append({'file_path': rel, 'content': content, 'line_count': lines})
            existing_paths.add(rel)

print(f'已有: {len(generated)} 个文件, {sum(g["line_count"] for g in generated)} 行')
remaining = [f for f in files if f.get('path') not in existing_paths]
print(f'待生成: {len(remaining)} 个文件')
print()

total_tokens = 0
for i, file_info in enumerate(remaining):
    file_path = file_info.get('path', f'unknown_{i}.py')
    print(f'[{i+1}/{len(remaining)}] {file_path} ...', end='', flush=True)

    related = ''
    for dep in file_info.get('depends_on', []):
        dep_name = dep.split('/')[-1]
        for g in generated:
            if g['file_path'].endswith(dep_name):
                related += f'\n--- {dep} ---\n{g["content"][:400]}...\n'

    prompt = (
        f'## 风格配置\n{style_seed}\n\n'
        f'## 术语映射\n{terminology}\n\n'
        f'## 数据 Schema\n{mock_schema}\n\n'
        f'## 当前文件\n{json.dumps(file_info, ensure_ascii=False)}\n\n'
        f'## 已生成的相关文件摘要\n{related if related else "（无）"}\n\n'
        f'请生成这个文件的完整源代码。'
    )

    for attempt in range(3):
        try:
            result = call_ai_json(prompt, system_prompt=p3_system)
            total_tokens += result['tokens']
            code = result['parsed'].get('content', '')

            if file_path.endswith('.py'):
                ast.parse(code)

            full = os.path.join(code_dir, file_path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, 'w', encoding='utf-8') as f:
                f.write(code)

            actual = len([l for l in code.split('\n') if l.strip()])
            generated.append({'file_path': file_path, 'content': code, 'line_count': actual})
            print(f' ✅ {actual}行 ({result["elapsed"]}s, {result["tokens"]}t)')
            break
        except SyntaxError as e:
            if attempt < 2:
                print(f' 语法错误重试...', end='', flush=True)
            else:
                print(f' ❌ 语法错误: {e}')
        except Exception as e:
            if attempt < 2:
                print(f' 重试...', end='', flush=True)
            else:
                print(f' ❌ {e}')

total_lines = sum(g['line_count'] for g in generated)
print(f'\n{"="*50}')
print(f'✅ P3 全部完成')
print(f'  文件数: {len(generated)} / {len(files)}')
print(f'  总行数: {total_lines}')
print(f'  本轮Token: {total_tokens}')
