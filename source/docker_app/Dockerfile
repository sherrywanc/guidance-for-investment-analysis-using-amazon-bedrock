FROM python:3.9.16
EXPOSE 8501
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN  pip3 install --upgrade pip && pip3 install -r requirements.txt

# Creating a new non-root user
RUN useradd -m demouser

# Dropping privileges by setting the user to newly created user
USER demouser

COPY . /app

ENV PYTHONPATH=/app

CMD streamlit run web/app.py
