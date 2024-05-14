<div style="float: left;">
<img src="https://s3.eu-west-1.amazonaws.com/blueshed.info/published/noun-windy-weather-6420809.svg" width="64" title="windy weather">
</div>

# Gust

Gust is a wrapper of [tornado](https://www.tornadoweb.org/en/stable/). It allows for a hello world such as:

```python
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
```

<p align="center">
  <img src="https://s3.eu-west-1.amazonaws.com/blueshed.info/published/noun-windy-weather-6420809.svg" width="350" title="windy weather">
</p>

windy weather image by bsd studio from [Noun Project](https://thenounproject.com/browse/icons/term/windy-weather/)(CC BY 3.0)
