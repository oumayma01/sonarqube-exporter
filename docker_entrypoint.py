import os
import time
import json
from prometheus_client import start_http_server, Gauge
import requests

# Environment Variables
SONARQUBE_SERVER = os.getenv('SONARQUBE_SERVER')
SONARQUBE_TOKEN = os.getenv('SONARQUBE_TOKEN')
EXPORTER_PORT = int(os.getenv('EXPORTER_PORT', 8198))

# Fetch all Sonarqube metrics
def fetch_sonarqube_metrics():
    auth = (SONARQUBE_TOKEN, '')
    excluded_metrics = ['ncloc_language_distribution', 'quality_profiles', 'quality_gate_details']
    response = requests.get(f"{SONARQUBE_SERVER}/api/metrics/search", auth=auth)
    if response.status_code == 200:
        try:
            all_metrics = response.json().get('metrics', [])
            filtered_metrics = [metric for metric in all_metrics if metric.get('key') not in excluded_metrics]
            return filtered_metrics
        except json.JSONDecodeError:
            print("Failed to decode JSON. Response content:", response.text)
            return []
    else:
        print(f"Failed to fetch metrics from SonarQube. Status code: {response.status_code}, Response content: {response.text}")
        return []


# Fetch all Sonarqube projects
def fetch_all_projects():
    auth = (SONARQUBE_TOKEN, '')
    response = requests.get(f"{SONARQUBE_SERVER}/api/projects/search", auth=auth)
    if response.status_code == 200:
        projects = response.json().get('components', [])
        project_keys = [project['key'] for project in projects]
        return project_keys
    else:
        print("Failed to fetch projects from SonarQube")
        return []

# Fetch metric values
def fetch_metric_value(project_key, metric_key):
    auth = (SONARQUBE_TOKEN, '')
    url = f"{SONARQUBE_SERVER}/api/measures/component"
    params = {'component': project_key, 'metricKeys': metric_key}

    try:
        response = requests.get(url, params=params, auth=auth)
        response.raise_for_status()
        measures = response.json().get('component', {}).get('measures', [])
        value = measures[0].get('value') if measures else None

        if value is None:
            return 0.0
        elif value in ['true', 'false', 'OK', 'ERROR']:
            return 0.0 if value in ['false', 'ERROR'] else 1.0
        else:
            return float(value)
    except Exception as e:
        print(f"Invalid or missing metric value for project {project_key} and metric {metric_key}: {e}")
        return 0.0

# Convert fetched Sonarqube metrics to Prometheus comaptible metrics
def convert_to_prometheus_metrics(sonar_metrics):
    prometheus_metrics = {}
    for metric in sonar_metrics:
        metric_name = metric.get('key')
        metric_description = metric.get('description', 'No description')
        prometheus_metrics[metric_name] = Gauge(metric_name, metric_description, ['project_key'])
        print(f"Processed metric '{metric_name}': {metric_description}")
    return prometheus_metrics

# Function to update the fetched metrics
def update_prometheus_metrics(sonar_metrics, prom_metrics, project_keys):
    for project_key in project_keys:
        for metric in sonar_metrics:
            metric_name = metric.get('key')
            metric_value = fetch_metric_value(project_key, metric_name)
            prom_metrics[metric_name].labels(project_key=project_key).set(metric_value)

# Exporter function
def start_exporter():
    sonar_metrics = fetch_sonarqube_metrics()
    prom_metrics = convert_to_prometheus_metrics(sonar_metrics)
    start_http_server(EXPORTER_PORT)

    while True:
        project_keys = fetch_all_projects()
        update_prometheus_metrics(sonar_metrics, prom_metrics, project_keys)
        time.sleep(600)

if __name__ == "__main__":
    start_exporter()
