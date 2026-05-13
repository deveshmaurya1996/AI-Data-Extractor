from ai.interfaces import EntityExtractionResult
from ai.semantic_intent_router import SemanticIntent, route_semantic_intent


def _entities_one(name: str = "Alice Chen") -> EntityExtractionResult:
    return EntityExtractionResult(
        customer_name=name,
        customer_candidates=[
            {"id": 1, "name": name, "schema": "ecommerce"},
        ],
        time_period=None,
        keywords=[],
        requires_clarification=False,
        spoken_customer_term="alice",
    )


def test_customer_360_phrase():
    r = route_semantic_intent(
        "show me all data related to Alice Chen",
        _entities_one(),
        has_uploads=False,
    )
    assert r.intent == SemanticIntent.CUSTOMER_360


def test_open_tickets_not_hijacked_as_360():
    r = route_semantic_intent(
        "open tickets for Alice Chen",
        _entities_one(),
        has_uploads=False,
    )
    assert r.intent is None


def test_upload_preview_when_flagged():
    r = route_semantic_intent(
        "show me my uploaded csv file",
        EntityExtractionResult(
            customer_name=None,
            customer_candidates=[],
            time_period=None,
            keywords=[],
            requires_clarification=False,
        ),
        has_uploads=True,
    )
    assert r.intent == SemanticIntent.UPLOAD_DATASET_PREVIEW


def test_show_me_all_data_without_customer_is_sample_overview():
    r = route_semantic_intent(
        "show me all data",
        EntityExtractionResult(
            customer_name=None,
            customer_candidates=[],
            time_period=None,
            keywords=[],
            requires_clarification=False,
        ),
        has_uploads=False,
    )
    assert r.intent == SemanticIntent.SAMPLE_DATA_OVERVIEW


def test_show_me_all_data_with_one_resolved_customer_stays_360():
    r = route_semantic_intent(
        "show me all data",
        _entities_one(),
        has_uploads=False,
    )
    assert r.intent == SemanticIntent.CUSTOMER_360


def test_show_me_x_data_routes_to_customer_360_when_resolved():
    r = route_semantic_intent(
        "show me alice data",
        _entities_one(),
        has_uploads=False,
    )
    assert r.intent == SemanticIntent.CUSTOMER_360


def test_bare_customer_name_routes_to_customer_360_when_resolved():
    r = route_semantic_intent(
        "Alice Chen",
        _entities_one(),
        has_uploads=False,
    )
    assert r.intent == SemanticIntent.CUSTOMER_360


def test_bare_name_falls_through_when_no_candidates():
    r = route_semantic_intent(
        "Alice Chen",
        EntityExtractionResult(
            customer_name=None,
            customer_candidates=[],
            time_period=None,
            keywords=[],
            requires_clarification=False,
        ),
        has_uploads=False,
    )
    assert r.intent is None
