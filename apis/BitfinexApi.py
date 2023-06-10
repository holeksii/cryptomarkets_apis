import base64
import datetime
import json
from .ApiTemplate import API, APIException

from schemas import (
    DepthSchema,
    PriceSchema,
    PriceVolumeSchema,
    WithdrawFeeSchema,
)

import aiohttp
import hashlib
import time
from .utils import parse_all_pages


class BitfinexAPI(API):
    API_PUB_URL = "https://api-pub.bitfinex.com/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    @classmethod
    def getSymbol(cls, asset0, asset1):
        if len(asset0) > 3 or len(asset1) > 3:
            return f"t{asset0}:{asset1}"
        else:
            return f"t{asset0}{asset1}"

    @classmethod
    def getAssets(cls, symbol):
        if len(symbol) == 6:
            return [symbol[:3], symbol[3:]]
        elif len(symbol) > 6 and ":" in symbol:
            return symbol.split(":")

    @staticmethod
    def getApiName():
        return "bitfinex"

    @staticmethod
    def getSpotWalletUrl():
        return "https://www.bitfinex.com/balances"

    @staticmethod
    def getSpotUrl(asset0, asset1):
        return f"https://trading.bitfinex.com/t/{asset0}:{asset1}"

    @staticmethod
    def _sign(payload, params, api_secret) -> str:
        signature = hashlib.sha384(api_secret).update(payload).hexdigest()
        return signature

    async def _request(
        self, method, url, params=None, data=None, headers={}, toSign=False
    ):
        if toSign:
            nonce = str(int(time.time() * 1000))
            payloadObject = {
                "request": url.replace(BitfinexAPI.API_PUB_URL, ""),
                "nonce": nonce,
                "options": {},
            }

            payload_json = json.dumps(payloadObject)
            payload = str(base64.b64encode(payload_json))
            signature = self._sign(payload, params, self.api_secret)
            headers["X-BFX-APIKEY"] = self.api_key
            headers["X-BFX-PAYLOAD"] = payload
            headers["X-BFX-SIGNATURE"] = signature

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                params=params,
                data=data,
                headers=headers,
                timeout=self.DEFAULT_TIMEOUT,
                verify_ssl=False,
            ) as response:
                if response.status == 200:
                    response_json = await response.json()
                    return response_json
                elif response.content_type == "application/json":
                    response_json = await response.json()
                    raise APIException("Error: " + response_json)
                else:
                    raise APIException("Error: " + "request error")

    async def getAssetList(self) -> list[list[str]]:
        url = BitfinexAPI.API_PUB_URL + "/conf/pub:list:pair:exchange"
        response = await self._request("GET", url)
        out = []

        for asset in response[0]:
            if ":" in asset:
                out.append(asset.split(":"))
            else:
                out.append([asset[:3], asset[3:]])

        return out

    async def getAssetPrice(self, asset0, asset1) -> PriceSchema:
        url = BitfinexAPI.API_PUB_URL + "/ticker/" + self.getSymbol(asset0, asset1)
        response = await self._request("GET", url)
        ps = PriceSchema(ask=response[2], bid=response[0])
        return ps

    async def getAssetsPrices(self) -> dict[str, PriceSchema]:
        url = BitfinexAPI.API_PUB_URL + "/tickers"
        params = {"symbols": "ALL"}
        response = await self._request("GET", url, params)
        out = {}

        for asset in response:
            if asset[0][0] == "t":
                assets = self.getAssets(asset[0][1:])
                out[assets[0] + "/" + assets[1]] = PriceSchema(
                    ask=asset[3], bid=asset[1]
                )

        return out

    async def get24hVolume(self, asset0, asset1) -> float:
        url = BitfinexAPI.API_PUB_URL + "/ticker/" + self.getSymbol(asset0, asset1)
        response = await self._request("GET", url)
        return response[7]

    async def get24hVolumes(self) -> dict[str, float]:
        url = BitfinexAPI.API_PUB_URL + "/tickers"
        params = {"symbols": "ALL"}
        response = await self._request("GET", url, params)
        out = {}

        for asset in response:
            if asset[0][0] == "t":
                assets = self.getAssets(asset[0][1:])
                out[assets[0] + "/" + assets[1]] = asset[8]

        return out

    async def getDepth(self, asset0, asset1) -> DepthSchema:
        url = BitfinexAPI.API_PUB_URL + f"/book/t{asset0}{asset1}/P0"
        params = {"len": 25}
        limit = 10
        response = await self._request("GET", url, params)
        bids, asks = [], []

        for i in range(limit):
            bids.append(PriceVolumeSchema(price=response[i][0], volume=response[i][2]))
            asks.append(
                PriceVolumeSchema(
                    price=response[i + 25][0], volume=-response[i + 25][2]
                )
            )

        ds = DepthSchema(
            bids=bids, asks=asks, timestamp=int(datetime.datetime.now().timestamp())
        )
        ds.sort()
        return ds

    async def getWithdrawFees(self) -> dict[str, WithdrawFeeSchema]:
        URL = "https://coinmarketfees.com/exchange/{market}/page/{page}"
        return parse_all_pages(
            url=URL,
            market="bitfinex",
            pages=10,
        )

    async def getWithdrawFee(self, asset) -> WithdrawFeeSchema:
        fees = await self.getWithdrawFees()
        return fees[asset]
