from scripts.weight_grid import enumerate_grid


def test_grid_has_1771_vectors_that_sum_to_one():
    vectors = enumerate_grid()
    assert len(vectors) == 1771
    assert all(abs(sum(vector.values()) - 1.0) < 1e-9 for vector in vectors)
    assert len({tuple(sorted(vector.items())) for vector in vectors}) == 1771
