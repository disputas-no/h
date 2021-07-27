from unittest import mock

import pytest
from h_matchers import Any

from h.security.permissions import Permission
from h.services.annotation_json_presentation import AnnotationJSONPresentationService


@pytest.mark.usefixtures("presenters", "formatters")
class TestAnnotationJSONPresentationService:
    def test_initializes_flag_formatter(self, services, formatters, svc):
        formatters.AnnotationFlagFormatter.assert_called_once_with(
            services["flag"], mock.sentinel.user
        )

    def test_it_configures_flag_formatter(self, services, formatters, svc):
        assert formatters.AnnotationFlagFormatter.return_value in svc.formatters

    def test_initializes_hidden_formatter(self, services, formatters, svc):
        formatters.AnnotationHiddenFormatter.assert_called_once_with(
            services["annotation_moderation"], Any.function(), mock.sentinel.user
        )

    def test_hidden_status_included_if_user_can_moderate_group(
        self, formatters, has_permission, svc
    ):
        group = mock.Mock()
        moderator_check = formatters.AnnotationHiddenFormatter.call_args[0][1]
        moderator_check(group)
        has_permission.assert_called_once_with(Permission.Group.MODERATE, group)

    def test_it_configures_hidden_formatter(self, services, formatters, svc):
        assert formatters.AnnotationHiddenFormatter.return_value in svc.formatters

    def test_initializes_moderation_formatter(
        self, services, formatters, has_permission, svc
    ):
        formatters.AnnotationModerationFormatter.assert_called_once_with(
            services["flag_count"], mock.sentinel.user, has_permission
        )

    def test_it_configures_moderation_formatter(self, services, formatters, svc):
        assert formatters.AnnotationModerationFormatter.return_value in svc.formatters

    def test_initializes_user_info_formatter(self, services, formatters, svc):
        formatters.AnnotationUserInfoFormatter.assert_called_once_with(
            mock.sentinel.db_session, services["user"]
        )

    def test_it_configures_user_info_formatter(self, services, formatters, svc):
        assert formatters.AnnotationUserInfoFormatter.return_value in svc.formatters

    def test_present_inits_presenter(self, svc, presenters, annotation_resource):
        svc.present(annotation_resource)

        presenters.AnnotationJSONPresenter.assert_called_once_with(
            annotation_resource, Any()
        )

    def test_present_adds_formatters(self, svc, annotation_resource, presenters):
        formatters = [mock.Mock(), mock.Mock()]
        svc.formatters = formatters

        svc.present(annotation_resource)

        presenters.AnnotationJSONPresenter.assert_called_once_with(Any(), formatters)

    def test_present_returns_presenter_dict(self, svc, presenters):
        presenter = presenters.AnnotationJSONPresenter.return_value

        result = svc.present(mock.Mock())

        assert result == presenter.asdict.return_value

    def test_present_all_loads_annotations_from_db(self, svc, storage):
        svc.present_all(["id-1", "id-2"])

        storage.fetch_ordered_annotations.assert_called_once_with(
            svc.session, ["id-1", "id-2"], query_processor=Any()
        )

    def test_present_all_initialises_annotation_resources(
        self, svc, storage, traversal
    ):
        ann = mock.Mock()
        storage.fetch_ordered_annotations.return_value = [ann]

        svc.present_all(["ann-1"])

        traversal.AnnotationContext.assert_called_once_with(
            ann, svc.group_svc, svc.links_svc
        )

    def test_present_all_presents_annotation_resources(
        self, svc, storage, traversal, present
    ):
        storage.fetch_ordered_annotations.return_value = [mock.Mock()]
        resource = traversal.AnnotationContext.return_value

        svc.present_all(["ann-1"])
        present.assert_called_once_with(svc, resource)

    def test_present_all_preloads_formatters(self, svc, storage):
        formatter = mock.Mock(spec_set=["preload"])
        svc.formatters = [formatter]

        svc.present_all(["ann-1", "ann-2"])

        formatter.preload.assert_called_once_with(["ann-1", "ann-2"])

    def test_returns_presented_annotations(self, svc, storage, present):
        storage.fetch_ordered_annotations.return_value = [mock.Mock()]

        result = svc.present_all(["ann-1"])
        assert result == [present.return_value]

    @pytest.fixture
    def svc(self, services, has_permission):
        return AnnotationJSONPresentationService(
            session=mock.sentinel.db_session,
            user=mock.sentinel.user,
            group_svc=services["group"],
            links_svc=services["links"],
            flag_svc=services["flag"],
            flag_count_svc=services["flag_count"],
            moderation_svc=services["annotation_moderation"],
            user_svc=services["user"],
            has_permission=has_permission,
        )

    @pytest.fixture
    def has_permission(self):
        return mock.Mock()

    @pytest.fixture
    def annotation_resource(self):
        return mock.Mock(spec_set=["annotation"], annotation=mock.Mock())

    @pytest.fixture
    def presenters(self, patch):
        return patch("h.services.annotation_json_presentation.service.presenters")

    @pytest.fixture
    def storage(self, patch):
        return patch("h.services.annotation_json_presentation.service.storage")

    @pytest.fixture
    def traversal(self, patch):
        return patch("h.services.annotation_json_presentation.service.traversal")

    @pytest.fixture
    def present(self, patch):
        return patch(
            "h.services.annotation_json_presentation.service.AnnotationJSONPresentationService.present"
        )

    @pytest.fixture
    def formatters(self, patch):
        return patch("h.services.annotation_json_presentation.service.formatters")


@pytest.fixture
def services(pyramid_config, user_service, links_service, groupfinder_service):
    service_mocks = {
        "user": user_service,
        "links": links_service,
        "group": groupfinder_service,
    }

    for name in ["flag", "flag_count", "annotation_moderation"]:
        svc = mock.Mock()
        service_mocks[name] = svc
        pyramid_config.register_service(svc, name=name)

    return service_mocks