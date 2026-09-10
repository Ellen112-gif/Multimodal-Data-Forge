def sample_signature(samples):

    return [
        (
            sample.sample_id,
            sample.status,
            sample.reject_reason,
        )
        for sample in samples
    ]


def test_same_results():

    local_results = [
        ("sample_001", "accepted", None),
        (
            "sample_002",
            "rejected",
            "low_resolution",
        ),
    ]

    ray_results = [
        ("sample_001", "accepted", None),
        (
            "sample_002",
            "rejected",
            "low_resolution",
        ),
    ]

    assert local_results == ray_results