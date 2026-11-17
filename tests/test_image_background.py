import pytest

from bench import image_background


def test_diffusion_receives_seed_and_no_document_values():
    pytest.importorskip("diffusers")
    pytest.importorskip("torch")

    class Pipe:
        def __call__(self, **kwargs):
            assert kwargs["generator"].initial_seed() == 17
            assert kwargs["guidance_scale"] == 0
            assert kwargs["prompt"] == image_background.BACKGROUND_PROMPT
            return type("Result", (), {"images": ["generated"]})()

    image, seconds = image_background.make_background(Pipe(), 17)
    assert image == "generated" and seconds >= 0
