"""Tests for orchestration API endpoints."""


from app.api.v1.orchestration import router


class TestOrchestrationRouter:
    def test_router_prefix(self):
        assert router.prefix == "/orchestrace"

    def test_router_tags(self):
        assert "orchestrace" in router.tags
