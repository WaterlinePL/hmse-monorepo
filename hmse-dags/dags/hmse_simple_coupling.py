import json
from datetime import datetime
from typing import Dict, List

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.python import BranchPythonOperator, get_current_context
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.trigger_rule import TriggerRule
from kubernetes.client import V1EnvVar, V1EnvVarSource, V1SecretKeySelector, V1Volume, V1VolumeMount, \
    V1PersistentVolumeClaimVolumeSource, V1ResourceRequirements

from hmse_utils import create_project_metadata_args_for_cli, get_used_hydrus_models, prepare_cli_config

default_args = {'start_date': datetime(2022, 1, 1)}
REST_CALL_MAX_TIME = 60
DAG_ID = "hmse_simple_coupling"


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
    tags=['operator', 'k8s'],
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

    @task(task_id="prepare-hydrus-volume-subpaths")
    def prepare_hydrus_models_subpaths(metadata: Dict) -> List[str]:
        used_hydrus_models = get_used_hydrus_models(metadata["shapes_to_hydrus"])
        return [f"{metadata['project_id']}/simulation/hydrus/{model}" for model in used_hydrus_models]

    @task(task_id="prepare-modflow-volume-subpath")
    def prepare_modflow_model_subpath(metadata: Dict) -> List[str]:
        return [f"{metadata['project_id']}/simulation/modflow/{metadata['modflow_metadata']['modflow_id']}"]

    @task(task_id="prepare-download-params")
    def prepare_download_params(metadata: Dict) -> List[Dict[str, str]]:
        return [{
            "project_id": metadata["project_id"],
            "minio_project_path": metadata['project_minio_location']
        }]

    def branch_weather_file_transfer(metadata: Dict):
        use_weather_files = len(metadata["hydrus_to_weather"]) > 0
        use_hydrus = len(metadata["shapes_to_hydrus"]) > 0

        print(f"Use weather files: {use_weather_files}")
        print(f"Use Hydrus: {use_hydrus}")

        if use_weather_files and use_hydrus:
            return ["transfer-weather-files", "branch-hydrus"]
        else:
            return ["branch-hydrus"]

    def branch_hydrus(metadata: Dict):
        use_hydrus = len(metadata["shapes_to_hydrus"]) > 0
        print(f"Use Hydrus: {use_hydrus}")

        if use_hydrus:
            return ["hydrus-simulation", "transfer-hydrus-results-to-modflow", "modflow-simulation"]
        else:
            return ["modflow-simulation"]

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
    hydrus_subpaths = prepare_hydrus_models_subpaths(project_metadata)
    the_only_modflow_subpath = prepare_modflow_model_subpath(project_metadata)
    download_params = prepare_download_params(project_metadata)

    prepare_simulation = KubernetesPodOperator.partial(
        
        name="prepare-simulation",
        image="watermodelling/minio-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=["bash"],
        labels={"simulation": "preparation"},
        task_id="prepare-simulation-volume-content",
        container_resources=V1ResourceRequirements(requests={'cpu': '1000m'}),
        image_pull_policy="IfNotPresent",
        namespace="{{ var.value['hmse_namespace'] }}",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume", mount_path="/workspace")],
        env_vars=secret_env
    ).expand(arguments=download_params.map(
        lambda params:
        [
            "init.sh",
            f"echo {params['project_id']}",
            f"mc cp {params['minio_project_path']} /workspace/ --recursive",
            f"mkdir /workspace/{params['project_id']}/simulation",
            f"cp -R /workspace/{params['project_id']}/hydrus /workspace/{params['project_id']}/simulation/"
            f"cp -R /workspace/{params['project_id']}/modflow /workspace/{params['project_id']}/simulation/"
        ]
    ))

    branch_weather_files = BranchPythonOperator(
        task_id='branch-weather-file-transfer',
        op_kwargs={"metadata": project_metadata},
        python_callable=branch_weather_file_transfer,
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS
    )

    weather_transfer = KubernetesPodOperator(
        name="transfer-weather-files",
        image="watermodelling/simulation-files-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=[
            "python3",
            "hmse_simulation_tool.py"
        ],
        arguments=[
            "--action",
            "weather_data_transfer_to_hydrus",
            *create_project_metadata_args_for_cli()
        ],
        labels={"simulation": "transfer-weather"},
        task_id="transfer-weather-files",
        container_resources=V1ResourceRequirements(requests={'cpu': '1000m'}),
        image_pull_policy="IfNotPresent",
        namespace="{{ var.value['hmse_namespace'] }}",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume", mount_path="/workspace")]
    )

    branch_hydrus_simulation = BranchPythonOperator(
        task_id='branch-hydrus',
        op_kwargs={"metadata": project_metadata},
        python_callable=branch_hydrus,
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS
    )

    transfer_hydrus_data_to_modflow = KubernetesPodOperator(
        name="transfer-hydrus-results-to-modflow",
        image="watermodelling/simulation-files-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=[
            "python3",
            "hmse_simulation_tool.py"
        ],
        arguments=[
            "--action",
            "transfer_data_from_hydrus_to_modflow",
            *create_project_metadata_args_for_cli()
        ],
        labels={"simulation": "transfer-hydrus-results-to-modflow"},
        task_id="transfer-hydrus-results-to-modflow",
        namespace="{{ var.value['hmse_namespace'] }}",
        container_resources=V1ResourceRequirements(requests={'cpu': '1000m'}),
        image_pull_policy="IfNotPresent",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume", mount_path="/workspace")]
    )

    hydrus_simulation = KubernetesPodOperator.partial(
        name="hydrus-simulation",
        image="watermodelling/hydrus-1d-linux:{{ var.value['hmse_version'] }}",
        cmds=["./hydrus"],
        labels={"simulation": "hydrus"},
        task_id="hydrus-simulation",
        namespace="{{ var.value['hmse_namespace'] }}",
        container_resources=V1ResourceRequirements(requests={'cpu': '1000m'}),
        image_pull_policy="IfNotPresent",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))]
    ).expand(volume_mounts=hydrus_subpaths.map(
        lambda model_subpath:
        [
            V1VolumeMount(name="simulation-volume",
                          mount_path="/workspace",
                          sub_path=model_subpath)
        ]
    ))

    modflow_simulation = KubernetesPodOperator.partial(
        name="modflow-simulation",
        image="mjstealey/docker-modflow:latest",
        cmds=["bash", "-cx"],
        arguments=["find /workspace -name *.nam | mf2005"],
        labels={"simulation": "modflow"},
        task_id="modflow-simulation",
        namespace="{{ var.value['hmse_namespace'] }}",
        container_resources=V1ResourceRequirements(requests={'cpu': '1000m'}),
        image_pull_policy="IfNotPresent",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS
    ).expand(volume_mounts=the_only_modflow_subpath.map(
        lambda model_subpath:
        [
            V1VolumeMount(name="simulation-volume",
                          mount_path="/workspace",
                          sub_path=model_subpath)
        ]
    ))

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
        container_resources=V1ResourceRequirements(requests={'cpu': '1000m'}),
        image_pull_policy="IfNotPresent",
        namespace="{{ var.value['hmse_namespace'] }}",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume",
                                     mount_path="/workspace")],
        env_vars=secret_env
    )

    cleanup_simulation = KubernetesPodOperator(
        name="cleanup-simulation-volume-content",
        image="watermodelling/minio-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=["bash"],
        arguments=[
            "init.sh",
            f"rm -rf /workspace/{project_metadata['project_id']}"
        ],
        labels={"simulation": "cleanup"},
        task_id="cleanup-simulation-volume-content",
        namespace="{{ var.value['hmse_namespace'] }}",
        container_resources=V1ResourceRequirements(requests={'cpu': '1000m'}),
        image_pull_policy="IfNotPresent",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume",
                                     mount_path="/workspace")],
        env_vars=secret_env
    )

    prepare_simulation >> simulation_params_to_cli_params(project_metadata) >> branch_weather_files
    branch_weather_files >> [weather_transfer, branch_hydrus_simulation]
    weather_transfer >> branch_hydrus_simulation >> [hydrus_simulation, modflow_simulation]
    hydrus_simulation >> transfer_hydrus_data_to_modflow >> modflow_simulation >> upload_results >> cleanup_simulation


dag = taskflow()
