# -*- coding: utf-8 -*-
import json
import logging
import scrapy
import re
from copy import deepcopy
from scrapy.http import Request
from scrapy_redis.spiders import RedisSpider
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError, ConnectError
from twisted.internet.error import TimeoutError, TCPTimedOutError


from KIT.database import redis_

redis = redis_.RedisClient()
logging = logging.getLogger(__name__)


class AmazonSpiderSpider(scrapy.Spider):
    name = 'amazon_spider'
    allowed_domains = ['amazon.com']
    start_urls = ['https://www.amazon.com/gp/profile/amzn1.account.'
                  'AHNWL5WFH2PPOBPXNSRV6AKEA6SQ/ref=cm_cr_dp_d_gw_tr?ie=UTF8']

    def make_requests_from_url(self, url):
        """ This method is deprecated. """
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'cache-control': 'no-cache',
            'cookie': 'session-id=140-6441181-9212353; session-id-time=2082787201l; i18n-prefs=USD; lc-main=zh_CN; sp-cdn="L5Z9:CN"; ubid-main=134-4668107-7231015; x-wl-uid=1yBn1sz7EJQslgUxEhRjh9OdT5XUTRivog6UWLvWrB7s0MlTcw3QtqlX/bA/jNx7jQD/sbzqO15U=; session-token=jkd7UJlk0sUO24Mjz+HeBkv+kjno6bkN+kIC4f43v9e9IOqFJCdEJ3Wvso1FNFdLcyV7JxSlRWC7SaLuUg9PjVty4XPxg0fm4Pkqqn14HNfRdcEZ+7Sx4i7tjESybnQBuuMsnfdAGGruZ9IMxxwBuBEDioE4CsVY1/kQvcW4dbRfJjGuSJZXanFBlNwKExWf; csm-hit=tb:FRM7MJKB99BDKTGRSBHW+b-7GXXM5J2B786PWK49SVS|1574063511763&t:1574063511763&adb:adblk_yes',
            'pragma': 'no-cache',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'
        }
        headers = {
            'Host': 'www.amazon.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers'
        }
        return Request(url, callback=self.parse, dont_filter=True, headers=headers)  # , errback=self.errback_httpbin

    def errback_httpbin(self, failure):
        # log all failures
        log_url = "==========异常============={}".format(failure.request)
        logging.error(log_url)
        # in case you want to do something special for some errors,
        # you may need the failure's type:

        if failure.check(HttpError):
            # these exceptions come from HttpError spider middleware
            # you can get the non-200 response
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)
            redis.lpush(key=AmazonSpiderSpider.name + ':start_urls', json_text=response.url)

        elif failure.check(ConnectError):

            request = failure.request
            self.logger.error('ConnectError on %s', request.url)
            redis.lpush(key=AmazonSpiderSpider.name + ':start_urls', json_text=request.url)

        elif failure.check(DNSLookupError):
            # this is the original request
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)
            redis.lpush(key=AmazonSpiderSpider.name + ':start_urls', json_text=request.url)

        elif failure.check(TimeoutError, TCPTimedOutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)
            redis.lpush(key=AmazonSpiderSpider.name + ':start_urls', json_text=request.url)

    def parse(self, response):
        print(response.url)
        script = response.xpath('//script[not(@type)][1]').extract()[3]
        token = re.findall(r'.*?"token":"(.*?)".*?', script)[0]
        directedId = response.url.split('/')[-2]
        logging.info(directedId)
        return self.next_req(token=token, directedId=directedId, nextPageToken='', Referer=response.url)

    def next_req(self, token, directedId, nextPageToken, Referer):
        '''打包，调用下一页'''
        url = 'https://www.amazon.com/profilewidget/timeline/visitor?' \
              'nextPageToken={nextPageToken}' \
              '&filteredContributionTypes=productreview%2Cglimpse%2Cideas' \
              '&directedId={directedId}' \
              '&token={token}'.format(token=token, directedId=directedId, nextPageToken=nextPageToken)
        logging.info(url)
        headers = {
            'Host': 'www.amazon.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
            'Referer': Referer,
            'TE': 'Trailers'
        }
        print(url)

        yield scrapy.Request(
            url=url,
            dont_filter=True,
            headers=headers,
            callback=self.next_content,
            meta={'token': token, 'directedId': directedId, 'Referer': Referer},
        )

    def next_content(self, response):
        print(response)
        print('==============================')
        data = json.loads(response.text)
        if data['contributions']:  # 获取数据
            for i in data['contributions']:
                # print(i['text'])
                pass

        if data['nextPageToken']:  # 请求下一页
            token = response.meta['token']
            Referer = response.meta['Referer']
            directedId = response.meta['directedId']
            nextPageToken = data['nextPageToken']
            return self.next_req(token=token, directedId=directedId, nextPageToken=nextPageToken, Referer=Referer)


