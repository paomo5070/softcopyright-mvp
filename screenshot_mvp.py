"""
软著工厂 MVP - 截图渲染链路验证
用法: python screenshot_mvp.py
依赖: pip install jinja2 playwright && playwright install chromium
"""

import asyncio
import json
import os
import sys
from datetime import datetime

from jinja2 import Template
from playwright.async_api import async_playwright


async def run_mvp_screenshot():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "render_outputs")
    os.makedirs(output_dir, exist_ok=True)

    # ── 1. 读取数据和模板 ──────────────────────────────
    with open(os.path.join(base_dir, "data.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(os.path.join(base_dir, "template.html"), "r", encoding="utf-8") as f:
        html_template = f.read()

    # ── 2. Jinja2 渲染 ─────────────────────────────────
    template = Template(html_template)
    rendered_html = template.render(**data)

    # 保存渲染后的 HTML（方便调试）
    html_path = os.path.join(output_dir, "rendered.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print(f"📄 渲染 HTML 已保存：{html_path}")

    # ── 3. Playwright 截图 ──────────────────────────────
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        try:
            await page.set_content(rendered_html, wait_until="networkidle")

            # 注入字体回退（防止中文方块）
            await page.add_style_tag(content="""
                @font-face {
                    font-family: 'CJKFallback';
                    src: local('Noto Sans CJK SC'), local('WenQuanYi Micro Hei'),
                         local('Microsoft YaHei'), local('PingFang SC');
                }
                * { font-family: 'CJKFallback', sans-serif !important; }
            """)

            # 等待 Tailwind 渲染
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1000)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 截图 1：控制面板（默认视图）
            path1 = os.path.join(output_dir, f"01_dashboard_{timestamp}.png")
            await page.screenshot(path=path1, full_page=False)
            print(f"✅ 截图 1（控制面板）：{path1}")

            # 截图 2：点击"能耗分析"菜单
            try:
                await page.click("text=能耗分析", timeout=3000)
                await page.wait_for_timeout(500)
                path2 = os.path.join(output_dir, f"02_analysis_{timestamp}.png")
                await page.screenshot(path=path2, full_page=False)
                print(f"✅ 截图 2（能耗分析）：{path2}")
            except Exception as e:
                print(f"⚠️  截图 2 跳过（菜单点击失败）：{e}")

            # 截图 3：全屏表格
            path3 = os.path.join(output_dir, f"03_fullscreen_{timestamp}.png")
            await page.screenshot(path=path3, full_page=True)
            print(f"✅ 截图 3（全屏）：{path3}")

        except Exception as e:
            print(f"❌ 截图失败：{e}")
            return False
        finally:
            await browser.close()

    # ── 4. 验证输出 ────────────────────────────────────
    files = [f for f in os.listdir(output_dir) if f.endswith(".png")]
    print(f"\n{'='*50}")
    print(f"📁 输出目录：{output_dir}")
    print(f"📄 生成截图：{len(files)} 张")
    for f in sorted(files):
        size = os.path.getsize(os.path.join(output_dir, f))
        print(f"   - {f} ({size / 1024:.1f} KB)")

    if len(files) >= 1:
        print(f"\n🎉 MVP 验证通过！截图链路可用。")
        return True
    else:
        print(f"\n❌ 未生成任何截图，请检查错误信息。")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_mvp_screenshot())
    sys.exit(0 if success else 1)
