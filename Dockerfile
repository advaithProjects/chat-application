FROM python:3.11-alpine
WORKDIR /usr/src/app
COPY requirements.txt ./
EXPOSE 5000
RUN pip install -r requirements.txt
COPY . .
CMD ["python","server.py"]


