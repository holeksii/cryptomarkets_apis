import aiohttp

from schemas import (
    DepthSchema,
    PriceSchema,
    WithdrawFeeSchema,
    WithdrawNetworkFeeSchema,
)


class APIException(BaseException):
    def __init__(self, message=""):
        self.message = message
        return

    def __str__(self):
        return self.message


class API:
    DEFAULT_TIMEOUT: int = 10
    OPERATIONAL: bool = True

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    # statics
    @staticmethod
    def getApiName() -> str:
        raise NotImplementedError()
        return "template"

    @staticmethod
    def getSpotWalletUrl() -> str:
        raise NotImplementedError()
        return "https://somesite/wallet/"

    @staticmethod
    def getSpotUrl(asset0, asset1) -> str:
        raise NotImplementedError()
        return "https://somesite/spot/{}/{}".format(asset0, asset1)

    @staticmethod
    def _sign(params, api_secret) -> str:
        raise NotImplementedError()
        return ""

    async def _request(
        self, method, url, params=None, data=None, headers={}, toSign=False
    ):
        if toSign:
            headers["signature"] = self._sign(params, self.api_secret)

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
                else:
                    raise APIException("Error: " + "request error")

    async def getAssetList(self) -> list[list[str]]:
        raise NotImplementedError()
        return [["BTC", "USDT"], ["ETH", "USDT"]]

    async def getAssetPrice(self, asset0, asset1) -> PriceSchema:
        raise NotImplementedError()
        # best bid/ask
        return PriceSchema(bid=0, ask=0)

    async def getAssetsPrices(self) -> dict[str, PriceSchema]:
        raise NotImplementedError()
        # best bid/ask of asset0/asset1
        return {
            "BTC/USDT": PriceSchema(bid=0, ask=0),
        }

    async def get24hVolume(self, asset0, asset1) -> float:
        raise NotImplementedError()
        # 24h volume in asset1
        return 0

    async def get24hVolumes(self) -> dict[str, float]:
        raise NotImplementedError()
        # 24h volume in asset1
        return {
            "BTC/USDT": 0,
        }

    async def getDepth(self, asset0, asset1) -> DepthSchema:
        raise NotImplementedError()
        ds = DepthSchema(asks=[], bids=[], timestamp=0)
        ds.sort()
        return ds

    async def getWithdrawFee(self, asset) -> WithdrawFeeSchema:
        raise NotImplementedError()
        wf = WithdrawFeeSchema(
            deposit_enabled=False,
            withdraw_enabled=False,
            networks=[
                WithdrawNetworkFeeSchema(  # noqa: F821
                    network="",
                    withdraw_fee=0,
                    min_withdrawal=0,
                    deposit_enabled=False,
                    withdraw_enabled=False,
                )
            ],
        )
        wf.fixBools()  # validates depositEnabled and withdrawEnabled for some exchanges
        return wf

    async def getWithdrawFees(self) -> dict[str, WithdrawFeeSchema]:
        raise NotImplementedError()
        return {
            "BTC": WithdrawFeeSchema(
                deposit_enabled=False,
                withdraw_enabled=False,
                networks=[
                    WithdrawNetworkFeeSchema(
                        network="",
                        withdraw_fee=0,
                        min_withdrawal=0,
                        deposit_enabled=False,
                        withdraw_enabled=False,
                    )
                ],
            )
        }
