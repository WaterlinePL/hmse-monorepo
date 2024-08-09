from typing import List, Dict, Union, Set, Tuple


def create_project_metadata_args_for_cli() -> List[str]:
    return [
        "--project_id",
        "{{ task_instance.xcom_pull(task_ids='simulation-params-to-cli-params', key='return_value').get('project_id') }}",
        "--start_date",
        "{{ task_instance.xcom_pull(task_ids='simulation-params-to-cli-params', key='return_value').get('start_date') }}",
        "--modflow_metadata",
        "{{ task_instance.xcom_pull(task_ids='simulation-params-to-cli-params', key='return_value').get('modflow_metadata') }}",
        "--shapes_to_hydrus",
        "{{ task_instance.xcom_pull(task_ids='simulation-params-to-cli-params', key='return_value').get('shapes_to_hydrus') }}",
        "--hydrus_to_weather",
        "{{ task_instance.xcom_pull(task_ids='simulation-params-to-cli-params', key='return_value').get('hydrus_to_weather') }}",
        "--spin_up",
        "{{ task_instance.xcom_pull(task_ids='simulation-params-to-cli-params', key='return_value').get('spin_up', '0') }}",
        "{{ '--is_feedback_loop' if task_instance.xcom_pull(task_ids='simulation-params-to-cli-params', key='return_value')"
        ".get('is_feedback_loop') else '--no_feedback_loop' }}"
    ]


def prepare_cli_config(simulation_config: Dict) -> Dict:
    cli_ready_config = {**simulation_config}
    return cli_ready_config


def get_used_hydrus_models(shapes_to_hydrus: Dict[str, Union[str, float]]) -> Set[str]:
    return {hydrus_id for hydrus_id in shapes_to_hydrus.values()
            if isinstance(hydrus_id, str)}


def get_compound_hydrus_ids_for_feedback_loop(shapes_to_hydrus: Dict[str, Union[str, float]]) -> Set[Tuple[str, str]]:
    return {f"{hydrus_id}--{shape_id}"
            for shape_id, hydrus_id in shapes_to_hydrus.items()
            if isinstance(hydrus_id, str)}
