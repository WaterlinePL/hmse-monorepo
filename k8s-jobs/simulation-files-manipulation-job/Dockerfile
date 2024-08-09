FROM python:3.8-slim-buster
COPY phydrus /phydrus
RUN pip install -e /phydrus
COPY /hmse-utils /hmse-utils
RUN pip install -e /hmse-utils
COPY k8s-jobs/simulation-files-manipulation-job/hmse_simulation_tool.py hmse_simulation_tool.py
CMD ["python3", "hmse_simulation_tool.py"]
