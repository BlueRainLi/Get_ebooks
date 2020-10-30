# -*- coding:utf-8 -*-
###########################
# File Name: get_ebooks_from_wenku8.py
# Author: BlueRainLi
# Mail: 118010159@link.cuhk.edu.cn
###########################

import os
import re
import threading
import time
from functools import reduce

import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from requests.adapters import HTTPAdapter


def retry_request_get(url, timeout, always=False):
    req = None
    ask = 'y'  # At least try to request for one times.
    while ask == 'y' or always == True:
        try:
            req = requests.get(url, timeout=timeout)
        except:
            if not always:
                ask = input('Something went wrong with the network. Do you want to retry? (Y/N) ').lower()
            while ask != 'y' and ask != 'n':
                ask = input('Please input the correct message. (Y/N)').lower()
        finally:
            if 'req' in locals().keys():  # If req is defined, return req.
                ask = 'n'
                always = False
    return req


def find_all(c, s: list):
    """

    :rtype: list
    """
    if c not in s:
        return False
    return [x for x in range(len(s)) if c == s[x]]


def get_picture(index: int, src: str, timeout, imglist: list):
    try:
        req = requests.get(src, timeout=timeout)
    except Exception as e:
        print(src, e)
    else:
        imgdata = req.content
        match = re.search('[0-9]+.(jpg|png)', src)
        name = match.group()
        img = epub.EpubItem(file_name=name, media_type=match.group(1), content=imgdata)
        imglist[index] = img


def checking_valid(group: list):
    for item in group:
        if isinstance(item,list):
            return False
        elif item[0].get("class") != ["vcss"]:
            return False
    return True


def make_dir(name: str):
    name = name.strip()  # Remove white space
    name = name.rstrip("\\")  # Remove \\
    exist = os.path.exists(name)
    if not exist:
        os.makedirs(name)
        print("Folder " + name + " created.")
        return True
    else:
        print("Folder " + name + " existed.")
        return False


def addList(x: list, y: list):
    return x + y


def checking_group_valid(group: list):
    for item in group:
        if type(item) != type([]):
            return False
        elif item[0].get("class") != ["vcss"]:
            return False
        else:
            for i in range(1, len(item)):
                if item[i].get("class") != ["ccss"]:
                    return False
    return True


def book_init(name: str, author: str, title=None, series=None, number=None):
    book = epub.EpubBook()
    book.set_identifier('id123456')
    if title == None:
        book.set_title(name)
    else:
        book.set_title(name + ' ' + title)
    book.set_language('zh')
    book.add_author(author)
    if series != None:
        book.add_metadata("DC", "series", series)
    if number != None:
        book.add_metadata("DC", "series-index", number)
    return book


