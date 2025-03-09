FROM python:3.13.2-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN python -m pip install --no-cache-dir poetry==1.8.3 \
    && poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi \
    && rm -rf $(poetry config cache-dir)/{cache,artifacts}

COPY . .

ENTRYPOINT ["python3", "-u", "-B", "-m", "app"]

CMD ["poetry", "run", "python", "-m", "app"]
