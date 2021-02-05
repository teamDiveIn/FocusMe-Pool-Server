FROM python:3.9
ENV PYTHONUNBUFFERED=1
RUN mkdir /app
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "manage.py", "makemigrations","&&","python","manage.py","migrate", "&&", "python","manage.py","runserver"]