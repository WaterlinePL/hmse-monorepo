import datetime

from server import cookie_utils


def test_is_unused_project_free():
    assert not cookie_utils.is_project_used_by_another_user("unused-project", "test-uuid")


def test_is_freshly_accessed_project_accessible_for_owner():
    test_user_id = "test-uuid"
    test_project_id = "test-project-name"
    cookie_utils.set_project_id_for_user(test_user_id, test_project_id)
    assert not cookie_utils.is_project_used_by_another_user(test_project_id, test_user_id)


def test_is_freshly_accessed_project_inaccessible_by_other():
    test_project_id = "test-project-name"
    cookie_utils.set_project_id_for_user("owner_test_uuid", test_project_id)
    assert cookie_utils.is_project_used_by_another_user(test_project_id, "other_browser_uuid")


def test_is_outdated_access_project_free(mocker):
    test_project_id = "test-project-name"
    owner_user_id = "owner_test_uuid"

    mocker_datetime = mocker.patch("server.cookie_utils.dt")
    setup_past_access_for_tests(mocker_datetime, test_project_id, owner_user_id)

    current_time = datetime.datetime.now()
    mocker_datetime.datetime.now.return_value = current_time
    assert not cookie_utils.is_project_used_by_another_user(test_project_id, "other_browser_uuid")


def test_refreshing_project(mocker):
    test_project_id = "test-project-name"
    owner_user_id = "owner_test_uuid"
    another_user_id = "other_browser_uuid"

    mocker_datetime = mocker.patch("server.cookie_utils.dt")
    setup_past_access_for_tests(mocker_datetime, test_project_id, owner_user_id)

    current_time = datetime.datetime.now()
    mocker_datetime.datetime.now.return_value = current_time
    assert not cookie_utils.is_project_used_by_another_user(test_project_id, another_user_id)

    cookie_utils.refresh_user_access(test_project_id)
    assert cookie_utils.is_project_used_by_another_user(test_project_id, another_user_id)


def setup_past_access_for_tests(mocker_datetime, test_project_id, owner_user_id):
    outdated_last_access = datetime.datetime.now() - datetime.timedelta(days=1)
    mocker_datetime.datetime.now.return_value = outdated_last_access
    mocker_datetime.timedelta = datetime.timedelta
    cookie_utils.set_project_id_for_user(owner_user_id, test_project_id)
