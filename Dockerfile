FROM python:3.12

EXPOSE 8080

WORKDIR /src

COPY . .

RUN pip install --no-cache-dir --no-deps -r requirements.txt

CMD [ "python3", "app.py" ]
