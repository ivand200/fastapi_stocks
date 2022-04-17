FROM python:3.8

RUN pip install --upgrade pip

COPY . /src/
WORKDIR /src

RUN apt-get update

RUN pip install -r requirements.txt

CMD ["uvicorn", "app.main:app", "--reload"]

