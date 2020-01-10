# -*- coding:utf-8 -*-
import re
import time

import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from requests.adapters import HTTPAdapter


def retry_request_get(url,timeout):
    ask = 'y' # At least try to request for one times.
    while ask == 'y':
        try:
            req = requests.get(url,timeout=timeout)
        except:
            ask = input('Something went wrong with the network. Do you want to retry? (Y/N)').lower()
            while ask != 'y' and ask != 'n':
                ask = input('Please input the correct message. (Y/N)').lower()
        finally:
            if 'req' in locals().keys(): # If req is defined, return req.
                ask = 'n'
    return req


def get_title_list(timeout=(8,10),max_retries=5):

    # Start recording time
    time1 = time.time()

    # Set max retries
    s = requests.Session()
    s.mount('http://',HTTPAdapter(max_retries=max_retries))
    s.mount('https://',HTTPAdapter(max_retries=max_retries))

    # Set main process
    late = 0
    title_list = []
    for x in range(1,3):
        for i in range(0,1000):
            url = "https://www.wenku8.net/novel/"+str(x)+"/"+str(x*1000+i)+"/index.htm"
            data = BeautifulSoup(retry_request_get(url,timeout).content,"html.parser")
            title_data = data.find(id="title") # get the title
            if type(title_data) == type(None):
                late = late + 1 # fail too much and we will break
                if late > 5:
                    break
                continue
            else:
                late = 0 # Reset late
                print(x*1000+i,title_data.string,data.find(id='info').string[3:],sep=" ") # print out the book message
                title_list.append(url+"  "+data.find(id='info').string[3:]+"  "+title_data.string)


    with open("title_list.txt","w") as f:
        f.write("\n".join(title_list))
    time2 = time.time()-time1
    print('Done\nUsing time: %0.2fs' %time2)


def get_single_one(No,timeout=(8,10),max_retries=5):

    # Start recording time
    time1 = time.time()

    # Set max retries
    s = requests.Session()
    s.mount('http://',HTTPAdapter(max_retries=max_retries))
    s.mount('https://',HTTPAdapter(max_retries=max_retries))

    # Set the standard website
    url = "https://www.wenku8.net/novel/1/"+No+"/index.htm"
    data = BeautifulSoup(retry_request_get(url,timeout).content,"html.parser") # analyze the data
    url_link = data.findAll(class_=['vcss','ccss']) # Get the all url link

    # Create a book and add some basic message
    book = epub.EpubBook()
    book.set_identifier('id123456')
    book.set_title(data.find(id='title').string)
    book.set_language('en')
    book.add_author(data.find(id='info').string[3:])
    print(data.find(id='title').string,data.find(id='info').string)

    # Create toc and contents of book
    chapters = []
    toc,x = [],[1,[]]
    for i in range(len(url_link)):
        item = url_link[i]
        if item.get('class') == ['vcss']:
            print(item.string)
            if x != [1,[]]:
                x[1] = tuple(x[1])
                toc.append(tuple(x))
            x = [epub.Section(item.string),[]]
        else:
            ahref = item.find('a')
            if ahref != None:
                filename = re.match('[0-9]+',ahref.get('href')).group()
                chapter = epub.EpubHtml(title=ahref.string,file_name=filename+'.xhtml',lang='hr')
                innerlink = "https://www.wenku8.net/novel/"+str(int(No)//1000)+'/'+No+"/"+ahref.get("href")
                print(filename,item.string)
                text_data = BeautifulSoup(retry_request_get(innerlink,timeout).content,"html.parser")
                if item.string != '插图': # Get basic pages
                    text = '<br/>'+item.string+'<br/>'+str(text_data.find(id='content'))
                    text = text.replace('<br/>\n<br/>','<br/>')
                    chapter.set_content(text)
                    x[1].append(chapter)
                    chapters.append(chapter)
                    book.add_item(chapter)
                else: # Get picture pages
                    imglink = text_data.findAll('img',class_='imagecontent')
                    imglist = []
                    text = '<img src='
                    for i in range(len(imglink)):
                        item = imglink[i]
                        src = item.get('src')
                        imgdata = retry_request_get(src,timeout).content
                        name = re.search('[0-9]+.jpg',src).group()
                        print(name,end=' ')
                        img = epub.EpubItem(file_name=name,media_type='jpg',content=imgdata)
                        imglist.append(img)
                        if i != len(imglink)-1:
                            text = text + name + '> <br/> <img src='
                        else:
                            text = text + name + '>'
                    print('')
                    chapter.set_content(text)
                    x[1].append(chapter)
                    chapters.append(chapter)
                    book.add_item(chapter)
                    for item in imglist:
                        book.add_item(item)
            if i == len(url_link)-1: # When finish all the link, add them to toc.
                x[1] = tuple(x[1])
                if tuple(x) not in toc:
                    toc.append(tuple(x))

    # Add important data such as toc and spine
    book.toc = tuple(toc)
    book.spine = ['nav']+chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Write the books
    epub.write_epub(data.find(id='title').string+'.epub',book)

    # Return the time
    time2 = time.time()-time1
    print('Done\nUsing time: %0.2fs' %time2)


if __name__ == "__main__":
    # get_title_list()
    get_single_one('1546')