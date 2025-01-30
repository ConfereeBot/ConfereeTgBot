FROM datawookie/undetected-chromedriver:latest

RUN apt-get update && apt-get install -y \
    jq \
    ffmpeg \
    pulseaudio \
    pulseaudio-utils \
    && rm -rf /var/lib/apt/lists/*

RUN wget $( \
        curl -sSL https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json \
        | jq -r '.channels.Stable.downloads.chrome[] | select(.platform == "linux64") | .url' \
    )
RUN unzip -qq -o chrome-linux64.zip -d /var/local/ && rm chrome-linux64.zip

WORKDIR /app

RUN python -m pip install --no-cache-dir poetry==1.8.3 debugpy

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi \
    && rm -rf $(poetry config cache-dir)/{cache,artifacts}

COPY . .

RUN rm /tmp/.X0-lock

ENTRYPOINT ["python", "-Xfrozen_modules=off", "-u", "-B", "-m"]
CMD ["meetsaver"]
