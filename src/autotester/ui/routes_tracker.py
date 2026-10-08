"""Empty Group 10 tracker router and policy contribution, filled by its later unit."""

from fastapi import APIRouter

from autotester.schema.auth import RouteRule

router = APIRouter()
ROUTE_POLICY: dict[tuple[str, str], RouteRule] = {}
