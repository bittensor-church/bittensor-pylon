from pylon_service.api._unstable.routers import unstable_router
from pylon_service.api.exception_handlers import domain_exception_handlers
from pylon_service.api.v1.routers import v1_router


def test_unstable_router_registers_version_local_exception_handlers():
    assert unstable_router.exception_handlers == domain_exception_handlers
    assert unstable_router.exception_handlers is not domain_exception_handlers


def test_v1_router_registers_version_local_exception_handlers():
    assert v1_router.exception_handlers == domain_exception_handlers
    assert v1_router.exception_handlers is not domain_exception_handlers
