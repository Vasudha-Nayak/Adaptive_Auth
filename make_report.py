"""
make_report.py
--------------
Creates CSV files, PNG graphs and a concise Markdown
summary for Objective 3.

No PDF or LaTeX generation is used.
"""

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import eval_config


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CSV HELPER
# ============================================================

def save_csv(rows, filename):

    path = RESULTS_DIR / filename

    dataframe = pd.DataFrame(rows)

    dataframe.to_csv(
        path,
        index=False
    )

    return path


# ============================================================
# GRAPH 1
# ============================================================

def plot_stage_latency(performance):

    stages = performance["stage_statistics"]

    names = list(stages.keys())

    values = [
        stages[name]["mean_ms"]
        for name in names
    ]

    plt.figure(figsize=(10, 6))

    plt.bar(
        names,
        values
    )

    plt.ylabel(
        "Mean Processing Time (ms)"
    )

    plt.xlabel(
        "Authentication Stage"
    )

    plt.title(
        "Mean Processing Time by Authentication Stage"
    )

    plt.xticks(
        rotation=25,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / "01_stage_latency.png",
        dpi=eval_config.FIGURE_DPI
    )

    plt.close()


# ============================================================
# GRAPH 2
# ============================================================

def plot_login_time(performance):

    scenarios = performance["scenario_times"]

    names = list(scenarios.keys())

    values = list(scenarios.values())

    plt.figure(figsize=(10, 6))

    plt.bar(
        names,
        values
    )

    plt.ylabel(
        "Estimated Server Processing Time (ms)"
    )

    plt.xlabel(
        "Login Scenario"
    )

    plt.title(
        "Static and Adaptive Authentication Login Time"
    )

    plt.xticks(
        rotation=25,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / "02_login_time_breakdown.png",
        dpi=eval_config.FIGURE_DPI
    )

    plt.close()


# ============================================================
# GRAPH 3
# ============================================================

def plot_processing_cost(performance):

    cost = performance["server_cost"]

    labels = [
        "CPU Utilization (%)",
        "Peak Memory (KB)"
    ]

    values = [
        cost["cpu_percent"],
        cost["peak_memory_kb"]
    ]

    plt.figure(figsize=(8, 6))

    plt.bar(
        labels,
        values
    )

    plt.ylabel(
        "Measured Value"
    )

    plt.title(
        "Server Processing Cost"
    )

    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / "03_processing_cost.png",
        dpi=eval_config.FIGURE_DPI
    )

    plt.close()


# ============================================================
# GRAPH 4
# ============================================================

def plot_latency_distribution(performance):

    latency = performance["latency_distribution"]

    data = []

    labels = []

    for name, values in latency.items():

        data.append(values)
        labels.append(name)

    plt.figure(figsize=(10, 6))

    plt.boxplot(
        data,
        labels=labels
    )

    plt.ylabel(
        "Latency (ms)"
    )

    plt.xlabel(
        "Authentication Operation"
    )

    plt.title(
        "Latency Distribution"
    )

    plt.xticks(
        rotation=25,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / "04_latency_distribution.png",
        dpi=eval_config.FIGURE_DPI
    )

    plt.close()


# ============================================================
# GRAPH 5
# ============================================================

def plot_bruteforce(security):

    rows = security["brute_force"]

    dataframe = pd.DataFrame(rows)

    plt.figure(figsize=(8, 6))

    plt.plot(
        dataframe["guesses"],
        dataframe["success_probability"],
        marker="o"
    )

    plt.xscale("log")

    plt.xlabel(
        "Number of Guesses"
    )

    plt.ylabel(
        "Modeled Success Probability"
    )

    plt.title(
        "Modeled Password Brute-Force Success Probability"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / "05_bruteforce_resistance.png",
        dpi=eval_config.FIGURE_DPI
    )

    plt.close()


# ============================================================
# GRAPH 6
# ============================================================

def plot_takeover(security):

    rows = security["takeover"]

    dataframe = pd.DataFrame(rows)

    plt.figure(figsize=(8, 6))

    plt.bar(
        dataframe["scenario"],
        dataframe["probability"]
    )

    plt.ylabel(
        "Modeled Probability"
    )

    plt.xlabel(
        "Attack Scenario"
    )

    plt.title(
        "Modeled Account Takeover Probability"
    )

    plt.xticks(
        rotation=20,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / "06_takeover_probability.png",
        dpi=eval_config.FIGURE_DPI
    )

    plt.close()


# ============================================================
# GRAPH 7 - FACE ROC
# ============================================================

def plot_face_roc(security):

    roc = security.get("face_roc")

    if not roc:
        return

    dataframe = pd.DataFrame(roc)

    plt.figure(figsize=(8, 6))

    plt.plot(
        dataframe["far"],
        dataframe["tpr"]
    )

    plt.xlabel(
        "False Acceptance Rate"
    )

    plt.ylabel(
        "True Positive Rate"
    )

    plt.title(
        "Face Authentication ROC Curve"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / "07_face_roc.png",
        dpi=eval_config.FIGURE_DPI
    )

    plt.close()


# ============================================================
# SUMMARY
# ============================================================

