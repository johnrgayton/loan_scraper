import argparse
from urllib.parse import urlencode

from loan_scraper.config import ScrapeConfig
from loan_scraper.output import write_listing_data
from loan_scraper.scraper import get_property_details, get_property_urls


def _param_or_none(value):
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    if cleaned in ("", "any", "none"):
        return None
    return str(value).strip()


def _include_flag(value):
    if value is None:
        return False
    cleaned = str(value).strip().lower()
    return cleaned in ("1", "true", "yes", "y")


def build_filters(args):
    property_type = _param_or_none(args.property_type)
    listing_type = _param_or_none(args.listing_type)

    bed_min = _param_or_none(args.bed_min)
    bed_max = _param_or_none(args.bed_max)

    path_parts = []
    if property_type:
        path_parts.append(property_type)
    if property_type and listing_type:
        path_parts.append(listing_type)
    if property_type and bed_min and bed_max:
        path_parts.append(f"{bed_min}-to-{bed_max}-bedroom")

    params = {}
    if _param_or_none(args.sfmin):
        params["sfmin"] = _param_or_none(args.sfmin)
    if _param_or_none(args.bath_min):
        params["bath-min"] = _param_or_none(args.bath_min)
    if _param_or_none(args.bath_max):
        params["bath-max"] = _param_or_none(args.bath_max)
    if _param_or_none(args.parking):
        params["parking"] = _param_or_none(args.parking)
    if _param_or_none(args.price_max):
        params["price-max"] = _param_or_none(args.price_max)

    am_values = []
    if _include_flag(args.exclude_active_adult):
        am_values.append("53")
    if _include_flag(args.require_garage):
        am_values.append("1")
    if am_values:
        params["am"] = ",".join(am_values)

    query = urlencode(params)
    path = "/".join(path_parts)
    if path:
        path = f"{path}/"
    if query:
        return f"{path}?{query}"
    return path


def build_parser():
    parser = argparse.ArgumentParser(
        description="Scrape homes.com listings and extract mortgage details."
    )
    parser.add_argument("--base-url", default=ScrapeConfig.base_url)
    parser.add_argument("--market", default=ScrapeConfig.market)
    parser.add_argument("--property-type", default=ScrapeConfig.property_type)
    parser.add_argument("--listing-type", default=ScrapeConfig.listing_type)
    parser.add_argument("--bed-min", default=ScrapeConfig.bed_min)
    parser.add_argument("--bed-max", default=ScrapeConfig.bed_max)
    parser.add_argument("--sfmin", default=ScrapeConfig.sfmin)
    parser.add_argument("--bath-min", default=ScrapeConfig.bath_min)
    parser.add_argument("--bath-max", default=ScrapeConfig.bath_max)
    parser.add_argument("--parking", default=ScrapeConfig.parking)
    parser.add_argument("--price-max", default=ScrapeConfig.price_max)
    parser.add_argument(
        "--exclude-active-adult", default=ScrapeConfig.exclude_active_adult
    )
    parser.add_argument("--require-garage", default=ScrapeConfig.require_garage)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    filters = build_filters(args)
    property_urls = get_property_urls(
        base_url=args.base_url, market=args.market, filters=filters
    )
    listing_data = get_property_details(property_urls, market=args.market)
    write_listing_data(listing_data)


if __name__ == "__main__":
    main()
