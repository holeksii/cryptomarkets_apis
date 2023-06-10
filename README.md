# cup_api_template

## How to prepare venv

1. Create virtual environment for python3.10

```bash
python3 -m venv env
```

2. Install requirements

```bash
env/bin/python -m pip install -r requirements.txt
```

3. Run with python

```bash
env/bin/python test.py
```

## how to run test

1. edit test.py and set your api key with your api module

```python
api = BinanceAPI("public", "secret")
```

2. run test.py

```bash
env/bin/python test.py
```

## how to import new api module

1. create new api file in apis directory

```python
# apis/binance.py
from .api_template import API, APIException
from schemas import *


# import needed libraries
import aiohttp
import hashlib
import hmac
import time


class BinanceAPI(API):

    def __init__(self, publicKey, secretKey):
        super().__init__(publicKey, secretKey)
        return

    @staticmethod
    def getApiName():
        return "binance"
```

2. add new api module to apis/__init__.py

```python
# apis/__init__.py
from .binance_api import BinanceAPI
```

3. edit new api file and add all mandatory methods. Note check binance_api.py for example

```python
# apis/binance.py


    # statics
    @staticmethod
    def getApiName() -> str:

    @staticmethod
    def getSpotWalletUrl() -> str:

    @staticmethod
    def getSpotUrl(asset0, asset1) -> str:

    # request
    @staticmethod
    def _sign(params, secretKey) -> str:
    # if you need to sign your request, you can use this method

    async def _request(self, method, url, params=None, data=None, headers={}, toSign=False):
    # if you need to make a request, you can use this method

    # asyncs getters
    async def getAssetList(self) -> list[list[str]]:

    async def getAssetsPrices(self) -> dict[str, PriceSchema]:

    async def get24hVolumes(self) -> dict[str, float]:

    async def getDepth(self, asset0, asset1) -> DepthSchema:

    async def getWithdrawFees(self) -> dict[str, WithdrawFeeSchema]:
```

4. run test.py

```bash
env/bin/python test.py
```


 