def get_title_list(timeout=(1, 3), max_retries=5):
    # Start recording time
    time1 = time.time()

    # Set max retries
    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=max_retries))
    s.mount('https://', HTTPAdapter(max_retries=max_retries))

    # Set main process
    late = 0
    available = True
    title_list = []
    for x in range(0, 3):
        for i in range(0, 1000):
            url = "https://www.wenku8.net/novel/" + str(x) + "/" + str(x * 1000 + i) + "/index.htm"
            data = BeautifulSoup(retry_request_get(url, timeout).content, "html.parser")
            title_data = data.find(id="title")  # get the title
            if type(title_data) == type(None):
                late = late + 1  # fail too much and we will break
                if late > 5:
                    break
                continue
            else:
                late = 0  # Reset late
                link = url.replace("index.htm", data.find(class_="ccss").contents[0].get("href"))
                data2 = BeautifulSoup(retry_request_get(link, timeout).content, "html.parser")
                if '因版权问题，文库不再提供该小说的阅读！' in data2.find(id="content").contents:
                    available = False
                else:
                    available = True

                if available == True:  # print out the book message
                    print(x * 1000 + i, title_data.string, data.find(id='info').string[3:], sep=" ")
                    title_list.append(url + "  " + data.find(id='info').string[3:] + "  " + title_data.string)
                else:
                    print(x * 1000 + i, title_data.string, data.find(id='info').string[3:], "Not Available", sep=" ")
                    title_list.append(
                        url + "  " + data.find(id='info').string[3:] + "  " + title_data.string + " Not available")

    # Write the data into txt file
    with open("./title_list.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(title_list))
    time2 = time.time() - time1
    print('Done\nUsing time: %0.2fs' % time2)


def get_ebooks(No: str, booknumber=1, timeout=(1, 3), max_retries=5, always=False):
    """
    A little function to get ebook(s) from www.wenku8.net.
    
    Args:
    No: A string of number representing the book. Example: "1","1999"
    booknumber: A int to choose to create only one file(1) or multiple files(2).
    timeout: A tuple with two values which refer to the waiting time of sending requests and waiting responses
    max_retries: A int to set the times of retring requests the url.
    always: A Boolean to depend whether keep retring to request or not.
    """
    # Start recording time
    time1 = time.time()

    # Set max retries
    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=max_retries))
    s.mount('https://', HTTPAdapter(max_retries=max_retries))

    # Set the standard website and get basic data
    url = "https://www.wenku8.net/novel/" + str(int(No) // 1000) + '/' + No + "/index.htm"
    res = requests.get(url)
    print("Requests url:", url)
    print("Requests status:", res.status_code)
    data = BeautifulSoup(res.content, "html.parser")
    chapter_list = data.findAll(class_="vcss")
    url_link = data.findAll(class_=["vcss", "ccss"])
    group = []
    part = []
    bookname = data.find(id='title').string
    author = data.find(id='info').string[3:]
    print(bookname, author)

    # Create all the data of sub-books
    print("Volume(s):")
    for i in range(len(url_link)):
        item = url_link[i]
        if item.get("class") == ["vcss"]:
            if item != url_link[0]:
                group.append(part)
            part = [item]
            print(item.string)
        elif i == len(url_link) - 1:
            part.append(item)
            group.append(part)
        else:
            part.append(item)
    print("Volume(s) status:", checking_group_valid(group))
    print("Volume(s) length:", len(group))

    # Start collecting the data
    toc = [None] * (len(group))
    bookadd = [None] * (len(group))
    for j in range(len(group)):
        item = group[j]
        print(j + 1, item[0].string)
        toc[j:int] = [epub.Section(item[0].string), []]
        chapters = []
        imglist = None
        for i in range(1, len(item)):
            ahref = item[i].find('a')
            if ahref != None:
                filename = re.match('[0-9]+', ahref.get('href')).group()
                chapter = epub.EpubHtml(title=ahref.string, file_name=filename + '.xhtml', lang='hr')
                innerlink = "https://www.wenku8.net/novel/" + str(int(No) // 1000) + '/' + No + '/' + ahref.get('href')
                print("  %5s" % filename, item[i].string)
                text_data = BeautifulSoup(retry_request_get(innerlink, timeout, always=always).content, "html.parser")
                alink = text_data.findAll("a")
                a_truelink = []
                for a_link in alink:
                    if a_link.find('img') == None:
                        continue
                    else:
                        new_tag = text_data.new_tag('img')
                        new_tag['src'] = a_link.get('href')
                        new_tag['class'] = "imagecontent"
                        a_link.replace_with(new_tag)
                        a_truelink.append(a_link)
                # Get picture pages
                imglink = text_data.findAll('img', class_='imagecontent')
                lens = len(imglink)
                if lens != 0: print("Number of picture: %d" % lens)
                imglist = [None] * lens
                while find_all(None, imglist):
                    Nonelist = find_all(None, imglist)
                    pendinglist = []
                    ask = 'y'
                    if len(Nonelist) != lens:
                        if always == False:
                            ask = input('  %d picture(s) failed. Do you want to retry? (Y/N) ' % len(Nonelist)).lower()
                        else:
                            print('  %d picture(s) failed. Retring.' % len(Nonelist))
                        if ask != 'y':
                            break
                    for ix in Nonelist:
                        k = imglink[ix]
                        src = k.get('src')
                        pendinglist.append(threading.Thread(target=get_picture, args=(ix, src, timeout, imglist)))
                    for x1 in pendinglist:
                        x1.start()
                    for x2 in pendinglist:
                        x2.join()

                for ik in range(len(imglink)):
                    name = imglist[ik].get_name()
                    print(name)
                    imglink[ik]['src'] = name
                    print(imglink[ik])

                # Get basic pages
                text = '<br/>' + item[i].string + '<br/>' + str(text_data.find(id='content'))
                text = text.replace('<br/>\n<br/>', '<br/>')

                chapter.set_content(text)
                chapters.append(chapter)
                toc[j][1].append(chapter)
                chapters = chapters + imglist
        bookadd[j] = chapters

    if booknumber == 2:
        make_dir(bookname)
        for i in range(len(chapter_list)):
            book = book_init(bookname, author, title=chapter_list[i].string)
            book.toc = tuple(toc[i][1])
            book.spine = ['nav'] + bookadd[i]
            for item in bookadd[i]:
                book.add_item(item)
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            epub.write_epub(bookname + "/" + bookname + " " + chapter_list[i].string + ".epub", book)
    else:
        spine = reduce(addList, bookadd)
        book = book_init(bookname, author)
        book.toc = tuple(toc)
        book.spine = ['nav'] + spine
        for item in spine:
            book.add_item(item)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub.write_epub(bookname + ".epub", book)

    time2 = time.time() - time1
    print('Done.\nUsing time: %0.1f min' % (time2 / 60))


if __name__ == "__main__":
    get_ebooks("1999", booknumber=2)
