FROM python:3.10-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code
RUN chmod +x ./docker-entrypoint.sh || true

EXPOSE 8000

CMD ["./docker-entrypoint.sh"]
