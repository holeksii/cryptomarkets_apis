import json
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from typing import Dict, Tuple

from schemas import WithdrawFeeSchema, WithdrawNetworkFeeSchema


def update_fee_dict(
    fee_dict: Dict[str, WithdrawFeeSchema],
    new_fee_dict: Dict[str, WithdrawFeeSchema],
) -> None:
    for asset, fee_schemas in new_fee_dict.items():
        if fee_dict.get(asset) is None:
            fee_dict[asset] = WithdrawFeeSchema(networks=[])
        for network_fee_schema in fee_schemas.networks:
            fee_dict[asset].networks.append(network_fee_schema)


def parse_table_row(
    row: str,
) -> Tuple[str, WithdrawNetworkFeeSchema] | Tuple[None, WithdrawNetworkFeeSchema]:
    soup = BeautifulSoup(row, "html.parser")
    asset = None
    if 'id="coin_' in row:
        info_text_div = soup.find("div", {"class": "info_text"})
        asset = info_text_div.find("a", {"class": "symbol"}).text.strip().upper()
    network = soup.find("td", {"class": "text-left"}).text.strip()
    td_text_center = soup.find_all("td", {"class": "text-center"})

    withdraw_fee = float(
        td_text_center[0].find("div", {"class": "ttop network-fee"}).text.strip()[1:]
    )
    min_withdrawal = float(
        td_text_center[2].find("div", {"class": "ttop network-min"}).text.strip()[1:]
    )

    return asset, WithdrawNetworkFeeSchema(
        network=network,
        withdraw_fee=withdraw_fee,
        min_withdrawal=min_withdrawal,
        deposit_enabled=True,
        withdraw_enabled=True,
    )


def parse_additional_networks(page: str) -> Dict[str, WithdrawFeeSchema]:
    additional_networks_json = json.loads(
        page.split("allNetworkSub= ")[1].split(";</script>")[0]
    )
    out = {}

    for asset_code, html in additional_networks_json.items():
        soup = BeautifulSoup(html["html"], "html.parser")
        if soup.prettify().strip() == "":
            continue

        wfs = WithdrawFeeSchema(networks=[])

        for row in soup.find_all("tr"):
            try:
                asset, network_fee_schema = parse_table_row(row.prettify())
                if asset is None:
                    page_soup = BeautifulSoup(page, "html.parser")
                    asset = page_soup.find("tr", {"data-id": asset_code})[
                        "name"
                    ].upper()
                if out.get(asset) is None:
                    out[asset] = wfs
                out[asset].networks.append(network_fee_schema)
            except Exception:
                pass
    return out


def parse_page(page: str) -> Dict[str, WithdrawFeeSchema]:
    soup = BeautifulSoup(page, "html.parser")
    table = soup.find("table", {"class": "box_table_list"})
    table_rows = table.find_all(
        "tr", {"class": "item_cSearch item item_coin_network table_tr_pr"}
    )

    out = {}
    asset = ""

    for row in table_rows:
        try:
            asset, fee_schema = parse_table_row(row.prettify())
            if out.get(asset) is None:
                out[asset] = WithdrawFeeSchema(networks=[])
            out[asset].netwirks.append(fee_schema)
        except Exception:
            pass

    additional_networks = parse_additional_networks(page)
    update_fee_dict(out, additional_networks)

    return out


def parse_all_pages(url: str, market: str, pages: int) -> Dict[str, WithdrawFeeSchema]:
    out = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for page_num in range(1, pages):
            futures.append(
                executor.submit(
                    requests.get, url.format(market=market, page=page_num), timeout=10
                )
            )
        for future in concurrent.futures.as_completed(futures):
            page = future.result()
            if BeautifulSoup(page.text, "html.parser").find("table") is None:
                break
            update_fee_dict(out, parse_page(page.text))
    return out
