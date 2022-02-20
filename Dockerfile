FROM python:3.9
ENV PYTHONUNBUFFERED 1
ENV IN_DOCKER_CONTAINER Yes
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . /app
CMD ["python", "main.py"]