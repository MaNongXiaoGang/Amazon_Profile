# coding=utf-8
#!/usr/bin python
'''

Author: lifenggang
        ZsLfg
Python3 环境
Email: 15116211002@163.com
'''

from scrapy import cmdline

# cmdline.execute("scrapy crawl top_bilibili_spider".split())
# cmdline.execute("scrapy crawl urgent_bilibili_spider".split())
cmdline.execute("scrapy crawl amazon_spider".split())


