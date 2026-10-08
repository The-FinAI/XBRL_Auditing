<div align="center">

<h1>XBRL_Auditing</h1>

<p><strong>Gold-answer extraction from XBRL DQC messages, companion code for FinAuditing</strong></p>

<p>
  <a href="https://arxiv.org/abs/2510.08886"><img src="https://img.shields.io/badge/arXiv-2510.08886%20(FinAuditing)-b31b1b.svg" alt="arXiv (FinAuditing)"></a>
  <a href="https://huggingface.co/collections/TheFinAI/finauditing-taxonomy-structured-auditing-68e5f80606e22454027075e7"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Collection-yellow?logo=huggingface" alt="Hugging Face Collection"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
</p>

<p>
  <a href="https://arxiv.org/abs/2510.08886">Paper (FinAuditing)</a> ·
  <a href="https://huggingface.co/collections/TheFinAI/finauditing-taxonomy-structured-auditing-68e5f80606e22454027075e7">Data</a>
</p>

</div>

---

## Overview

This repository is companion code for [FinAuditing](https://github.com/The-FinAI/FinAuditing). The notebooks show how to extract gold-standard answers from XBRL Data Quality Committee (DQC) messages, where each DQC rule ID corresponds to a specific error type and is aligned with one FinAuditing subtask: semantic matching, relationship extraction, or mathematical reasoning.

## How It Works

- Three code examples, [`relationship_extraction_0081.ipynb`](relationship_extraction_0081.ipynb), [`semantic_matching_0099.ipynb`](semantic_matching_0099.ipynb), and [`mathematical_reasoning_0126.ipynb`](mathematical_reasoning_0126.ipynb), demonstrate how to extract gold-standard answers from DQC messages for rule IDs 0081, 0099, and 0126, respectively.
- Each rule ID corresponds to a specific error type and is aligned with a particular subtask:
  - **DQC_0099**: semantic matching task
  - **DQC_0081**: relationship extraction task
  - **DQC_0126**: mathematical reasoning task
- These examples were executed on sample data for demonstration purposes. You are expected to run the provided code on the actual dataset to generate the final extraction results.
- In addition to these three rules, seven remaining rule IDs do not yet have a designed extraction pipeline. Refer to the structure and logic of the provided examples to construct corresponding pipelines for these remaining rule IDs (i.e., error types).

## Repository Contents

| Path | Contents |
|------|----------|
| `semantic_matching_*.ipynb` | Notebooks for DQC rules 0099, 0109, 0123, 0137 |
| `relationship_extraction_*.ipynb` | Notebooks for DQC rules 0001, 0081, 0145 |
| `mathematical_reasoning_*.ipynb` | Notebooks for DQC rules 0015, 0117, 0126 |
| [`example_input_files/`](example_input_files), [`example_output_files/`](example_output_files) | Sample inputs (CSV) and outputs (XLSX) for the demonstration runs |
| [`input_files/`](input_files), [`output_files/`](output_files) | Per-rule input CSVs and output spreadsheets |
| [`create_chunk/`](create_chunk) | US-GAAP taxonomy spreadsheets (2021–2024) and `run_chunk.sh` / `chunk_gaap_taxonomy.py`, which convert a GAAP Taxonomy Excel file into JSONL chunks |
| [`agentic_benchmark_audit/`](agentic_benchmark_audit) | `select_usgaap_segmentation.ipynb`, `constructMR2HF.ipynb` (builds the mathematical reasoning data as a Hugging Face dataset), and selected mathematical reasoning spreadsheets (`excels_MR_task/`) |

## Resources on Hugging Face

| Resource | Description |
|----------|-------------|
| [FinAuditing collection](https://huggingface.co/collections/TheFinAI/finauditing-taxonomy-structured-auditing-68e5f80606e22454027075e7) | All FinAuditing datasets |
| [TheFinAI/en-finsm](https://huggingface.co/datasets/TheFinAI/en-finsm) | FinSM (Financial Semantic Matching) evaluation set |
| [TheFinAI/en-finre](https://huggingface.co/datasets/TheFinAI/en-finre) | FinRE (Financial Relationship Extraction) evaluation set |
| [TheFinAI/en-finmr](https://huggingface.co/datasets/TheFinAI/en-finmr) | FinMR (Financial Mathematical Reasoning) evaluation set |

## Citation

This repository has no paper of its own. If you use it, please cite the related FinAuditing benchmark:

```bibtex
@misc{wang2025finauditingfinancialtaxonomystructuredmultidocument,
      title={FinAuditing: A Financial Taxonomy-Structured Multi-Document Benchmark for Evaluating LLMs}, 
      author={Yan Wang and Keyi Wang and Shanshan Yang and Jaisal Patel and Jeff Zhao and Fengran Mo and Xueqing Peng and Lingfei Qian and Jimin Huang and Guojun Xiong and Xiao-Yang Liu and Jian-Yun Nie},
      year={2025},
      eprint={2510.08886},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2510.08886}, 
}
```

## License

The code in this repository is released under the [MIT License](LICENSE). Datasets and models on Hugging Face keep their own licenses, stated on each card.

---

<p align="center">Built by <a href="https://thefin.ai">The Fin AI</a> · <a href="https://huggingface.co/TheFinAI">Hugging Face</a> · <a href="https://github.com/The-FinAI">GitHub</a></p>
