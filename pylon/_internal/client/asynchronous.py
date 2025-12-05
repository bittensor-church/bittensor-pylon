from pylon._internal.client.abstract import AbstractAsyncPylonClient
from pylon._internal.client.api.asynchronous import IdentityAsyncApi, OpenAccessAsyncApi
from pylon._internal.client.communicators.http import AsyncHttpCommunicator


class AsyncPylonClient(AbstractAsyncPylonClient[OpenAccessAsyncApi, IdentityAsyncApi, AsyncHttpCommunicator]):
    _open_access_api_cls = OpenAccessAsyncApi
    _identity_api_cls = IdentityAsyncApi
    _communicator_cls = AsyncHttpCommunicator
