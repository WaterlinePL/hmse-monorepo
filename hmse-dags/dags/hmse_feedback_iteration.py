import json
from datetime import datetime
from typing import Dict, List

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.python import get_current_context
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.trigger_rule import TriggerRule
from kubernetes.client import V1Volume, V1VolumeMount, \
    V1PersistentVolumeClaimVolumeSource

from hmse_utils import create_project_metadata_args_for_cli, prepare_cli_config, \
    get_compound_hydrus_ids_for_feedback_loop

default_args = {'start_date': datetime(2022, 1, 1)}
DAG_ID = "hmse_feedback_iteration"


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
    tags=['hmse', 'k8s', 'feedback', 'iteration'],
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
        used_hydrus_models = get_compound_hydrus_ids_for_feedback_loop(metadata["shapes_to_hydrus"])
        return [f"{metadata['project_id']}/simulation/hydrus/{model}" for model in used_hydrus_models]

    @task(task_id="prepare-modflow-volume-subpath")
    def prepare_modflow_model_subpath(metadata: Dict) -> List[str]:
        return [f"{metadata['project_id']}/simulation/modflow/{metadata['modflow_metadata']['modflow_id']}"]

    pvc_name = Variable.get("simulation_pvc")

    project_metadata = extract_simulation_params()
    hydrus_subpaths = prepare_hydrus_models_subpaths(project_metadata)
    the_only_modflow_subpath = prepare_modflow_model_subpath(project_metadata)

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

    initialize_feedback_iteration = KubernetesPodOperator(
        name="initialize-feedback-iteration",
        image="watermodelling/simulation-files-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=[
            "python3",
            "hmse_simulation_tool.py"
        ],
        arguments=[
            "--action",
            "initialize_feedback_iteration",
            *create_project_metadata_args_for_cli()
        ],
        labels={"simulation": "iteration-files"},
        task_id="initialize-feedback-iteration",
        namespace="{{ var.value['hmse_namespace'] }}",
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume", mount_path="/workspace")]
    )

    transfer_modflow_data_to_hydrus = KubernetesPodOperator(
        name="transfer-modflow-results-to-hydrus",
        image="watermodelling/simulation-files-manipulation-job:{{ var.value['hmse_version'] }}",
        cmds=[
            "python3",
            "hmse_simulation_tool.py"
        ],
        arguments=[
            "--action",
            "transfer_data_from_modflow_to_hydrus",
            *create_project_metadata_args_for_cli()
        ],
        labels={"simulation": "transfer-modflow-results-to-hydrus"},
        task_id="transfer-modflow-results-to-hydrus",
        namespace="{{ var.value['hmse_namespace'] }}",
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
        volumes=[V1Volume(name="simulation-volume",
                          persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))],
        volume_mounts=[V1VolumeMount(name="simulation-volume", mount_path="/workspace")]
    )

    modflow_simulation = KubernetesPodOperator.partial(
        name="modflow-simulation",
        image="mjstealey/docker-modflow:latest",
        cmds=["bash", "-cx"],
        arguments=["find /workspace -name *.nam | mf2005"],
        labels={"simulation": "modflow"},
        task_id="modflow-simulation",
        namespace="{{ var.value['hmse_namespace'] }}",
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

    simulation_params_to_cli_params(project_metadata) >> iteration_pre_configuration >> initialize_feedback_iteration
    initialize_feedback_iteration >> transfer_modflow_data_to_hydrus >> hydrus_simulation
    hydrus_simulation >> transfer_hydrus_data_to_modflow >> modflow_simulation


dag = taskflow()
