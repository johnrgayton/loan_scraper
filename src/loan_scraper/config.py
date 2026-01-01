from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapeConfig:
    base_url: str = "https://www.homes.com"
    market: str = "venice-fl"
    filters: str = (
        "houses-for-sale/resale/4-to-5-bedroom/"
        "?sfmin=1500&am=53,1&bath-min=2&bath-max=5&parking=2&price-max=600000"
    )
    output_dir: str = "/Users/johngayton/Desktop/homes_com_scraping"
