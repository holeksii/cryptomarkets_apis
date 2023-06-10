import datetime
import hmac
import sys
import uuid

from schemas import (
    DepthSchema,
    PriceSchema,
    PriceVolumeSchema,
    WithdrawFeeSchema,
    WithdrawNetworkFeeSchema,
)

from .ApiTemplate import API, APIException
import aiohttp
import hashlib
import time


class BitstampAPI(API):
    API_URL = "https://www.bitstamp.net/api/v2"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    @staticmethod
    def getApiName():
        return "bitstamp"

    @staticmethod
    def getSpotWalletUrl():
        return "https://www.bitstamp.net/account/balance/"

    @staticmethod
    def getSpotUrl(asset0, asset1):
        return f"https://www.bitstamp.net/markets/{asset0}/{asset1}"

    @staticmethod
    def _sign(payload, api_key, api_secret) -> str:
        timestamp = str(int(round(time.time() * 1000)))
        nonce = str(uuid.uuid4())
        content_type = "application/x-www-form-urlencoded"
        payload = {"offset": "1"}

        if sys.version_info.major >= 3:
            from urllib.parse import urlencode
        else:
            from urllib import urlencode

        payload_string = urlencode(payload)

        message = (
            "BITSTAMP "
            + api_key
            + "POST"
            + "www.bitstamp.net"
            + "/api/v2/user_transactions/"
            + ""
            + content_type
            + nonce
            + timestamp
            + "v2"
            + payload_string
        )
        message = message.encode("utf-8")
        signature = hmac.new(
            api_secret, msg=message, digestmod=hashlib.sha256
        ).hexdigest()
        return signature

    async def _request(
        self, method, url_path, params=None, data=None, headers={}, toSign=False
    ):
        if toSign:
            signature = self._sign(params, self.api_key, self.api_secret)
            headers["X-Auth"] = "BITSTAMP " + self.api_key
            headers["X-Auth-Signature"] = signature
            headers["X-Auth-Nonce"] = str(uuid.uuid4())
            headers["X-Auth-Timestamp"] = str(int(round(time.time() * 1000)))
            headers["X-Auth-Version"] = "v2"
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                BitstampAPI.API_URL + url_path,
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
        url_path = "/trading-pairs-info/"
        response = await self._request("GET", url_path)
        asset_list = []

        for asset in response:
            asset_list.append(
                [asset["name"].split("/")[0], asset["name"].split("/")[1]]
            )

        return asset_list

    async def getAssetPrice(self, asset0, asset1) -> PriceSchema:
        url_path = "/ticker/" + asset0.lower() + asset1.lower()
        response = await self._request("GET", url_path)
        return PriceSchema(bid=float(response["bid"]), ask=float(response["ask"]))

    async def getAssetsPrices(self) -> dict[str, PriceSchema]:
        url_path = "/ticker/"
        response = await self._request("GET", url_path)
        out = {}

        for asset in response:
            out[asset["pair"]] = PriceSchema(
                bid=float(asset["bid"]), ask=float(asset["ask"])
            )

        return out

    async def get24hVolume(self, asset0, asset1) -> float:
        url_path = "/ticker/" + asset0.lower() + asset1.lower()
        response = await self._request("GET", url_path)
        return float(response["volume"])

    async def get24hVolumes(self) -> dict[str, float]:
        url_path = "/ticker/"
        response = await self._request("GET", url_path)
        out = {}

        for asset in response:
            out[asset["pair"]] = float(asset["volume"])

        return out

    async def getDepth(self, asset0, asset1) -> DepthSchema:
        url_path = "/order_book/" + asset0.lower() + asset1.lower()
        response = await self._request("GET", url_path)

        limit = 10

        ds = DepthSchema(
            asks=[
                PriceVolumeSchema(price=float(i[0]), volume=float(i[1]))
                for i in response["asks"][:limit]
            ],
            bids=[
                PriceVolumeSchema(price=float(i[0]), volume=float(i[1]))
                for i in response["bids"][:limit]
            ],
            timestamp=int(datetime.datetime.now().timestamp()),
        )
        ds.sort()

        return ds

    async def getWithdrawFees(self) -> dict[str, WithdrawFeeSchema]:
        url_path = "/fees/withdrawal/"
        response = await self._request("POST", url_path, toSign=True)
        out = {}

        for asset in response:
            wfs = WithdrawFeeSchema(
                deposit_enabled=True,
                withdraw_enabled=True,
                networks=[
                    WithdrawNetworkFeeSchema(
                        network="",
                        withdraw_fee=float(asset["fee"]),
                        min_withdrawal=0.0,
                        deposit_enabled=True,
                        withdraw_enabled=True,
                    )
                ],
            )
            wfs.fixBools()
            out[asset["currency"]] = wfs

        return out

    async def getWithdrawFee(self, asset) -> WithdrawFeeSchema:
        url_path = "/fees/withdrawal/" + asset.lower()
        response = await self._request("POST", url_path, toSign=True)

        wfs = WithdrawFeeSchema(
            deposit_enabled=True,
            withdraw_enabled=True,
            networks=[
                WithdrawNetworkFeeSchema(
                    network="",
                    withdraw_fee=float(response["fee"]),
                    min_withdrawal=0.0,
                    deposit_enabled=True,
                    withdraw_enabled=True,
                )
            ],
        )
        wfs.fixBools()

        return wfs
