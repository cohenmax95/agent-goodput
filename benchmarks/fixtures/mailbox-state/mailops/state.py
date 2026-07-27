from enum import StrEnum


class Disposition(StrEnum):
    MATCHED = "MATCHED"
    HELD_FOR_SCAN = "HELD_FOR_SCAN"
    DISCARDED = "DISCARDED"


def register_scanned_response(*, source: str, image_only: bool, matched: bool) -> Disposition:
    if source == "scan_history" and image_only:
        # The source artifact stays available for operator review even after matching.
        return Disposition.HELD_FOR_SCAN
    if matched:
        return Disposition.MATCHED
    return Disposition.DISCARDED
