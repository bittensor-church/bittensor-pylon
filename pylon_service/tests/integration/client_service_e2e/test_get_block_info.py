from pylon_client.artanis.v1 import GetLatestBlockInfoResponse


def test_get_latest_block_info(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.v1.open_access.get_latest_block_info()

        assert isinstance(response, GetLatestBlockInfoResponse)
        assert response.number > 0
        assert response.hash
        assert response.timestamp > 0
