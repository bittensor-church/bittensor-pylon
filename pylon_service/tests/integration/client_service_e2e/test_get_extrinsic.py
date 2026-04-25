import pytest
from pylon_client.artanis import BlockNumber, ExtrinsicIndex, PylonNotFound
from pylon_client.artanis.v1 import GetExtrinsicResponse


def test_get_extrinsic_from_latest_block(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        block_info = client.v1.open_access.get_latest_block_info()

        response = client.v1.open_access.get_extrinsic(
            block_number=BlockNumber(block_info.number),
            extrinsic_index=ExtrinsicIndex(0),
        )

        assert isinstance(response, GetExtrinsicResponse)
        assert response.block_number == block_info.number
        assert response.extrinsic_index == 0
        assert response.extrinsic_hash
        assert response.call.call_module
        assert response.call.call_function


def test_get_extrinsic_nonexistent_block(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        with pytest.raises(PylonNotFound):
            client.v1.open_access.get_extrinsic(
                block_number=BlockNumber(999_999_999),
                extrinsic_index=ExtrinsicIndex(0),
            )


def test_get_extrinsic_out_of_bounds_index(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        block_info = client.v1.open_access.get_latest_block_info()

        with pytest.raises(PylonNotFound):
            client.v1.open_access.get_extrinsic(
                block_number=BlockNumber(block_info.number),
                extrinsic_index=ExtrinsicIndex(9999),
            )
