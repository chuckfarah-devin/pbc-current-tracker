"""
Plume source classification and snorkel suitability index (pure logic, no I/O).
"""
from app.config import settings
from app.models.conditions import (
    CurrentData, LakeOData, PlumeData, RunoffData, SnorkelIndex, TurbidityData,
)

_LABELS = [(80, "Excellent"), (60, "Good"), (40, "Fair"), (20, "Marginal"), (0, "Poor")]


def classify_plume(runoff: RunoffData, lake_o: LakeOData, current_resolution_m: int | None = None) -> PlumeData:
    east_cfs = lake_o.east_discharge_cfs_total
    c16_cfs = runoff.c16_flow_cfs
    rain_mm = runoff.recent_rain_mm

    if east_cfs is not None and east_cfs >= settings.lake_o_discharge_threshold_cfs:
        source = "LakeO"
        confidence = min(0.95, 0.6 + (east_cfs - settings.lake_o_discharge_threshold_cfs) / 5000.0)
    elif (
        c16_cfs is not None and c16_cfs >= settings.c16_flow_threshold_cfs
        and (rain_mm is None or rain_mm >= settings.c16_rain_threshold_mm)
    ):
        source = "C16_runoff"
        confidence = min(0.9, 0.5 + c16_cfs / 3000.0)
    elif c16_cfs is not None and c16_cfs >= settings.c16_flow_threshold_cfs:
        source = "C16_runoff"
        confidence = 0.55
    else:
        source = "tidal_local"
        confidence = 0.70

    resolution = (
        "macro" if source == "LakeO" else
        "meso" if source == "C16_runoff" else
        "micro" if (current_resolution_m is not None and current_resolution_m <= 100) else
        "macro"
    )
    return PlumeData(direction_deg=None, speed_mps=None,
                     source=source, confidence=round(confidence, 2),
                     resolution=resolution)


def enrich_plume_with_current(plume: PlumeData, current: CurrentData) -> PlumeData:
    return PlumeData(direction_deg=current.direction_deg, speed_mps=current.speed_mps,
                     source=plume.source, confidence=plume.confidence)


def compute_snorkel_index(
    turbidity: TurbidityData,
    current: CurrentData,
    runoff: RunoffData,
    lake_o: LakeOData,
    plume: PlumeData,
) -> SnorkelIndex:
    score = 100
    reasons: list[str] = []

    # Turbidity penalty (max -40)
    if turbidity.clarity_score is not None:
        c = turbidity.clarity_score
        if c < 20:
            score -= 40; reasons.append("Very poor water clarity")
        elif c < 40:
            score -= 28; reasons.append("Low water clarity")
        elif c < 60:
            score -= 15; reasons.append("Moderate turbidity")
        elif c < 80:
            score -= 5
    else:
        score -= 15; reasons.append("Clarity data unavailable")

    # Current speed penalty (max -25)
    spd = current.speed_mps
    if spd is not None:
        if spd > 0.75:
            score -= 25; reasons.append("Strong current (> 1.5 kn)")
        elif spd > 0.5:
            score -= 15; reasons.append("Moderate current")
        elif spd > 0.35:
            score -= 8
    else:
        score -= 5; reasons.append("Current data unavailable")

    # Runoff penalty (max -20)
    intensity = runoff.runoff_intensity
    if intensity == "high":
        score -= 20; reasons.append("High C-16 discharge")
    elif intensity == "med":
        score -= 10; reasons.append("Moderate C-16 discharge")
    elif runoff.c16_flow_cfs is None:
        score -= 5; reasons.append("Runoff data unavailable")

    # Lake O penalty (max -15)
    infl = lake_o.lake_o_influence
    if infl == "high":
        score -= 15; reasons.append("High Lake Okeechobee discharge")
    elif infl == "med":
        score -= 8; reasons.append("Moderate Lake O discharge")

    score = max(0, min(100, score))
    label = next(lbl for thr, lbl in _LABELS if score >= thr)
    return SnorkelIndex(score=score, label=label, reasons=reasons)
