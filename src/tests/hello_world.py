"""Simple hello, world"""

from blueshed.gust import Gust, web


@web.get('/(.*)')
def get(request):
    """just a get"""
    return 'hello, world'


def main():
    """seperate construction from run"""
    Gust().run()


if __name__ == '__main__':
    main()
