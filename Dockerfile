FROM python:3.12.3

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY ./*.py ./*.pkl ./.env ./

CMD [ "python", "-u", "./bot.py" ]
