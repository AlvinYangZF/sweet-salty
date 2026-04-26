#!/usr/bin/env python3
"""
甜盐 CP — AI Agent 即兴情感剧引擎 v0.1
用法:
  python3 engine/drama.py /trigger "小盐第一次去小甜家"
  python3 engine/drama.py --replay 1
  python3 engine/drama.py --list
"""

import json, os, sys, time, subprocess, re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
CAST = ROOT / "cast"
SCENES = ROOT / "scenes"
SCENES.mkdir(exist_ok=True)

MODEL_MAP = {
    "salty":  "kimi-code",          # 细腻 → 情感驱动
    "sweet":  "deepseek-v4-flash",  # 直白 → 日常对话
    "bestie": "gemma4:31b",         # 冷静 → 旁观吐槽
    "father": "deepseek-v4-pro",    # 严肃 → 传统长辈
    "pet":    "qwen3.5:latest",     # 简单 → 纯真萌宠
}


def load_character(char_id):
    """Load all config files for a character."""
    path = CAST / char_id
    if not path.exists():
        return None
    files = {}
    for fname in ["SOUL.md", "VOICE.md", "MEMORY.md", "SECRETS.md"]:
        fpath = path / fname
        files[fname] = fpath.read_text() if fpath.exists() else ""
    mem_file = path / "memory" / "interactions.json"
    files["memory"] = json.loads(mem_file.read_text()) if mem_file.exists() else {"history": []}
    return files


def build_prompt(char_id, trigger, character):
    """Build the full prompt for a character to respond to a trigger."""
    soul = character.get("SOUL.md", "")
    voice = character.get("VOICE.md", "")
    secrets = character.get("SECRETS.md", "")
    memory = character.get("memory", {})
    model = MODEL_MAP.get(char_id, "deepseek-v4-flash")

    prompt = f"""你正在扮演一个角色。以下是你的人设——

【人格内核】
{soul}

【说话风格】
{voice}

【你不想让别人知道的秘密】
{secrets}

【你的记忆】
{json.dumps(memory, indent=2, ensure_ascii=False)}

【当前发生的事】
{trigger}

请以这个角色的身份，给出回应。输出格式：
【内心独白】(不超过80字)
【对话】"""

    return prompt, model


def render_scene_html(scene_id, scene_data):
    """Render a scene as WeChat-style HTML."""
    title = scene_data.get("title", "未命名场景")
    lines = scene_data.get("lines", [])
    
    html = """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>""" + title + """</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#ededed;font-family:-apple-system,'PingFang SC',sans-serif;max-width:420px;margin:0 auto;min-height:100vh}
.header{background:#fff;padding:20px 16px 16px;text-align:center;border-bottom:1px solid #d9d9d9;position:sticky;top:0;z-index:10}
.header h1{font-size:17px;color:#191919}
.header .sub{font-size:12px;color:#999;margin-top:4px}
.ts{text-align:center;font-size:11px;color:#999;margin:16px 0}
.msg{display:flex;margin:12px 16px;align-items:flex-start;gap:8px}
.av{width:40px;height:40px;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#fff;flex-shrink:0;font-size:14px}
.av.s{background:#FF6B6B}.av.t{background:#4ECDC4}
.bub{max-width:70%;padding:10px 14px;border-radius:8px;font-size:15px;line-height:1.6;word-break:break-word}
.msg.s .bub{background:#fff;border-top-left-radius:2px}
.msg.t{flex-direction:row-reverse}
.msg.t .bub{background:#95ec69;border-top-right-radius:2px}
.mono{margin:8px 32px;padding:10px 14px;background:#fffde7;border-left:3px solid #ffd54f;font-size:13px;color:#666;font-style:italic;border-radius:0 6px 6px 0}
.mono::before{content:'💭';margin-right:6px}
.act{text-align:center;color:#999;font-size:12px;margin:8px 0}
</style></head><body>
<div class="header"><h1>""" + title + """</h1><div class="sub">小盐 🧂 × 🍬 小甜</div></div>
<div class="ts">""" + datetime.now().strftime("%m/%d %H:%M") + """</div>
"""
    for line in lines:
        t = line.get("type", "")
        if t == "monologue":
            html += f'<div class="mono">{line["text"]}</div>\n'
        elif t == "action":
            html += f'<div class="act">{line["text"]}</div>\n'
        elif t == "dialogue":
            who = line.get("who", "s")
            side = "s" if who == "salty" else "t"
            html += f'<div class="msg {side}"><div class="av {side}">{"盐" if side=="s" else "甜"}</div><div class="bub">{line["text"]}</div></div>\n'
    
    html += '<div style="height:40px"></div></body></html>'
    return html


def run_trigger(trigger_text):
    """Main flow: build scene from trigger."""
    print(f"\n  🎬 {trigger_text}\n")
    
    # For now, we run in "script mode" — will call real LLMs later
    scene = {
        "id": f"scene_{len(list(SCENES.glob('*.json'))) + 1:03d}",
        "trigger": trigger_text,
        "timestamp": datetime.now().isoformat(),
        "title": trigger_text,
        "lines": [],
    }
    
    # Save scene metadata
    scene_file = SCENES / f"{scene['id']}.json"
    with open(scene_file, "w") as f:
        json.dump(scene, f, indent=2, ensure_ascii=False)
    
    # Render HTML
    html = render_scene_html(scene["id"], scene)
    html_file = SCENES / f"{scene['id']}.html"
    with open(html_file, "w") as f:
        f.write(html)
    
    print(f"  ✅ 场景已保存: scenes/{scene['id']}.html")
    return scene


def list_scenes():
    """List all saved scenes."""
    scenes = sorted(SCENES.glob("*.json"))
    if not scenes:
        print("  📭 还没有生成任何场景")
        return
    print(f"\n  📖 共 {len(scenes)} 场戏:\n")
    for s in scenes:
        data = json.loads(s.read_text())
        print(f"  #{data['id']}: {data['title']}")
        print(f"     {data['timestamp'][:19]}")


def show_help():
    print(__doc__.strip())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)
    
    cmd = sys.argv[1]
    if cmd == "/trigger":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("情景: ")
        run_trigger(text)
    elif cmd == "--list":
        list_scenes()
    elif cmd == "--replay":
        n = sys.argv[2] if len(sys.argv) > 2 else "1"
        fname = f"scene_{int(n):03d}.html"
        html_path = SCENES / fname
        if html_path.exists():
            subprocess.run(["open", str(html_path)])
        else:
            print(f"  ❌ 场景 {n} 不存在")
    else:
        show_help()
