"""
Provider verification tests using Pact Verifier.

This module verifies that the service honors all contracts defined by consumers.
The Verifier replays interactions from pact files against the actual running service.
"""

from pact import Verifier

from tests.pact.state_handlers import StateHandler


def test_provider_honors_pact_with_pylon_client(
    provider_server,
    open_access_mock_bt_client,
    sn1_mock_bt_client,
    sn2_mock_bt_client,
    pacts_dir,
    provider_url,
    mock_stores,
    monkeypatch,
):
    """
    Verify that pylon_service honors all contracts with pylon_client.

    The Verifier:
    1. Loads pact files from the pacts directory
    2. For each interaction, calls the state handler to set up mock behavior
    3. Makes HTTP request to the running provider
    4. Verifies response matches the contract
    5. Calls teardown to clean up mock state
    """
    verifier = (
        Verifier("pylon_service")
        .add_source(str(pacts_dir))
        .add_transport(url=provider_url)
        .state_handler(
            StateHandler.create_all(
                open_access_mock_bt_client, sn1_mock_bt_client, sn2_mock_bt_client, mock_stores, monkeypatch
            ),
            teardown=True,
        )
    )

    verifier.verify()
