setup:
	if which uv && [ ! -d .venv ] ; then uv sync ; fi
	source .venv/bin/activate \
		&& uv pip install -q -U pip \
		&& uv pip install -e '.[dev]'
