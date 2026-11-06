"""Independent denominators for deliberate cold/warm cache experiments."""

from ask_phil.cache_evaluation import CacheObservation, summarize_cache_workload
from ask_phil.cache_records import CacheDelivery


def test_cache_measurements_separate_eligibility_all_requests_and_reviewed_hits() -> None:
    rows = [
        CacheObservation(
            phase="cold",
            delivery=CacheDelivery(status="miss", reason="absent", eligible=True),
            elapsed_ms=100,
            end_to_end_ms=120,
            cost_usd=0.02,
            supported=True,
        ),
        CacheObservation(
            phase="warm",
            delivery=CacheDelivery(status="hit", reason="exact", eligible=True),
            elapsed_ms=10,
            end_to_end_ms=20,
            cost_usd=0,
            supported=True,
            compatible=True,
        ),
        CacheObservation(
            phase="warm",
            delivery=CacheDelivery(status="hit", reason="exact", eligible=True),
            elapsed_ms=10,
            end_to_end_ms=20,
            cost_usd=0,
            supported=False,
            compatible=False,
        ),
        CacheObservation(
            phase="control",
            delivery=CacheDelivery(status="bypass", reason="history"),
            elapsed_ms=100,
            end_to_end_ms=120,
            cost_usd=None,
        ),
    ]
    result = summarize_cache_workload(rows)
    assert (result.requests, result.eligible, result.hits, result.misses, result.bypasses) == (
        4,
        3,
        2,
        1,
        1,
    )
    assert result.eligible_hit_rate == 2 / 3
    assert result.all_request_hit_coverage == 0.5
    assert result.reviewed_hits == 2
    assert (result.incorrect_hits, result.stale_hits) == (1, 1)
    assert result.incorrect_reuse_rate == 0.5
    assert result.stale_reuse_rate == 0.5
    assert result.support_reviewed == 3
    assert result.supported_share == 2 / 3
    assert result.cost_usd is None
    assert result.known_cost_usd == 0.02
    assert result.mean_end_to_end_ms == 70


def test_empty_or_unreviewed_workload_has_no_manufactured_accuracy() -> None:
    empty = summarize_cache_workload([])
    assert empty.eligible_hit_rate is None
    assert empty.all_request_hit_coverage is None
    assert empty.supported_share is None
    assert empty.incorrect_reuse_rate is None
    unreviewed = summarize_cache_workload(
        [
            CacheObservation(
                phase="warm",
                delivery=CacheDelivery(status="hit", reason="exact", eligible=True),
                elapsed_ms=10,
                end_to_end_ms=20,
                cost_usd=0,
            ),
        ]
    )
    assert unreviewed.reviewed_hits == 0
    assert unreviewed.incorrect_reuse_rate is None
    assert unreviewed.stale_reuse_rate is None
