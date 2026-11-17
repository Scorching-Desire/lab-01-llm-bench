"""Optional local diffusion for page backgrounds with no document values."""

import time
from importlib.metadata import version

from bench import data
from bench.schema_fields import DocFields

MODEL = "stabilityai/sd-turbo"
LICENSE_URL = "https://huggingface.co/stabilityai/sd-turbo/blob/main/LICENSE.md"
BACKGROUND_PROMPT = "light ivory paper texture, soft edge shadows, fine paper grain, blank, no text or symbols"
STEPS = 2


def load_pipe():
    import torch
    from diffusers import AutoPipelineForText2Image

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    pipe = AutoPipelineForText2Image.from_pretrained(MODEL, variant="fp16", dtype=dtype).to(device)
    pipe.set_progress_bar_config(disable=True)
    return pipe


def make_background(pipe, seed):
    import torch

    generator = torch.Generator(device="cpu").manual_seed(seed)
    start = time.perf_counter()
    image = pipe(prompt=BACKGROUND_PROMPT, num_inference_steps=STEPS, guidance_scale=0.0,
                 generator=generator, width=512, height=512).images[0]
    return image, time.perf_counter() - start


def manifest_row(path, record_id, seed, seconds, pipe):
    return dict(file=path.as_posix(), record_id=record_id, variant="gen", model=MODEL,
                seed=seed, seconds=round(seconds, 3), tool="diffusers.AutoPipelineForText2Image",
                tool_version=version("diffusers"), torch_version=version("torch"), device=str(pipe.device),
                size=[512, 512], guidance_scale=0.0, steps=STEPS, prompt=BACKGROUND_PROMPT,
                license="Stability AI Community License", license_url=LICENSE_URL,
                not_determined=sorted(DocFields.model_fields), sha256=data.sha256_file(path))
