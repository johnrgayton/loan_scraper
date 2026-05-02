from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScrapeConfig:
    base_url: str = "https://www.homes.com"
    market: str = "venice-fl"
    property_type: Optional[str] = None
    listing_type: Optional[str] = None
    bed_min: Optional[str] = None
    bed_max: Optional[str] = None
    sfmin: Optional[str] = None
    bath_min: Optional[str] = None
    bath_max: Optional[str] = None
    parking: Optional[str] = None
    price_max: Optional[str] = None
    exclude_active_adult: Optional[str] = None
    require_garage: Optional[str] = None
