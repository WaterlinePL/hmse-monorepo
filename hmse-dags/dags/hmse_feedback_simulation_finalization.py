import json
from datetime import datetime
from typing import Dict

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.python import get_current_context
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from kubernetes.client import V1EnvVar, V1EnvVarSource, V1SecretKeySelector, V1Volume, V1VolumeMount, \
    V1PersistentVolumeClaimVolumeSource

from hmse_utils import create_project_metadata_args_for_cli, prepare_cli_config

default_args = {'start_date': datetime(2022, 1, 1)}
DAG_ID = "hmse_feedback_finalization"

# Request params JSON structure:
# {
#     "conf": {
#         "simulation": {
#             "project_id": "sample-project",
#             "start_date": "1970-1-1",
#             "project_minio_location": "bucket/path/to/project",  # The bucket must be accessible via S3 credentials
#             "spin_up": 30,
#             "modflow_metadata": {
#                 "modflow_id": "modflow_model",
#                 "grid_unit": "m"
#             },
#             "shapes_to_hydrus": {
#                 "shape1": "hydrus_model1",
#                 "shape2": "hydrus_model2",
#                 "shape3": "hydrus_model3"
#             },
#             "hydrus_to_weather": {
#                 "hydrus_model1": "weather_data1",
#                 "hydrus_model2": "weather_data2"
#             },
#             "is_feedback_loop": true,
#         }
#     }
# }


@dag(
    DAG_ID,
    schedule_interval=None,
    default_args=default_args,
    catchup=False,
    tags=['hmse', 'k8s', 'feedback', 'finalization'],
)
def taskflow():
    @task(task_id="extract-simulation-params")
    def extract_simulation_params() -> Dict:
        print("Extracting simulation params")
        context = get_current_context()
        params = context['params']
        print(f'Params: {json.dumps(params, indent=2)}')
        return params['simulation']

    @task(task_id="simulation-params-to-cli-params")
    def simulation_params_to_cli_params(simulation_params: Dict) -> Dict:
        return prepare_cli_config(simulation_params)

    pvc_name = Variable.get("simulation_pvc")
    minio_secret_name = Variable.get("simulation_minio_secret")
    secret_env = [
        V1EnvVar(name="ENDPOINT",
                 value_from=V1EnvVarSource(
                     secret_key_ref=V1SecretKeySelector(
                         name=minio_secret_name,
                         key="endpoint",
                         optional=False
                     ))),
        V1EnvVar(name="ACCESS_KEY",
                 value_from=V1EnvVarSource(
                     secret_key_ref=V1SecretKeySelector(
                         name=minio_secret_name,
                         key="access_key",
                         optional=False
                     ))),
        V1EnvVar(name="SECRET_KEY",
                 value_from=V1EnvVarSource(
                     secret_key_ref=V1SecretKeySelector(
                         name=minio_secret_name,
                         key="secret_key",
                         optional=False
                     )))
    ]

    project_metadata = extract_simulation_params()

    iteration_pre_configuration = KubernetesPodOperator(
        name="iteration-pre-configuration",
        image="watermodelling/simulation-files-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=[
            "python3",
            "hmse_simulation_tool.py"
        ],
        arguments=[
            "--action",
            "pre_configure_iteration",
            *create_project_metadata_args_for_cli()
        ],
        labels={"simulation": "pre-configure-iteration"},
        task_id="iteration-pre-configuration",
        namespace="{{ var.value['hmse_namespace'] }}",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume", mount_path="/workspace")]
    )

    extract_to_json = KubernetesPodOperator(
        name="extract-to-json",
        image="watermodelling/simulation-files-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=[
            "python3",
            "hmse_simulation_tool.py"
        ],
        arguments=[
            "--action",
            "extract_output_to_json",
            *create_project_metadata_args_for_cli()
        ],
        labels={"simulation": "extract-modflow-results-to-json"},
        task_id="extract-to-json",
        namespace="{{ var.value['hmse_namespace'] }}",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume", mount_path="/workspace")]
    )

    upload_results = KubernetesPodOperator(
        name="upload-simulation-results",
        image="watermodelling/minio-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=["bash"],
        arguments=[
            "init.sh",
            f"cd /workspace/{project_metadata['project_id']}",
            f"zip -FSr output.zip simulation",
            f"mc cp output.zip {project_metadata['project_minio_location']}/output.zip",
        ],
        labels={"simulation": "upload-results"},
        task_id="upload-simulation-results",
        namespace="{{ var.value['hmse_namespace'] }}",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume",
                                     mount_path="/workspace")],
        env_vars=secret_env
    )

    cleanup_simulation = KubernetesPodOperator(
        name="cleanup-simulation-volume-content",
        image="watermodelling/simulation-files-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=[
            "python3",
            "hmse_simulation_tool.py"
        ],
        arguments=[
            "--action",
            "cleanup_project_volume",
            *create_project_metadata_args_for_cli()
        ],
        labels={"simulation": "cleanup"},
        task_id="cleanup-simulation-volume-content",
        namespace="{{ var.value['hmse_namespace'] }}",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume", mount_path="/workspace")]
    )

    simulation_params_to_cli_params(project_metadata) >> iteration_pre_configuration >> extract_to_json
    extract_to_json >> upload_results >> cleanup_simulation


dag = taskflow()
