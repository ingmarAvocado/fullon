"""
Dictionary with all public methos available.
"""


def get_components():
    """ description """
    components = {
                  'bots': ['prev', 'next', 'start', 'stop', 'live', 'add', 'test', 'edit', 'exit', 'delete', "dry_reset"],
                  'exchange': ['list'],
                  'services': ['accounts', 'tickers', 'ohlcv', 'bots', 'services', 'full'],
                  'strategies': ['add', 'delete'],
                  'symbols': ['list', 'add', 'delete', 'list_exchange'],
                  'tickers': ['list'],
                  'top': [],
                  'help': [],
                  'users': ['list', 'details'],
                  }
    return components
