from __future__ import annotations

import pytest
from pylon_commons.models import SubnetPrice, SubnetPrices


@pytest.mark.asyncio
async def test_get_alpha_prices_returns_prepared_subnets(open_contact, prepared_subnets):
    """
    All-subnets alpha prices include every prepared subnet with non-negative rao values.
    """
    block = await open_contact.get_latest_block()

    result = await open_contact.get_alpha_prices(block)

    assert isinstance(result, SubnetPrices)
    assert result.block == block
    prepared_netuids = {subnet.netuid for subnet in prepared_subnets}
    assert prepared_netuids <= set(result.prices)
    assert all(price.value >= 0 for price in result.prices.values())


@pytest.mark.asyncio
async def test_get_alpha_price_matches_all_subnets_entry(open_contact, prepared_subnets):
    """
    Single-subnet alpha price for a prepared subnet matches its entry in the all-subnets result.
    """
    netuid = prepared_subnets[0].netuid
    block = await open_contact.get_latest_block()
    all_prices = await open_contact.get_alpha_prices(block)

    result = await open_contact.get_alpha_price(netuid, block)

    assert isinstance(result, SubnetPrice)
    assert result.netuid == netuid
    assert result.block == block
    assert result.price == all_prices.prices[netuid]
