import pytest
from litestar.status_codes import HTTP_200_OK


@pytest.mark.asyncio
async def test_unstable_open_access_get_drand_last_stored_round_returns_round(
    open_access_test_client,
    mock_bt_client_factory,
    snapshot_json,
):
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_drand_last_stored_round=[123],
        ):
            response = await open_access_test_client.get(
                "/api/_unstable/openaccess/block/latest/drand/last_stored_round"
            )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
