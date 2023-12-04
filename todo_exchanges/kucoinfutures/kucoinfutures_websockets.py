import asyncio
from kucoin_futures.client import WsToken
from kucoin_futures.ws_client import KucoinFuturesWsClient
from typing import Dict, Any, Coroutine, Tuple
#params = {'KEY': '64210332ecb900000172f782', 'SECRET': 'cffddbc9-cbe7-4d31-b430-fb81726a1139', 'FUTURES': "1"}

# Replace with your API keys
API_KEY = "64233d58fc1e89000146b03d"
SECRET_KEY = "d8ff9a68-3647-416c-adf5-dfec000876b9"

# KuCoin Futures API WebSocket endpoint
API_BASE_URL = "wss://api-futures.kucoin.com/endpoint"
API_PASS = "RayRaulSuck"




async def main():
    async def deal_msg(msg):
        if msg['topic'] == '/contractMarket/level2:XBTUSDM':
            print(f'Get XBTUSDM Ticker:{msg["data"]}')
        elif msg['topic'] == '/contractMarket/level3:XBTUSDTM':
            print(f'Get XBTUSDTM level3:{msg["data"]}')

    # is public
    # client = WsToken()
    # is private
    client = WsToken(key=API_KEY, secret=SECRET_KEY, passphrase=API_PASS, is_sandbox=False, url='')
    # is sandbox
    # client = WsToken(is_sandbox=True)
    ws_client = await KucoinFuturesWsClient.create(loop, client, deal_msg, private=False)
    await ws_client.subscribe('/contractMarket/level2:XBTUSDM')
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())