import asyncio
import json
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VOICE_ROOT = REPO_ROOT / 'tauri-app' / 'public-packaged' / 'voice-packs'

VOICE_PACKS = {
    'warm-female': {
        'name': '温柔女声',
        'voice': 'zh-CN-XiaoxiaoNeural',
        'rate': '-5%',
        'pitch': '-5Hz',
    },
    'cheerful-female': {
        'name': '元气女声',
        'voice': 'zh-CN-XiaoyiNeural',
        'rate': '+5%',
        'pitch': '+8Hz',
    },
    'calm-male': {
        'name': '沉稳男声',
        'voice': 'zh-CN-YunxiNeural',
        'rate': '-8%',
        'pitch': '-8Hz',
    },
    'cute-child': {
        'name': '可爱童音',
        'voice': 'zh-CN-XiaoxiaoNeural',
        'rate': '+12%',
        'pitch': '+18Hz',
    },
}

PHRASES = {
    'bubble-gentle-01.mp3': '我在呢。',
    'bubble-gentle-02.mp3': '怎么啦？',
    'bubble-gentle-03.mp3': '嗯，我听到了。',
    'bubble-gentle-04.mp3': '有事找我吗？',
    'bubble-gentle-05.mp3': '我在旁边陪着你。',
    'bubble-cheerful-01.mp3': '嘿嘿，你点到我啦。',
    'bubble-cheerful-02.mp3': '我有在认真看你哦。',
    'bubble-cheerful-03.mp3': '今天也想陪你一下。',
    'bubble-cheerful-04.mp3': '诶嘿，我在这儿。',
    'bubble-cheerful-05.mp3': '要不要和我说一句话？',
    'bubble-shy-01.mp3': '欸？',
    'bubble-shy-02.mp3': '突然点我呀。',
    'bubble-shy-03.mp3': '唔，被发现了。',
    'bubble-shy-04.mp3': '嗯？怎么啦？',
    'bubble-shy-05.mp3': '我还以为你在忙呢。',
    'bubble-calm-01.mp3': '我会在这儿待着的。',
    'bubble-calm-02.mp3': '慢慢来也没关系。',
    'bubble-calm-03.mp3': '如果你想说话，我在。',
    'bubble-calm-04.mp3': '先陪你一下。',
    'bubble-calm-05.mp3': '我没有走开哦。',
    'proactive-welcome-back.mp3': '主人，欢迎回来。',
    'proactive-morning.mp3': '早呀，今天也一起慢慢开始吧。',
    'proactive-night.mp3': '不早啦，忙完的话也记得早点休息。',
    'proactive-long-work.mp3': '你已经坐挺久啦，要不要起来活动一下？',
    'proactive-meal-lunch.mp3': '差不多到饭点了，记得照顾一下自己。',
    'proactive-meal-dinner.mp3': '晚饭时间快到了，别让自己太晚吃饭哦。',
    'proactive-weather.mp3': '我帮你看了一眼天气，今天出门前可以多留意一下温度。',
    'proactive-care.mp3': '主人，今天也别太辛苦啦。',
    'memory-remembered.mp3': '我记住了。',
}


def ensure_edge_tts_installed() -> None:
    if importlib.util.find_spec('edge_tts') is not None:
        return
    raise SystemExit(
        'edge-tts is not installed.\n'
        'Install it with:\n'
        '  python -m pip install edge-tts\n'
    )


def write_meta_json(pack_id: str, pack_name: str, pack_dir: Path) -> None:
    meta = {
        'id': pack_id,
        'name': pack_name,
        'phrases': {text: file_name for file_name, text in PHRASES.items()},
    }
    (pack_dir / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')


async def generate_pack(pack_id: str, config: dict) -> None:
    import edge_tts

    pack_dir = VOICE_ROOT / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)
    write_meta_json(pack_id, config['name'], pack_dir)

    for file_name, text in PHRASES.items():
        output_path = pack_dir / file_name
        communicate = edge_tts.Communicate(
            text=text,
            voice=config['voice'],
            rate=config['rate'],
            pitch=config['pitch'],
        )
        await communicate.save(str(output_path))
        print(f'generated {output_path}')


async def main() -> None:
    ensure_edge_tts_installed()
    VOICE_ROOT.mkdir(parents=True, exist_ok=True)
    for pack_id, config in VOICE_PACKS.items():
        await generate_pack(pack_id, config)


if __name__ == '__main__':
    asyncio.run(main())
