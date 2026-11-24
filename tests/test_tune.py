import importlib.util

import pytest


def test_lora_targets_only_selected_matrices():
    if importlib.util.find_spec("peft") is None or importlib.util.find_spec("torch") is None:
        pytest.skip("група tune не встановлена")
    from peft import LoraConfig

    config = LoraConfig(r=8, lora_alpha=8, target_modules=["q_proj", "v_proj"], bias="none")
    assert set(config.target_modules) == {"q_proj", "v_proj"}
    assert config.r == config.lora_alpha == 8
