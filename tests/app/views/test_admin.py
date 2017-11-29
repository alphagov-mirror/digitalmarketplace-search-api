import mock
import pytest
from flask import json
from nose.tools import assert_equal

from tests.app.helpers import BaseApplicationTest, assert_response_status, get_json_from_response


pytestmark = pytest.mark.usefixtures("services_mapping")


class TestSearchIndexes(BaseApplicationTest):
    def test_should_be_able_create_and_delete_index(self):
        response = self.create_index()
        assert_response_status(response, 200)
        assert_equal(get_json_from_response(response)["message"],
                     "acknowledged")

        response = self.client.get('/index-to-create')
        assert_response_status(response, 200)

        response = self.client.delete('/index-to-create')
        assert_response_status(response, 200)
        assert_equal(get_json_from_response(response)["message"],
                     "acknowledged")

        response = self.client.get('/index-to-create')
        assert_response_status(response, 404)

    def test_should_be_able_to_create_aliases(self):
        self.create_index()
        response = self.client.put('/index-alias', data=json.dumps({
            "type": "alias",
            "target": "index-to-create"
        }), content_type="application/json")

        assert_response_status(response, 200)
        assert_equal(get_json_from_response(response)["message"], "acknowledged")

    def test_should_not_be_able_to_delete_aliases(self):
        self.create_index()
        self.client.put('/index-alias', data=json.dumps({
            "type": "alias",
            "target": "index-to-create"
        }), content_type="application/json")

        response = self.client.delete('/index-alias')

        assert_response_status(response, 400)
        assert_equal(get_json_from_response(response)["error"], "Cannot delete alias 'index-alias'")

    def test_should_not_be_able_to_delete_index_with_alias(self):
        self.create_index()
        self.client.put('/index-alias', data=json.dumps({
            "type": "alias",
            "target": "index-to-create"
        }), content_type="application/json")

        response = self.client.delete('/index-to-create')

        assert_response_status(response, 400)
        assert_equal(
            get_json_from_response(response)["error"],
            "Index 'index-to-create' is aliased as 'index-alias' and cannot be deleted"
        )

    def test_cant_create_alias_for_missing_index(self):
        response = self.client.put('/index-alias', data=json.dumps({
            "type": "alias",
            "target": "index-to-create"
        }), content_type="application/json")

        assert_response_status(response, 404)
        assert get_json_from_response(response)["error"].startswith(
            'index_not_found_exception: no such index')

    def test_cant_replace_index_with_alias(self):
        self.create_index()
        response = self.client.put('/index-to-create', data=json.dumps({
            "type": "alias",
            "target": "index-to-create"
        }), content_type="application/json")

        assert_response_status(response, 400)
        assert_equal(get_json_from_response(response)["error"],
                     'invalid_alias_name_exception: Invalid alias name [index-to-create], an index exists with the '
                     'same name as the alias (index-to-create)')

    def test_can_update_alias(self):
        self.create_index()
        self.create_index('index-to-create-2')
        self.client.put('/index-alias', data=json.dumps({
            "type": "alias",
            "target": "index-to-create"
        }), content_type="application/json")

        response = self.client.put('/index-alias', data=json.dumps({
            "type": "alias",
            "target": "index-to-create-2"
        }), content_type="application/json")

        assert_response_status(response, 200)
        status = get_json_from_response(self.client.get('/_all'))["status"]
        assert_equal(status['index-to-create']['aliases'], [])
        assert_equal(status['index-to-create-2']['aliases'], ['index-alias'])

    def test_creating_existing_index_updates_mapping(self):
        self.create_index()

        with self.app.app_context():
            with mock.patch(
                'app.main.services.search_service.es.indices.put_mapping'
            ) as es_mock:
                response = self.create_index()

        assert_response_status(response, 200)
        assert_equal("acknowledged", get_json_from_response(response)["message"])
        es_mock.assert_called_with(
            index='index-to-create',
            doc_type='services',
            body=mock.ANY
        )

    def test_should_not_be_able_delete_index_twice(self):
        self.create_index()
        self.client.delete('/index-to-create')
        response = self.client.delete('/index-to-create')
        assert_response_status(response, 404)
        assert_equal(get_json_from_response(response)["error"],
                     'index_not_found_exception: no such index (index-to-create)')

    def test_should_return_404_if_no_index(self):
        response = self.client.get('/index-does-not-exist')
        assert_response_status(response, 404)
        assert_equal(get_json_from_response(response)["error"],
                     "index_not_found_exception: no such index (index-does-not-exist)")

    def test_bad_mapping_name_gives_400(self):
        response = self.client.put('/index-to-create', data=json.dumps({
            "type": "index",
            "mapping": "some-bad-mapping"
        }), content_type="application/json")

        assert_response_status(response, 400)
        assert get_json_from_response(response)["error"] == "Mapping definition named 'some-bad-mapping' not found."