def create_summary(
    performance,
    security
):

    stage = performance["stage_statistics"]

    scenarios = performance["scenario_times"]

    keys = security["session_keys"]

    integrity = security["integrity"]

    lines = []

    lines.append(
        "# Objective 3 Evaluation Summary"
    )

    lines.append("")

    lines.append(
        f"Evaluation date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    lines.append("")

    lines.append(
        "## Performance"
    )

    lines.append("")

    lines.append(
        "| Authentication Stage | Mean (ms) | Median (ms) | SD (ms) | P95 (ms) |"
    )

    lines.append(
        "|---|---:|---:|---:|---:|"
    )

    for name, value in stage.items():

        lines.append(
            f"| {name} | "
            f"{value['mean_ms']:.4f} | "
            f"{value['median_ms']:.4f} | "
            f"{value['std_ms']:.4f} | "
            f"{value['p95_ms']:.4f} |"
        )

    lines.append("")

    lines.append(
        "## Login Scenarios"
    )

    lines.append("")

    lines.append(
        "| Scenario | Server Processing Time (ms) |"
    )

    lines.append(
        "|---|---:|"
    )

    for name, value in scenarios.items():

        lines.append(
            f"| {name} | {value:.4f} |"
        )

    lines.append("")

    lines.append(
        "## Cryptographic Integrity"
    )

    lines.append("")

    for key, value in integrity.items():

        lines.append(
            f"- **{key}:** {value}"
        )

    lines.append("")

    lines.append(
        "## Session Key Uniqueness"
    )

    lines.append("")

    lines.append(
        f"- Keys generated: {keys['total_generated']}"
    )

    lines.append(
        f"- Unique keys: {keys['unique_keys']}"
    )

    lines.append(
        f"- Duplicate keys: {keys['duplicates']}"
    )

    lines.append(
        f"- Observed uniqueness: "
        f"{keys['uniqueness_percentage']:.4f}%"
    )

    lines.append("")

    lines.append(
        "## Important Methodological Note"
    )

    lines.append("")

    lines.append(
        "Password brute-force and account-takeover "
        "probabilities are modeled estimates based on "
        "the assumptions in eval_config.py. They should "
        "not be reported as experimentally measured "
        "attack success rates."
    )

    lines.append("")

    lines.append(
        "Face ROC analysis is generated only when "
        "real face_scores.csv data is supplied."
    )

    summary_path = (
        RESULTS_DIR / "results_summary.md"
    )

    summary_path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


# ============================================================
# MAIN
# ============================================================

def main(
    performance_results=None,
    security_results=None
):

    if performance_results is None:

        import bench_performance

        performance_results = (
            bench_performance.run_performance()
        )

    if security_results is None:

        import bench_security

        security_results = (
            bench_security.run_security()
        )

    # --------------------------------------------------------
    # CSV FILES
    # --------------------------------------------------------

    stage_rows = []

    for name, values in (
        performance_results["stage_statistics"].items()
    ):

        stage_rows.append({
            "stage": name,
            **values
        })

    save_csv(
        stage_rows,
        "stage_latency.csv"
    )


    scenario_rows = []

    for name, value in (
        performance_results["scenario_times"].items()
    ):

        scenario_rows.append({
            "scenario": name,
            "server_time_ms": value
        })

    save_csv(
        scenario_rows,
        "login_scenarios.csv"
    )


    save_csv(
        [performance_results["server_cost"]],
        "server_cost.csv"
    )


    save_csv(
        [performance_results["crypto_sizes"]],
        "crypto_sizes.csv"
    )


    save_csv(
        [performance_results["latency_distribution"]],
        "latency_distribution.csv"
    )


    save_csv(
        [security_results["integrity"]],
        "security_integrity.csv"
    )


    save_csv(
        [security_results["session_keys"]],
        "session_key_uniqueness.csv"
    )


    save_csv(
        security_results["brute_force"],
        "bruteforce_curve.csv"
    )


    save_csv(
        security_results["takeover"],
        "takeover_probability.csv"
    )


    save_csv(
        security_results["features"],
        "security_features.csv"
    )


    if security_results.get("face_roc"):

        save_csv(
            security_results["face_roc"],
            "face_roc.csv"
        )


    # --------------------------------------------------------
    # GRAPHS
    # --------------------------------------------------------

    print("\nGenerating graphs...")

    plot_stage_latency(
        performance_results
    )

    plot_login_time(
        performance_results
    )

    plot_processing_cost(
        performance_results
    )

    plot_latency_distribution(
        performance_results
    )

    plot_bruteforce(
        security_results
    )

    plot_takeover(
        security_results
    )

    plot_face_roc(
        security_results
    )


    # --------------------------------------------------------
    # ASSUMPTIONS
    # --------------------------------------------------------

    assumptions = {
        "password_hash_method":
            eval_config.PASSWORD_HASH_METHOD,

        "face_threshold":
            eval_config.FACE_THRESHOLD,

        "network_rtt_seconds":
            eval_config.NET_RTT_S,

        "human_time_seconds":
            eval_config.HUMAN_S,

        "client_face_time_seconds":
            eval_config.CLIENT_FACE_S,

        "password_vocabulary":
            eval_config.VOCAB,

        "number_of_users":
            eval_config.N_USERS,

        "attack_attempt_budget":
            eval_config.ATTEMPT_BUDGET,

        "mailbox_access_probability":
            eval_config.P_MAILBOX,

        "default_face_far":
            eval_config.FAR_DEFAULT
    }

    with open(
        RESULTS_DIR / "assumptions.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            assumptions,
            file,
            indent=4
        )


    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    metadata = {
        "evaluation_time":
            datetime.now().isoformat(),

        "crypto_backend":
            performance_results["crypto_backend"],

        "seed":
            eval_config.SEED,

        "iterations":
            eval_config.N_ITER
    }

    with open(
        RESULTS_DIR / "run_metadata.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4
        )


    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    create_summary(
        performance_results,
        security_results
    )

    print(
        "\nAll results saved to:"
    )

    print(
        RESULTS_DIR
    )


if __name__ == "__main__":

    main()