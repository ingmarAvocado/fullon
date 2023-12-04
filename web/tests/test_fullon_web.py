import sys 
from  run  import fullon_web

def test_toytest():
    test = fullon_web.FullonWebServer()
    assert test.toytest(1) == 2

def test_btcprice():
    test = fullon_web.FullonWebServer()
    r =  test.btcprice()
    assert ("font" in r) == True

