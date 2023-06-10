import time

import aiohttp

from schemas import (
    DepthSchema,
    PriceSchema,
    PriceVolumeSchema,
    WithdrawFeeSchema,
    WithdrawNetworkFeeSchema,
)
from .ApiTemplate import API, APIException


class BitgetAPI(API):
    API_URL = "https://api.bitget.com/api"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    @staticmethod
    def getApiName():
        return "bitget"

    @staticmethod
    def getSpotWalletUrl():
        return "https://www.bitget.com/balance"

    @staticmethod
    def getSpotUrl(asset0, asset1):
        return f"https://www.bitget.com/spot/{asset0}{asset1}_SPBL?type=spot"

    async def _request(self, method, url_path, params=None, data=None, headers={}):
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                BitgetAPI.API_URL + url_path,
                params=params,
                data=data,
                headers=headers,
                timeout=self.DEFAULT_TIMEOUT,
                verify_ssl=False,
            ) as response:
                if response.status == 200:
                    response_json = await response.json()
                    return response_json["data"]
                elif response.content_type == "application/json":
                    response_json = await response.json()
                    raise APIException("Error: " + response_json)
                else:
                    raise APIException("Error: " + "request error")

    async def getAssetList(self) -> list[list[str]]:
        url_path = "/spot/v1/public/products"
        request = await self._request("GET", url_path)
        return [[asset["baseCoin"], asset["quoteCoin"]] for asset in request]

    async def getAssetPrice(self, asset0, asset1) -> PriceSchema:
        url_path = f"/spot/v1/market/ticker?symbol={asset0}{asset1}_SPBL"
        request = await self._request("GET", url_path)
        return PriceSchema(
            bid=request["buyOne"],
            ask=request["sellOne"],
        )

    async def getAssetsPrices(self) -> dict[str, PriceSchema]:
        url_path = "/spot/v1/market/tickers"
        request = await self._request("GET", url_path)
        out = {}

        for asset in request:
            out[asset["symbol"]] = PriceSchema(
                bid=asset["buyOne"],
                ask=asset["sellOne"],
            )

        return out

    async def get24hVolumes(self) -> dict[str, float]:
        url_path = "/spot/v1/market/tickers"
        request = await self._request("GET", url_path)
        out = {}

        for asset in request:
            out[asset["symbol"]] = asset["baseVol"]

        return out

    async def get24hVolume(self, asset0, asset1) -> float:
        url_path = f"/spot/v1/market/ticker?symbol={asset0}{asset1}_SPBL"
        request = await self._request("GET", url_path)
        return request["baseVol"]

    async def getDepth(self, asset0, asset1) -> DepthSchema:
        url_path = "/spot/v1/market/depth"
        params = {
            "symbol": f"{asset0}{asset1}_SPBL",
            "type": "step0",
            "limit": 10,
        }
        response = await self._request("GET", url_path, params=params)

        ds = DepthSchema(
            asks=[
                PriceVolumeSchema(price=ask[0], volume=ask[1])
                for ask in response["asks"]
            ],
            bids=[
                PriceVolumeSchema(price=bid[0], volume=bid[1])
                for bid in response["bids"]
            ],
            timestamp=int(time.time() * 1000),
        )
        ds.sort()

        return ds

    async def getWithdrawFee(self, asset) -> WithdrawFeeSchema:
        fees = await self.getWithdrawFees()
        return fees[asset]

    async def getWithdrawFees(self) -> dict[str, WithdrawFeeSchema]:
        url_path = "/spot/v1/public/currencies"
        response = await self._request("GET", url_path)

        out = {}
        for asset in response:
            wfs = WithdrawFeeSchema(
                deposit_enabled=True,
                withdraw_enabled=True,
                networks=[
                    WithdrawNetworkFeeSchema(
                        network=network["chain"],
                        withdraw_fee=float(network["withdrawFee"])
                        + float(network["extraWithDrawFee"]),
                        min_withdrawal=float(network["minWithdrawAmount"]),
                        deposit_enabled=True,
                        withdraw_enabled=True,
                    )
                    for network in asset["chains"]
                ],
            )

            wfs.fixBools()
            out[asset["coinName"]] = wfs

        return out
