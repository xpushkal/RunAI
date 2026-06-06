# Redrob candidate ranker — common tasks.
# Uses the uv-managed .venv if present, else falls back to `python`.

PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)
CANDIDATES := India_runs_data_and_ai_challenge/candidates.jsonl
OUT := submission.csv

.PHONY: setup precompute rank validate verify demo explore clean

setup:                ## create venv + install deps
	uv venv --python 3.11
	uv pip install -r requirements.txt

precompute:           ## one-time: embeddings + graph features -> artifacts/
	$(PY) -m src.precompute
	$(PY) -m src.graph

rank:                 ## produce the ranked submission CSV (the reproduce command)
	$(PY) rank.py --candidates $(CANDIDATES) --out $(OUT)

validate:             ## run the official format validator on the output
	$(PY) India_runs_data_and_ai_challenge/validate_submission.py $(OUT)

verify: rank validate  ## rank + validate + determinism check
	@$(PY) rank.py --out /tmp/_det.csv >/dev/null 2>&1 && \
	  diff -q $(OUT) /tmp/_det.csv >/dev/null && echo "determinism: byte-identical" || \
	  echo "determinism: MISMATCH"

demo:                 ## launch the Streamlit sandbox
	$(PY) -m streamlit run app.py

explore:              ## M1 data exploration
	$(PY) scripts/explore.py

clean:                ## remove generated outputs (keeps artifacts/)
	rm -f submission.csv /tmp/_det.csv
