def test_k_means() -> None:
    from genshinmap.models import XYPoint
    from genshinmap.img import k_means_points

    points = [
        # Cluster 1
        XYPoint(9, 9),
        XYPoint(10, 10),
        XYPoint(11, 11),
        XYPoint(12, 12),
        XYPoint(13, 13),
        # Cluster 2
        XYPoint(100, 100),
        XYPoint(101, 101),
        XYPoint(102, 102),
    ]
    clusters = k_means_points(points, 15, 2)
    top_left, bottom_right, cluster_points = clusters[0]
    assert top_left == XYPoint(9, 9)
    assert bottom_right == XYPoint(13, 13)
    assert len(cluster_points) == 5
