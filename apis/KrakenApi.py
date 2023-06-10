import datetime
from schemas import DepthSchema, PriceSchema, PriceVolumeSchema, WithdrawFeeSchema
from .ApiTemplate import API, APIException
import aiohttp
import hashlib
import hmac
import time
import urllib.parse
import base64
from .utils import parse_all_pages


class KrakenAPI(API):
    API_URL = "https://api.kraken.com"

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)

    @staticmethod
    def getApiName():
        return "kraken"

    @staticmethod
    def getSpotWalletUrl():
        return "https://pro.kraken.com/app/portfolio/spot"

    @staticmethod
    def getSpotUrl(asset0, asset1):
        return f"https://pro.kraken.com/app/trade/{asset0}-{asset1}"

    @staticmethod
    def _sign(url_path: str, data, api_secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data["nonce"]) + postdata).encode()
        message = url_path.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(api_secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    async def _request(
        self, method, url_path, params={}, data={}, headers={}, toSign=False
    ):
        if toSign:
            data["nonce"] = str(int(time.time() * 1000))
            headers["API-Key"] = (self.api_key,)
            headers["API-Sign"] = self._sign(url_path, data, self.api_secret)

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                KrakenAPI.API_URL + url_path,
                params=params,
                data=data,
                headers=headers,
                timeout=self.DEFAULT_TIMEOUT,
                verify_ssl=False,
            ) as response:
                if response.status == 200:
                    response_json = await response.json()
                    return response_json["result"]
                elif response.content_type == "application/json":
                    response_json = await response.json()
                    raise APIException("Error: " + response_json["error"])
                else:
                    raise APIException("Error: " + "request error")

    async def getAssetList(self) -> list[list[str]]:
        url_path = "/0/public/AssetPairs"
        response = await self._request("GET", url_path)
        keys = []
        for pair in response.values():
            keys.append(pair["wsname"].split("/"))

        return keys

    async def getAssetsPrices(self) -> dict[str, PriceSchema]:
        url_path = "/0/public/Ticker"
        response = await self._request("GET", url_path)

        assets = await self.getAssetList()
        out = {}

        for asset0, asset1 in assets:
            symbol = asset0 + asset1
            assets = asset0 + "/" + asset1
            if symbol not in response:
                continue

            element = response[symbol]

            out[assets] = PriceSchema(
                ask=float(element["a"][0]), bid=float(element["b"][0])
            )

        return out

    async def get24hVolumes(self) -> dict[str, float]:
        url_path = "/0/public/Ticker"
        response = await self._request("GET", url_path)

        assets = await self.getAssetList()
        out = {}

        for asset0, asset1 in assets:
            symbol = asset0 + asset1
            assets = asset0 + "/" + asset1
            if symbol not in response:
                continue

            element = response[symbol]
            out[assets] = float(element["v"][1])

        return out

    async def getDepth(self, asset0, asset1) -> DepthSchema:
        url_path = "/0/public/Depth"

        params = {
            "pair": asset0 + asset1,
            "count": 10,
        }

        response = await self._request("GET", url_path, params=params)
        response = response.popitem()[1]

        ds = DepthSchema(
            asks=[
                PriceVolumeSchema(price=float(i[0]), volume=float(i[1]))
                for i in response["asks"]
            ],
            bids=[
                PriceVolumeSchema(price=float(i[0]), volume=float(i[1]))
                for i in response["bids"]
            ],
            timestamp=int(datetime.datetime.now().timestamp()),
        )
        ds.sort()

        return ds

    async def getWithdrawFees(self) -> dict[str, WithdrawFeeSchema]:
        URL = "https://coinmarketfees.com/exchange/{market}/page/{page}"
        return parse_all_pages(
            url=URL,
            market="kraken",
            pages=10,
        )

    async def getWithdrawFee(self, asset) -> WithdrawFeeSchema:
        fees = await self.getWithdrawFees()
        return fees[asset]
