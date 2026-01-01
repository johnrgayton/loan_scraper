from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapeConfig:
    base_url: str = "https://www.homes.com"
    market: str = "venice-fl"
    property_type: str = "houses-for-sale"
    listing_type: str = "resale"
    bed_min: str = "4"
    bed_max: str = "5"
    sfmin: str = "1500"
    bath_min: str = "2"
    bath_max: str = "5"
    parking: str = "2"
    price_max: str = "600000"
    exclude_active_adult: str = "true"
    require_garage: str = "true"
