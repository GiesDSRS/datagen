FROM python:3.13-slim

# Define arguments
#docker buildx build --platform linux/amd64  --push  -t hub.ncsa.illinois.edu/gies-dsrs/ikmpt-ui .

RUN pip install --upgrade pip

RUN adduser --disabled-password worker
USER worker
WORKDIR /home/worker

COPY --chown=worker:worker . .
RUN pip3 install --user -r requirements.txt

ENV PATH="/home/worker/.local/bin:${PATH}"

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
