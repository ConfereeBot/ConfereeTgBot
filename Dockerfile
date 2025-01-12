FROM datawookie/undetected-chromedriver:latest

ENV CHROME_VERSION=131.0.6778.264
ENV CHROMEDRIVER_VERSION=131.0.6778.264

RUN wget https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip \
            && wget https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip
RUN unzip -qq -o chrome-linux64.zip -d /var/local/ \
            && unzip -qq -o chromedriver-linux64.zip -d /var/local/ \
            && rm chrome-linux64.zip chromedriver-linux64.zip

WORKDIR /app

RUN python -m pip install --no-cache-dir poetry==1.8.3 debugpy

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi \
    && rm -rf $(poetry config cache-dir)/{cache,artifacts}

COPY . .

ENTRYPOINT ["python", "-u", "-B" "-m"]
CMD ["meetsaver.gmeet-bot"]
