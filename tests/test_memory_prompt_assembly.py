from backend.server import build_memory_block


def test_memory_block_orders_preference_short_and_long_term():
    memory_block = build_memory_block(
        preference=[{"content": "叫用户阿泽"}],
        short_term=[{"content": "最近在做桌面 AI 项目"}],
        long_term=[{"content": "长期喜欢治愈风格"}],
    )

    assert memory_block.index("叫用户阿泽") < memory_block.index("最近在做桌面 AI 项目")
    assert memory_block.index("最近在做桌面 AI 项目") < memory_block.index("长期喜欢治愈风格")
