from typing import NewType

Address = NewType("Address", str)
BlockNumber = NewType("BlockNumber", int)
TransactionHash = NewType("TransactionHash", str)
TransactionIndex = NewType("TransactionIndex", int)
LogIndex = NewType("LogIndex", int)
RpcUrl = NewType("RpcUrl", str)
