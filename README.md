# selfbatch-for-local-llm
One request can't fill a GPU: decode saturates the memory bandwidth while 99% of the compute sits idle. Split the output into N parts and decode them concurrently — the same weight read now produces N tokens.
