HOTKEY_1 = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
HOTKEY_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
COLDKEY = "5" + "C" * 47
BLOCK_HASH = "0x" + "a" * 64
BLOCK_NUMBER = 1000
COMMITMENT_HEX = "0xaabbccdd11223344"
IDENTITY_NAME = "sn1"
IDENTITY_TOKEN = "sn1_token"
OPEN_ACCESS_TOKEN = "test_token"
NETUID = 1
NETUID_2 = 2
BLOCK_TIMESTAMP = 1700000000
EXTRINSIC_INDEX = 0
EXTRINSIC_HASH = "0x" + "b" * 64
PRICE_VALUE_RAO = 1_000_000
PRICE_VALUE_RAO_2 = 2_000_000
EVM_CONTRACT_ADDRESS = "0x" + "d" * 40
EVM_FROM_BLOCK = 100
EVM_TO_BLOCK = 200
EVM_TRANSACTION_HASH = "0x" + "e" * 64
EVM_TRANSFER_ABI = [
    {
        "type": "event",
        "name": "Transfer",
        "anonymous": False,
        "inputs": [
            {"name": "from", "type": "address", "indexed": True},
            {"name": "to", "type": "address", "indexed": True},
            {"name": "value", "type": "uint256", "indexed": False},
        ],
    }
]
