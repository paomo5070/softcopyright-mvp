"""
软著工厂 - 查重校验模块
AST 结构对比 + 文档语义相似度
"""

import ast
import os
import json
from collections import Counter
from difflib import SequenceMatcher


def extract_ast_features(code: str) -> dict:
    """从 Python 代码提取 AST 结构特征"""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"valid": False}

    features = {
        "valid": True,
        "functions": [],
        "classes": [],
        "imports": [],
        "control_flow": [],
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            features["functions"].append({"name": node.name, "args": args, "lines": node.end_lineno - node.lineno})
        elif isinstance(node, ast.ClassDef):
            bases = [b.id if isinstance(b, ast.Name) else "?" for b in node.bases]
            features["classes"].append({"name": node.name, "bases": bases})
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    features["imports"].append(alias.name)
            else:
                module = node.module or ""
                features["imports"].append(module)
        elif isinstance(node, (ast.For, ast.While, ast.If, ast.Try, ast.With)):
            features["control_flow"].append(type(node).__name__)

    return features


def ast_similarity(code_a: str, code_b: str) -> float:
    """比较两段代码的 AST 结构相似度"""
    feat_a = extract_ast_features(code_a)
    feat_b = extract_ast_features(code_b)

    if not feat_a["valid"] or not feat_b["valid"]:
        return 0.0

    scores = []

    # 函数签名相似度
    sigs_a = set(f"{f['name']}({len(f['args'])})" for f in feat_a["functions"])
    sigs_b = set(f"{f['name']}({len(f['args'])})" for f in feat_b["functions"])
    if sigs_a or sigs_b:
        scores.append(len(sigs_a & sigs_b) / max(len(sigs_a | sigs_b), 1))

    # 类名相似度
    cls_a = set(c["name"] for c in feat_a["classes"])
    cls_b = set(c["name"] for c in feat_b["classes"])
    if cls_a or cls_b:
        scores.append(len(cls_a & cls_b) / max(len(cls_a | cls_b), 1))

    # 控制流模式相似度
    cf_a = Counter(feat_a["control_flow"])
    cf_b = Counter(feat_b["control_flow"])
    if cf_a or cf_b:
        all_keys = set(cf_a.keys()) | set(cf_b.keys())
        diffs = sum(abs(cf_a.get(k, 0) - cf_b.get(k, 0)) for k in all_keys)
        total = sum(cf_a.get(k, 0) + cf_b.get(k, 0) for k in all_keys)
        scores.append(1 - diffs / max(total, 1))

    return sum(scores) / max(len(scores), 1)


def text_similarity(text_a: str, text_b: str) -> float:
    """文本相似度（用于文档比对）"""
    return SequenceMatcher(None, text_a, text_b).ratio()


def check_project(project_dir: str, existing_dirs: list = None) -> dict:
    """
    检查项目的代码质量和与已有项目的相似度。
    返回: {"ast_valid": bool, "total_lines": int, "similarities": [...], "passed": bool}
    """
    code_dir = os.path.join(project_dir, "code")
    if not os.path.exists(code_dir):
        return {"ast_valid": False, "error": "code 目录不存在"}

    results = {
        "ast_valid": True,
        "file_count": 0,
        "total_lines": 0,
        "files": [],
        "similarities": [],
        "passed": True,
    }

    # AST 校验
    for root, dirs, files in os.walk(code_dir):
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            full_path = os.path.join(root, f)
            with open(full_path, "r", encoding="utf-8") as fh:
                code = fh.read()

            try:
                ast.parse(code)
                status = "✅"
            except SyntaxError as e:
                status = f"❌ {e}"
                results["ast_valid"] = False
                results["passed"] = False

            lines = len([l for l in code.split("\n") if l.strip()])
            results["file_count"] += 1
            results["total_lines"] += lines
            results["files"].append({"path": f, "lines": lines, "status": status})

    # 与已有项目对比
    if existing_dirs:
        current_codes = {}
        for root, dirs, files in os.walk(code_dir):
            for f in files:
                if f.endswith(".py"):
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fh:
                        current_codes[f] = fh.read()

        for exist_dir in existing_dirs:
            exist_code_dir = os.path.join(exist_dir, "code")
            if not os.path.exists(exist_code_dir):
                continue

            for root, dirs, files in os.walk(exist_code_dir):
                for f in files:
                    if f.endswith(".py") and f in current_codes:
                        with open(os.path.join(root, f), "r", encoding="utf-8") as fh:
                            exist_code = fh.read()
                        sim = ast_similarity(current_codes[f], exist_code)
                        if sim > 0.3:
                            results["similarities"].append({
                                "file": f,
                                "other_project": os.path.basename(exist_dir),
                                "similarity": round(sim, 3),
                            })

    # 最终判定
    max_sim = max((s["similarity"] for s in results["similarities"]), default=0)
    if max_sim > 0.4:
        results["passed"] = False

    return results


def main():
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 checker.py <project_dir> [existing_project_dir1] [existing_project_dir2] ...")
        sys.exit(1)

    project_dir = sys.argv[1]
    existing_dirs = sys.argv[2:] if len(sys.argv) > 2 else []

    result = check_project(project_dir, existing_dirs)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["passed"]:
        print("\n⚠️  项目未通过检查！")
        sys.exit(1)
    else:
        print(f"\n✅ 检查通过: {result['file_count']} 个文件, {result['total_lines']} 行")


if __name__ == "__main__":
    main()
