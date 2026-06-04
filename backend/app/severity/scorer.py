def calculate_severity(anomalies_df):
    if anomalies_df.empty:
        return "Healthy", 0

    anomaly_count = len(anomalies_df)
    max_score = anomalies_df["anomaly_score"].max() if "anomaly_score" in anomalies_df else 1

    score = anomaly_count * max_score

    if score >= 10:
        return "P1 Critical", round(score, 2)
    elif score >= 6:
        return "P2 High", round(score, 2)
    elif score >= 3:
        return "P3 Medium", round(score, 2)
    else:
        return "P4 Low", round(score, 2)
