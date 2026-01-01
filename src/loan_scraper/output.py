import csv
import os
import re
from datetime import date


def write_listing_data(final_data, output_dir, market):
    cur_dt = date.today().strftime("%Y%m%d")
    state = re.search("-([a-z]{2})$", market).group(1)
    folder_path = os.path.join(output_dir, state)
    file_path = f"{market}_{cur_dt}.csv"

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    full_file = os.path.join(folder_path, file_path)

    with open(full_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        # header row
        writer.writerow(
            [
                "property_url",
                "address",
                "price",
                "features",
                "beds",
                "baths",
                "sq_ft",
                "description",
                "current_mortgage_type",
                "current_mortgage_term",
                "current_mortgage_start_dt",
                "current_mortgage_status",
                "current_mortgage_amount",
                "current_mortgage_balance",
                "current_mortgage_rate",
            ]
        )

        for dat in final_data:
            writer.writerow(dat)
