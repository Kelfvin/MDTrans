from vllm import LLM
from PIL import Image
from mineru_vl_utils import MinerUClient
from mineru_vl_utils import MinerULogitsProcessor  # if vllm>=0.10.1

llm = LLM(
    model="opendatalab/MinerU2.5-Pro-2604-1.2B",
    logits_processors=[MinerULogitsProcessor]  # if vllm>=0.10.1
)

client = MinerUClient(
    backend="vllm-engine", vllm_llm=llm,
    image_analysis=False # default False, set True to enable image/chart analysis
)

print(client.two_step_extract(Image.open("/path/to/page.png")))

