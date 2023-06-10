from pydantic import BaseModel


class PriceSchema(BaseModel):
    bid: float
    ask: float

    def __str__(self):
        return "bid: {}, ask: {}".format(self.bid, self.ask)


class PriceVolumeSchema(BaseModel):
    price: float
    volume: float

    def __str__(self):
        return "price: {}, volume: {}".format(self.price, self.volume)


class DepthSchema(BaseModel):
    asks: list[PriceVolumeSchema]
    bids: list[PriceVolumeSchema]
    timestamp: int

    def sort(self):
        self.asks.sort(key=lambda x: x.price)
        self.bids.sort(key=lambda x: x.price, reverse=True)

    def __str__(self):
        return "asks: {}, bids: {}, timestamp: {}".format(
            self.asks, self.bids, self.timestamp
        )


class WithdrawNetworkFeeSchema(BaseModel):
    network: str
    withdraw_fee: float
    min_withdrawal: float
    deposit_enabled: bool
    withdraw_enabled: bool


class WithdrawFeeSchema(BaseModel):
    deposit_enabled: bool
    withdraw_enabled: bool
    networks: list[WithdrawNetworkFeeSchema]

    def fixBools(self):
        self.withdraw_enabled = False
        self.deposit_enabled = False

        for i in self.networks:
            if i.withdraw_enabled:
                self.withdraw_enabled = True
            if i.deposit_enabled:
                self.deposit_enabled = True
