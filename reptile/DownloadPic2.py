import os
import lxml.etree
import urllib.request as re
from lxml import etree

pic_dir = 'E:\\MM'
headurl = 'https://www.zbjuran.com'
myurl = 'https://www.zbjuran.com/mei/qingchun/'

if not os.path.exists(pic_dir):
    os.makedirs(pic_dir)

def DownloadPic(url):
    PicName = pic_dir + '\\' + url.split('/')[-1]
    try:
        f = open(PicName, 'wb')
        f.write(re.urlopen(url).read())
        f.close()
    except Exception as e:
        print(PicName+" error")

def FindPic(url):
    request = re.Request(url)
    text = re.urlopen(request).read()
    htmlEmt = etree.HTML(text)
    result = htmlEmt.xpath('//center//img//@src')
    suburl = headurl + result[0]
    DownloadPic(suburl)

def FindPage(url):
    FindPic(url)
    PageUrl = '/'.join(url.split('/')[0:-1])
    print(PageUrl)
    request = re.Request(url)
    text = re.urlopen(request).read()
    htmlEmt = etree.HTML(text)
    result = htmlEmt.xpath('//*[@class="page"]//a//@href')
    for page in result[2:-1]:
        print(page)
        cururl = PageUrl + '/' + page
        print(cururl)
        FindPic(cururl)

def NextPage(url):
    request = re.Request(url)
    text = re.urlopen(request).read()
    htmlEmt = etree.HTML(text)
    result = htmlEmt.xpath('//b//*[@target="_blank"]//@href')
    print(result)
    for item in result:
        iturl = headurl + item
        FindPage(iturl)
    result = htmlEmt.xpath('//*[@class="pages"]//a//@href')
    print(result[-2])
    if result[-2] != 'javascript:;':
        nexturl =  myurl + '/' + result[-2]
        print('翻页:'+ nexturl)
        NextPage(nexturl)

NextPage(myurl)
##myurl = 'https://www.zbjuran.com/mei/qingchun/list_14_39.html'
##request = re.Request(myurl)
##text = re.urlopen(request).read()
##htmlEmt = etree.HTML(text)
##result = htmlEmt.xpath('//*[@class="pages"]//a//@href')
##print(result[-2])

