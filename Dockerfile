ARG DOCKER_REGISTRY=""
FROM ${DOCKER_REGISTRY}python:3.8-slim

WORKDIR /sonarqube_exporter/

COPY . . 

RUN /usr/local/bin/python3 -m pip install --upgrade pip

RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 8198 

ENTRYPOINT ["python","docker_entrypoint.py"]
