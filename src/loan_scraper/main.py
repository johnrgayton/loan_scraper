import argparse

from loan_scraper.config import ScrapeConfig
from loan_scraper.output import write_listing_data
from loan_scraper.scraper import get_property_details, get_property_urls


def build_parser():
    parser = argparse.ArgumentParser(
        description="Scrape homes.com listings and extract mortgage details."
    )
    parser.add_argument("--base-url", default=ScrapeConfig.base_url)
    parser.add_argument("--market", default=ScrapeConfig.market)
    parser.add_argument("--filters", default=ScrapeConfig.filters)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    property_urls = get_property_urls(
        base_url=args.base_url, market=args.market, filters=args.filters
    )
    listing_data = get_property_details(property_urls)
    write_listing_data(listing_data)


if __name__ == "__main__":
    main()
