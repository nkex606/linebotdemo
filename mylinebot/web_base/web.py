from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse


class Web:
    def __init__(self, site, url, content_tag, content_clazz, img_tag, img_class):
        self.site = site
        self.url = url
        self.content_tag = content_tag
        self.content_clazz = content_clazz
        self.img_tag = img_tag
        self.img_class = img_class

    @staticmethod
    def _html_formater(text, tag, clazz):
        return BeautifulSoup(text, 'html.parser').find_all(tag, class_=clazz)

    @staticmethod
    def get_content(url, tag_name, tag_clazz):
        r = requests.get(url)
        return Web._html_formater(r.text, tag_name, tag_clazz)

    def get_content_images(self):
        img = set()
        parsed_uri = urlparse(self.url)
        domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
        rs = Web.get_content(self.url, self.content_tag, self.content_clazz)
        for r in rs:
            if r.a:  # avoid post has been delete
                tag_attr = 'href' if 'ptt' in domain else 'src'
                rs2 = Web.get_content(domain + r.a['href'], self.img_tag, self.img_class)
                for r2 in rs2:
                    if 'jpg' in r2[tag_attr] or 'jpeg' in r2[tag_attr]:
                        img.add(r2[tag_attr])
        return img
