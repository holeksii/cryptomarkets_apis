from .ApiTemplate import API, APIException

from schemas import (
    DepthSchema,
    PriceSchema,
    PriceVolumeSchema,
    WithdrawFeeSchema,
    WithdrawNetworkFeeSchema,
)

import aiohttp
import hashlib
import hmac
import time


class BinanceAPI(API):
    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)
        return

    @staticmethod
    def getApiName():
        return "binance"

    @staticmethod
    def getSpotWalletUrl():
        return "https://www.binance.com/en/my/wallet/account/main"

    @staticmethod
    def getSpotUrl(asset0, asset1):
        return f"https://www.binance.com/en/trade/{asset0}_{asset1}"

    @staticmethod
    def _sign(params, api_secret):
        codedParams = "&".join([f"{k}={v}" for k, v in params.items()])
        # get signature using private key
        signature = hmac.new(
            api_secret.encode("utf-8"),
            msg=codedParams.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return signature

    async def _request(
        self, method, url, params=None, data=None, headers={}, toSign=False
    ):
        if toSign:
            if params is None:
                params = {}
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            params["signature"] = self._sign(params, self.api_secret)
            headers["X-MBX-APIKEY"] = self.api_key

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
                    raise APIException("Error: " + response_json["msg"])
                else:
                    raise APIException("Error: " + "request error")

    async def getAssetList(self):
        url = "https://api.binance.com/api/v3/exchangeInfo"

        keys = []
        response = await self._request("GET", url)
        if "code" not in response:
            keys = [[i["baseAsset"], i["quoteAsset"]] for i in response["symbols"]]
        return keys

    async def getAssetPrice(self, asset0, asset1) -> PriceSchema:
        raise Exception("Not implemented")

    async def getAssetsPrices(self) -> dict[str, PriceSchema]:
        url = "https://api.binance.com/api/v3/ticker/bookTicker"

        response = await self._request("GET", url)
        bookTickerCache = {i["symbol"]: i for i in response}

        out = {}
        for asset0, asset1 in await self.getAssetList():
            symbol = asset0 + asset1
            asset = asset0 + "/" + asset1
            if symbol in bookTickerCache:
                out[asset] = PriceSchema(
                    bid=float(bookTickerCache[symbol]["bidPrice"]),
                    ask=float(bookTickerCache[symbol]["askPrice"]),
                )

        return out

    async def get24hVolume(self, asset0, asset1) -> float:
        volumes = await self.get24hVolumes()
        return volumes[asset0 + "/" + asset1]

    async def get24hVolumes(self) -> dict[str, float]:
        url = "https://api.binance.com/api/v3/ticker/24hr"

        response = await self._request("GET", url)
        tickerCache = {i["symbol"]: i for i in response}

        out = {}
        for asset0, asset1 in await self.getAssetList():
            symbol = asset0 + asset1
            asset = asset0 + "/" + asset1
            if symbol in tickerCache:
                out[asset] = float(tickerCache[symbol]["quoteVolume"])

        return out

    async def getDepth(self, asset0, asset1) -> DepthSchema:
        url = "https://api.binance.com/api/v3/depth"

        params = {
            "symbol": asset0 + asset1,
            "limit": 10,
        }
        response = await self._request("GET", url, params=params)

        ds = DepthSchema(
            timestamp=response["lastUpdateId"],
            bids=[PriceVolumeSchema(price=i[0], volume=i[1]) for i in response["bids"]],
            asks=[PriceVolumeSchema(price=i[0], volume=i[1]) for i in response["asks"]],
        )
        ds.sort()
        return ds

    async def getWithdrawFee(self, asset) -> WithdrawFeeSchema:
        fees = await self.getWithdrawFees()
        return fees[asset]

    async def getWithdrawFees(self) -> dict[str, WithdrawFeeSchema]:
        url = "https://api.binance.com/sapi/v1/capital/config/getall"
        result = await self._request("GET", url, toSign=True)

        out = {}
        for i in result:
            out[i["coin"]] = WithdrawFeeSchema(
                deposit_enabled=i["depositAllEnable"],
                withdraw_enabled=i["withdrawAllEnable"],
                networks=[
                    WithdrawNetworkFeeSchema(
                        network=i["network"],
                        withdraw_fee=i["withdrawFee"],
                        min_withdrawal=i["withdrawMin"],
                        deposit_enabled=i["depositEnable"],
                        withdraw_enabled=i["withdrawEnable"],
                    )
                    for i in i["networkList"]
                ],
            )

        return out
