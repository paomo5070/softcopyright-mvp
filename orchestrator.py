"""
软著工厂 - Orchestrator（中控状态机）
用法: python3 orchestrator.py "公司全称" "软件名称"
"""

import ast
import json
import os
import sys
import time

from ai_client import call_ai, call_ai_json


# ── 配置 ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")


def load_prompt(name: str) -> str:
    path = os.path.join(PROMPTS_DIR, f"{name}.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def approve(stage_name: str, summary: str) -> bool:
    """门控审批：展示摘要，等待老板确认"""
    print(f"\n{'='*60}")
    print(f"📌 阶段：{stage_name}")
    print(f"{'='*60}")
    print(summary)
    print(f"{'='*60}")
    while True:
        choice = input("👉 输入 y 通过 / n 重做 / q 退出: ").strip().lower()
        if choice in ("y", "n", "q"):
            return choice == "y"
        print("   请输入 y、n 或 q")


class SoftCopyrightFactory:
    """软著工厂主控"""

    def __init__(self, company_name: str, software_name: str):
        self.company = company_name
        self.software = software_name
        safe_name = f"{company_name}_{software_name}".replace(" ", "_")[:50]
        self.project_dir = os.path.join(PROJECTS_DIR, safe_name)
        self.cost_log = {"p1": {}, "p2": {}, "p3": [], "p4": {}, "p5": {}}
        self.total_tokens = 0
        self.total_time = 0

        os.makedirs(self.project_dir, exist_ok=True)
        os.makedirs(os.path.join(self.project_dir, "code"), exist_ok=True)
        os.makedirs(os.path.join(self.project_dir, "screenshots"), exist_ok=True)
        os.makedirs(os.path.join(self.project_dir, "package"), exist_ok=True)

    def _log_cost(self, stage: str, result: dict):
        tokens = result.get("tokens", 0)
        elapsed = result.get("elapsed", 0)
        self.total_tokens += tokens
        self.total_time += elapsed
        print(f"   💰 Token: {tokens} | 耗时: {elapsed}s | 累计: {self.total_tokens} tokens")

    def _save_json(self, filename: str, data: dict):
        path = os.path.join(self.project_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   💾 已保存: {path}")
        return path

    def _load_json(self, filename: str) -> dict:
        path = os.path.join(self.project_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ── P1: 分析师 ────────────────────────────────────
    def run_p1(self) -> dict:
        """阶段 1：企业画像与需求分析"""
        system = load_prompt("analyst")
        user_prompt = f"公司全称：{self.company}\n软件名称：{self.software}\n\n请完成企业画像分析，输出完整的 JSON。"

        while True:
            result = call_ai_json(user_prompt, system_prompt=system)
            self._log_cost("p1", result)
            data = result["parsed"]

            # 构建审批摘要
            profile = data.get("company_profile", {})
            seed = data.get("style_seed", {})
            entities = data.get("mock_data_schema", {}).get("entities", [])
            summary = (
                f"📊 P1 企业画像\n"
                f"  行业: {profile.get('industry', '?')}\n"
                f"  标签: {', '.join(profile.get('business_tags', []))}\n"
                f"  风格: {seed.get('code_personality', '?')} / {seed.get('paradigm_bias', '?')}\n"
                f"  语言: {seed.get('language', '?')} / {seed.get('naming_convention', '?')}\n"
                f"  数据实体: {len(entities)} 个 ({', '.join(e.get('name','') for e in entities)})\n"
                f"  功能点: {len(data.get('feature_outline', []))} 个\n"
                f"  开发必要性: {profile.get('software_purpose', '?')[:80]}..."
            )

            if approve("P1 - 企业画像与需求分析", summary):
                self._save_json("p1_insight.json", data)
                return data
            print("   🔄 重新生成...")

    # ── P2: 架构师 ────────────────────────────────────
    def run_p2(self, p1_data: dict) -> dict:
        """阶段 2：架构设计与文件清单"""
        system = load_prompt("architect")
        user_prompt = f"请根据以下分析师输出，设计完整的项目架构：\n\n{json.dumps(p1_data, ensure_ascii=False, indent=2)}"

        while True:
            result = call_ai_json(user_prompt, system_prompt=system)
            self._log_cost("p2", result)
            data = result["parsed"]

            # 构建审批摘要
            files = data.get("file_tree", [])
            total_lines = sum(f.get("line_target", 0) for f in files)
            modules = data.get("module_groups", {})
            summary = (
                f"🏗️ P2 架构设计\n"
                f"  项目: {data.get('project_info', {}).get('name', '?')}\n"
                f"  文件数: {len(files)} 个\n"
                f"  目标总行数: {total_lines} 行\n"
                f"  模块组: {', '.join(modules.keys())}\n"
                f"  架构说明: {data.get('architecture_notes', '?')[:100]}..."
            )

            # 自动校验
            issues = []
            if len(files) < 15:
                issues.append(f"文件数不足: {len(files)} < 15")
            if len(files) > 25:
                issues.append(f"文件数过多: {len(files)} > 25")
            if total_lines < 2500:
                issues.append(f"目标行数不足: {total_lines} < 2500")
            if issues:
                print(f"   ⚠️ 校验问题: {'; '.join(issues)}")

            if approve("P2 - 架构设计与文件清单", summary):
                self._save_json("p2_architecture.json", data)
                return data
            print("   🔄 重新生成...")

    # ── P3: 程序员 ────────────────────────────────────
    def run_p3(self, p1_data: dict, p2_data: dict) -> list:
        """阶段 3：逐文件代码生成"""
        system = load_prompt("coder")
        files = p2_data.get("file_tree", [])
        style_seed = json.dumps(p1_data.get("style_seed", {}), ensure_ascii=False)
        terminology = json.dumps(p1_data.get("terminology_map", {}), ensure_ascii=False)
        mock_schema = json.dumps(p1_data.get("mock_data_schema", {}), ensure_ascii=False)

        # 前 3 个文件作为"前哨站"检查
        checkpoint_count = 3
        generated = []
        code_dir = os.path.join(self.project_dir, "code")

        for i, file_info in enumerate(files):
            file_path = file_info.get("path", f"unknown_{i}.py")
            print(f"\n   📝 生成 [{i+1}/{len(files)}]: {file_path}")

            # 构建已生成文件的摘要（供参考一致性）
            related_summary = ""
            for dep in file_info.get("depends_on", []):
                for g in generated:
                    if g["file_path"].endswith(dep.split("/")[-1]):
                        related_summary += f"\n--- {dep} ---\n{g['content'][:500]}...\n"

            user_prompt = (
                f"## 风格配置\n{style_seed}\n\n"
                f"## 术语映射\n{terminology}\n\n"
                f"## 数据 Schema\n{mock_schema}\n\n"
                f"## 当前文件\n{json.dumps(file_info, ensure_ascii=False)}\n\n"
                f"## 已生成的相关文件摘要\n{related_summary if related_summary else '（无，这是第一个文件）'}\n\n"
                f"请生成这个文件的完整源代码。"
            )

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = call_ai_json(user_prompt, system_prompt=system)
                    self._log_cost("p3", result)
                    code_content = result["parsed"].get("content", "")

                    # AST 校验（仅 Python 文件）
                    if file_path.endswith(".py"):
                        ast.parse(code_content)
                        print(f"   ✅ ast.parse 通过")

                    # 保存文件
                    full_path = os.path.join(code_dir, file_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(code_content)

                    actual_lines = len([l for l in code_content.split("\n") if l.strip()])
                    generated.append({
                        "file_path": file_path,
                        "content": code_content,
                        "line_count": actual_lines,
                    })
                    print(f"   ✅ 已保存 ({actual_lines} 行)")
                    break

                except SyntaxError as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️ 语法错误 (重试 {attempt+1}/{max_retries}): {e}")
                        # 只传错误上下文
                        lines = code_content.split("\n") if 'code_content' in dir() else []
                        start = max(0, e.lineno - 6) if e.lineno else 0
                        end = min(len(lines), (e.lineno or 0) + 5)
                        context = "\n".join(f"{j+1}: {lines[j]}" for j in range(start, end))
                        user_prompt += f"\n\n## 上次生成有语法错误，请修复：\n错误: {e}\n错误位置上下文:\n{context}"
                    else:
                        print(f"   ❌ 语法错误，跳过此文件: {e}")

                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️ 生成失败 (重试 {attempt+1}/{max_retries}): {e}")
                    else:
                        print(f"   ❌ 生成失败，跳过此文件: {e}")

            # 前哨站检查
            if i == checkpoint_count - 1:
                total = sum(g["line_count"] for g in generated)
                summary = (
                    f"🔍 P3 前哨站检查（前 {checkpoint_count} 个文件）\n"
                    f"  已生成: {len(generated)} 个文件\n"
                    f"  总行数: {total} 行\n"
                    f"  文件列表:\n"
                )
                for g in generated:
                    summary += f"    - {g['file_path']} ({g['line_count']} 行)\n"
                if not approve("P3 前哨站 - 确认代码质量", summary):
                    print("   🔄 前哨站未通过，终止生成")
                    return generated

        # 最终统计
        total_lines = sum(g["line_count"] for g in generated)
        summary = (
            f"📦 P3 代码生成完成\n"
            f"  文件数: {len(generated)}/{len(files)}\n"
            f"  总行数: {total_lines} 行\n"
            f"  全部 ast.parse 通过 ✅"
        )
        approve("P3 - 代码生成完成", summary)
        return generated

    # ── P4: 截图渲染 ──────────────────────────────────
    def run_p4(self, p1_data: dict, p2_data: dict) -> list:
        """阶段 4：Jinja2 渲染 + Playwright 截图"""
        print("\n   🎨 P4 截图渲染...")

        # 构造渲染数据（从 p1 mock_data_schema 生成假数据）
        mock_schema = p1_data.get("mock_data_schema", {})
        entities = mock_schema.get("entities", [])
        primary = mock_schema.get("primary_entity", entities[0]["name"] if entities else "Item")

        # 从模板目录选择模板
        template_dir = os.path.join(BASE_DIR, "templates")
        template_path = os.path.join(template_dir, "dashboard.html")
        if not os.path.exists(template_path):
            template_path = os.path.join(BASE_DIR, "template.html")

        # 生成截图
        import subprocess
        screenshots_dir = os.path.join(self.project_dir, "screenshots")
        render_script = os.path.join(BASE_DIR, "renderer.py")

        if os.path.exists(render_script):
            cmd = [
                sys.executable, render_script,
                "--template", template_path,
                "--data", os.path.join(self.project_dir, "p1_insight.json"),
                "--output", screenshots_dir,
                "--app-name", self.software,
            ]
            subprocess.run(cmd, timeout=120)
        else:
            # 回退到 MVP 脚本
            cmd = [sys.executable, os.path.join(BASE_DIR, "screenshot_mvp.py")]
            subprocess.run(cmd, cwd=BASE_DIR, timeout=120)

        # 统计截图
        screenshots = [f for f in os.listdir(screenshots_dir) if f.endswith(".png")] if os.path.exists(screenshots_dir) else []
        summary = f"📸 P4 截图渲染\n  生成: {len(screenshots)} 张截图\n  目录: {screenshots_dir}"
        approve("P4 - 截图渲染", summary)
        return screenshots

    # ── P5: 文档封装 ──────────────────────────────────
    def run_p5(self, p1_data: dict, p2_data: dict, code_files: list) -> str:
        """阶段 5：Word 文档封装"""
        print("\n   📄 P5 文档封装...")
        packer_path = os.path.join(BASE_DIR, "packer.py")
        package_dir = os.path.join(self.project_dir, "package")

        if os.path.exists(packer_path):
            import subprocess
            cmd = [
                sys.executable, packer_path,
                "--project-dir", self.project_dir,
                "--output", package_dir,
            ]
            subprocess.run(cmd, timeout=120)

        summary = f"📦 P5 封装完成\n  输出目录: {package_dir}"
        approve("P5 - 文档封装", summary)
        return package_dir

    # ── 总控 ──────────────────────────────────────────
    def run_all(self):
        """执行全部五阶段"""
        print(f"\n🏭 软著工厂启动")
        print(f"   公司: {self.company}")
        print(f"   软件: {self.software}")
        print(f"   目录: {self.project_dir}")
        print(f"{'─'*60}")

        start_time = time.time()

        # P1
        p1 = self.run_p1()

        # P2
        p2 = self.run_p2(p1)

        # P3
        code_files = self.run_p3(p1, p2)

        # P4
        screenshots = self.run_p4(p1, p2)

        # P5
        package_dir = self.run_p5(p1, p2, code_files)

        # 最终报告
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"🎉 全部完成！")
        print(f"   总耗时: {elapsed:.0f}s")
        print(f"   总 Token: {self.total_tokens}")
        print(f"   项目目录: {self.project_dir}")
        print(f"{'='*60}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 orchestrator.py '公司全称' '软件名称'")
        print("示例: python3 orchestrator.py '阳光新能源科技有限公司' '智能能耗监控系统'")
        sys.exit(1)

    factory = SoftCopyrightFactory(sys.argv[1], sys.argv[2])
    factory.run_all()
