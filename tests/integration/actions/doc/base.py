""" base class for doc tests
"""
import difflib
import json
import os

import pytest

from typing import Optional

from ..._common import fixture_path_from_request
from ..._common import update_fixtures
from ..._tmux_session import TmuxSession

from ....defaults import FIXTURES_COLLECTION_DIR


class BaseClass:
    """base class for interactive doc tests"""

    UPDATE_FIXTURES = False
    TEST_FOR_MODE: Optional[str] = None

    @staticmethod
    @pytest.fixture(scope="module", name="tmux_doc_session")
    def fixture_tmux_doc_session(request):
        """tmux fixture for this module"""
        params = {
            "pane_height": "2000",
            "pane_width": "200",
            "setup_commands": [
                f"export ANSIBLE_COLLECTIONS_PATH={FIXTURES_COLLECTION_DIR}",
                "export ANSIBLE_DEVEL_WARNING=False",
                "export ANSIBLE_DEPRECATION_WARNINGS=False",
            ],
            "unique_test_id": request.node.nodeid,
        }
        with TmuxSession(**params) as tmux_session:
            yield tmux_session

    def test(
        self, request, tmux_doc_session, index, user_input, comment, testname, expected_in_output
    ):
        # pylint:disable=unused-argument
        # pylint: disable=too-few-public-methods
        # pylint: disable=too-many-arguments
        """test interactive/stdout config"""
        if self.TEST_FOR_MODE == "interactive":
            search_within_response = ":help help"
        elif self.TEST_FOR_MODE == "stdout":
            search_within_response = tmux_doc_session.cli_prompt
        else:
            raise ValueError(
                "Value of 'TEST_FOR_MODE' is not set."
                " Valid value is either 'interactive' or 'stdout'"
            )

        received_output = tmux_doc_session.interaction(user_input, search_within_response)
        updated_received_output = []
        mask = "X" * 50
        for line in received_output:
            if tmux_doc_session.cli_prompt in line:
                updated_received_output.append(mask)
            elif "filename" in line or "│warnings:" in line:
                updated_received_output.append(mask)
            else:
                for value in ["time=", "skipping entry", "failed:", "permission denied"]:
                    if value in line:
                        break
                else:
                    updated_received_output.append(line)

        if expected_in_output:
            for out in expected_in_output:
                assert any(out in line for line in received_output), (out, received_output)
        else:
            if (
                self.UPDATE_FIXTURES
                or os.environ.get("ANSIBLE_NAVIGATOR_UPDATE_TEST_FIXTURES") == "true"
            ):
                update_fixtures(request, index, updated_received_output, comment, testname=testname)

            dir_path, file_name = fixture_path_from_request(request, index, testname=testname)
            with open(f"{dir_path}/{file_name}", encoding="utf-8") as infile:
                expected_output = json.load(infile)["output"]
            assert expected_output == updated_received_output, "\n" + "\n".join(
                difflib.unified_diff(
                    expected_output, updated_received_output, "expected", "received"
                )
            )