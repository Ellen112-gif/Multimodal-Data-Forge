import matplotlib.pyplot as plt


samples = [100, 500, 1000]

local = [5.77, 4.73, 4.60]
ray_2w = [5.67, 5.48, 5.55]
ray_4w = [7.06, 7.79, 8.04]


plt.figure(figsize=(9, 5.5))

plt.plot(
    samples,
    local,
    marker="o",
    linewidth=2.2,
    markersize=7,
    label="Local",
)

plt.plot(
    samples,
    ray_2w,
    marker="o",
    linewidth=2.2,
    markersize=7,
    label="Ray-2W",
)

plt.plot(
    samples,
    ray_4w,
    marker="o",
    linewidth=2.2,
    markersize=7,
    label="Ray-4W",
)

plt.xlabel(
    "Dataset Size (samples)",
    fontsize=12,
)

plt.ylabel(
    "Throughput (samples/s)",
    fontsize=12,
)

plt.title(
    "Multimodal Data Pipeline Scaling Benchmark",
    fontsize=14,
    fontweight="bold",
)

plt.xticks(
    samples,
    ["100", "500", "1,000"],
)

plt.grid(
    axis="y",
    linestyle="--",
    alpha=0.3,
)

plt.legend(
    frameon=False,
    fontsize=11,
)

plt.annotate(
    "8.04 samples/s\n1.75× vs Local",
    xy=(1000, 8.04),
    xytext=(700, 8.65),
    arrowprops={
        "arrowstyle": "->",
        "lw": 1.2,
    },
    fontsize=10,
    fontweight="bold",
)

plt.ylim(4.0, 9.2)

plt.tight_layout()

plt.savefig(
    "benchmarks/scaling_benchmark.png",
    dpi=300,
    bbox_inches="tight",
)

plt.show()