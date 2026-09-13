> **The idea is the human's. The work and the knowledge come from AI.**
> 点子是人的，工作和知识是 AI 做的。

# selfbatch-for-local-llm

> One request can't fill a GPU. On a local model there is no one else to fill
> it either. So split the output into N segments and generate them
> concurrently — the same weight read now produces N tokens.

During decode a locally deployed LLM can't use most of its compute: one request
is a single serial stream, so the GPU sits idle step after step. Cross-request
batching fixes this — but **only when other users happen to be there**. A single
request can never fill the machine on its own.

This project fixes it from inside one request: **split one long output into N
segments, decode them concurrently, then align them with k rounds of mutual
revision.**

Measured on a single NVIDIA GB10 (27B bf16, 2048-token context):

| | |
|---|---|
| Aggregate decode throughput at N=64 | **34×** vs a single stream *(measured)* |
| End-to-end, real document | **not yet demonstrated** — see below |

**An honest caveat.** The parallel decode win is real and measured. But the first
real end-to-end run came out **5.1× slower**, not faster. With the model's
reasoning left on, one alignment round deliberates ~4,800 characters to revise
~300, so **a single fusion round costs more than writing the whole document once**
(769 s vs 442 s). Whether the end-to-end win survives depends entirely on making
that round cheap — turn reasoning off, or train the rewrite to be a minimal edit.

**That is the open question — not the parallelism.**

---

## The one question you must answer first

> **Delete a middle segment — can the later ones still be written correctly?**

- **Yes** → the task is *information-parallel*. This works.
- **No** → it is *information-serial* (proofs, step-by-step derivations, state
  machines). **Splitting makes the output worse. Don't.**

The most valuable — and most easily misjudged — category is *"looks serial but
isn't"*: step-by-step tutorials, procedures, parameter tables. They read like
"step 1, step 2, …" but every step's content comes from the source material, not
from the previous step's result.

## How it works

1. **Serial outline** (one call), then frozen.
2. **N segments generated in parallel** (N concurrent calls).
   Each prompt contains only: the source material + the outline (titles only) +
   that segment's own instruction. **Never another segment's body text.**
3. **k alignment rounds** (N concurrent calls each).
   Every segment sees the whole document and is asked to agree on terminology,
   facts, numbers, and timeline. **New segments replace old ones** — history
   stays on disk, it never accumulates into the prompt.
4. Assemble.

## Measured: the batch timing curve

Fixed 2048-token input, forced 256-token output, greedy. Single GB10, 27B bf16.

| batch | decode median | per-step vs 1 stream | aggregate speedup | efficiency |
|---|---|---|---|---|
| 1 | 57.64 s | 1.000 | 1.0× | 100% |
| 2 | 59.84 s | 1.038 | 1.9× | 96% |
| 4 | 60.77 s | 1.054 | 3.8× | 95% |
| 8 | 63.65 s | 1.104 | 7.2× | 91% |
| 16 | 69.50 s | 1.206 | 13.3× | 83% |
| 32 | 84.29 s | 1.462 | 21.9× | 68% |
| 64 | 108.19 s | 1.877 | **34.1×** | 53% |

At batch=1 the memory bandwidth is already ~90% saturated (225 ms vs a 203 ms
roofline) while **less than 1% of the compute is in use**. The waste is not an
idle GPU — it is *one token produced per full weight read*.

## Cost model

```
speedup = N / ((1 + k) × per-step ratio)      effective batch size = N / (1 + k)
```

**Not `N / k`.** Each alignment round rewrites the whole output, so the k-round
cost is real: with N=10, k=2 you get ~2.9×, not 5×.

| k | cost | N=10 | N=32 |
|---|---|---|---|
| 1 | 2× | 5.0× | 16.0× |
| **2** | **3×** | **3.3×** | **10.7×** |
| 4 | 5× | 2.0× | 6.4× |

## Same machine efficiency, two ways to cash it in

| | Cashes in as | Decided by | Cost |
|---|---|---|---|
| Cross-request batching (cloud vendors) | **more users** (total throughput) | traffic | each user gets slower |
| **This project** | **one user's speed** | the task itself | (1+k)× tokens generated |

Single-user token rate, measured: 4.44 tok/s at 1 stream → **2.37 tok/s** at 64
concurrent streams. Vendors cannot make one user faster; they can only raise the
sum. This project raises the individual user's rate to **13.0 tok/s** at N=10,
k=2 — above even the zero-load single-stream baseline.

**It fills the troughs.** Cross-request batching eats the peaks (when someone
else's request is present); this eats the troughs (when nobody else is).

## Requirements

1. The serving layer must **batch concurrent requests**. A sequential script
   gets zero speedup. (Measured with vLLM's OpenAI-compatible server.)
2. `N` should stay where per-step efficiency is still high — **N = 16–32** on
   this hardware (53% efficiency at N=64).

## Status

- **The parallel decode speedup is measured.** Full batch curve 1→64 on one GPU:
  34× aggregate throughput at N=64, at 1.88× the per-step cost.
- **The end-to-end win is not demonstrated yet.** The first real run came out
  slower, and the reason is now identified — the alignment round, not the
  parallelism (see the caveat above).
- **Quality is unverified.** Whether segmented output matches single-pass
  quality, and how many alignment rounds `k` needs zero-shot, is the next
  milestone.

## Repository layout

```
harness/        runner: task loading, verbatim prompts, vLLM client, orchestration
frontend/       live view (web page + terminal view) of segments being written
prompts/        the judgment + execution protocol, standalone
tasks/          30 designed tasks (A/B/C = 10/10/10) + ground-truth keys
work/           measurement and verification scripts
results/        measured data (batch curve, raw model outputs)
handoff/        the original frozen project brief
FINDINGS.md     full analysis
DECISIONS.md    every ruling made while executing, and deviations
```
