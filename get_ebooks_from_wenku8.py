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
from typing import List, cast


def retry_request_get(url, timeout, always=False):
    req = None
    ask = 'y'  # At least try to request for one times.
    while req is None and (ask == 'y' or always):
        try:
            req = requests.get(url, timeout=timeout)
            req.raise_for_status()
        except requests.RequestException:
            if not always:
                ask = input('Something went wrong with the network. Do you want to retry? (Y/N) ').lower()
            while ask != 'y' and ask != 'n':
                ask = input('Please input the correct message. (Y/N)').lower()
    return req


def find_all(c, s: list) -> List[int]:
    """

    :rtype: List[int]
    """
    if c not in s:
        return []
    return [x for x in range(len(s)) if c == s[x]]


def get_picture(index: int, src: str, timeout, img_list: list):
    try:
        req = requests.get(src, timeout=timeout)
    except Exception as e:
        print(src, e)
    else:
        img_data = req.content
        match = re.search('[0-9]+.(jpg|png)', src)
        name = match.group()
        img = epub.EpubImage()
        img.file_name = name
        img.media_type = "image/" + match.group(1)
        img.content = img_data
        img_list[index] = img


def checking_valid(group: list):
    for item in group:
        if isinstance(item, list):
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


def add_list(x: list, y: list):
    return x + y


def checking_group_valid(group: list):
    for item in group:
        if isinstance(item, list):
            return False
        elif item[0].get("class") != ["vcss"]:
            return False
        else:
            for i in range(1, len(item)):
                if item[i].get("class") != ["ccss"]:
                    return False
    return True


def book_init(name: str, author: str, title=None, series=None, number=None, identifier='BlueRain77'):
    book = epub.EpubBook()
    book.set_identifier(identifier)
    if title is None:
        book.set_title(name)
    else:
        book.set_title(name + ' ' + title)
    book.set_language('zh')
    book.add_author(author)
    if series is not None:
        book.add_metadata("DC", "series", series)
    if number is not None:
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
    title_list = []
    for x in range(0, 3):
        for i in range(0, 1000):
            url = "https://www.wenku8.net/novel/" + str(x) + "/" + str(x * 1000 + i) + "/index.htm"
            data = BeautifulSoup(retry_request_get(url, timeout).content, "html.parser")
            title_data = data.find(id="title")  # get the title
            if title_data is None:
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

                if available:  # print out the book message
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


def get_ebooks(number: str, book_number=1, timeout=(1, 3), max_retries=5, always=False):
    """
    A little function to get ebook(s) from www.wenku8.net.
    
    Args:
    number: A string of number representing the book. Example: "1","1999"
    book_number: A int to choose to create only one file(1) or multiple files(2).
    timeout: A tuple with two values which refer to the waiting time of sending requests and waiting responses
    max_retries: A int to set the times of retrying requests the url.
    always: A Boolean to depend whether keep retrying to request or not.
    """
    # Start recording time
    time1 = time.time()

    # Set max retries
    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=max_retries))
    s.mount('https://', HTTPAdapter(max_retries=max_retries))

    # Set the standard website and get basic data
    url = "https://www.wenku8.net/novel/" + str(int(number) // 1000) + '/' + number + "/index.htm"
    res = requests.get(url)
    print("Requests url:", url)
    print("Requests status:", res.status_code)
    data = BeautifulSoup(res.content, "html.parser")
    chapter_list = data.findAll(class_="vcss")
    url_link = data.findAll(class_=["vcss", "ccss"])
    group = []
    part = []
    book_name = data.find(id='title').string
    author = data.find(id='info').string[3:]
    print(book_name, author)

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
    toc = [0] * (len(group))
    book_add = [None] * (len(group))
    total_image_list = [None] * (len(group))

    for j in range(len(group)):
        item = group[j]
        print(j + 1, item[0].string)
        toc[j] = [epub.Section(item[0].string), []]
        chapters = []
        for i in range(1, len(item)):
            a_href = item[i].find('a')
            if a_href is not None:
                filename = re.match('[0-9]+', a_href.get('href')).group()
                chapter = epub.EpubHtml(title=a_href.string, file_name=filename + '.xhtml', lang='hr')
                inner_link = "https://www.wenku8.net/novel/" + str(int(number) // 1000)
                inner_link += '/' + number + '/' + a_href.get('href')
                print("  %5s" % filename, item[i].string)
                text_data = BeautifulSoup(retry_request_get(inner_link, timeout, always=always).content, "html.parser")
                a_links = text_data.findAll("a")
                a_true_links = []
                for a_link in a_links:
                    if a_link.find('img') is None:
                        continue
                    else:
                        new_tag = text_data.new_tag('img')
                        new_tag['src'] = a_link.get('href')
                        new_tag['class'] = "imagecontent"
                        a_link.replace_with(new_tag)
                        a_true_links.append(a_link)
                # Get picture pages
                img_links = text_data.findAll('img', class_='imagecontent')
                lens = len(img_links)
                if lens != 0:
                    print("Number of picture: %d" % lens)
                img_lists = [None] * lens
                while find_all(None, img_lists):
                    none_list = find_all(None, img_lists)
                    pending_list = []
                    ask = 'y'
                    if len(none_list) != lens:
                        if not always:
                            ask = input('  %d picture(s) failed. Do you want to retry? (Y/N) ' % len(none_list)).lower()
                        else:
                            print('  %d picture(s) failed. Retrying.' % len(none_list))
                        if ask != 'y':
                            break
                    for ix in none_list:
                        k = img_links[ix]
                        src = k.get('src')
                        pending_list.append(threading.Thread(target=get_picture, args=(ix, src, timeout, img_lists)))
                    for x1 in pending_list:
                        x1.start()
                    for x2 in pending_list:
                        x2.join()

                for ik in range(len(img_links)):
                    name = cast(epub.EpubImage, img_lists[ik]).get_name()
                    print(name)
                    img_links[ik]['src'] = name

                # Get basic pages
                text = '<br/>' + item[i].string + '<br/>' + str(text_data.find(id='content'))
                text = text.replace('<br/>\n<br/>', '<br/>')

                chapter.set_content(text)
                chapters.append(chapter)
                toc[j][1].append(chapter)
                total_image_list[j] = img_lists
        book_add[j] = chapters

    if book_number == 2:
        make_dir(book_name)
        for i in range(len(chapter_list)):
            book = book_init(book_name, author, title=chapter_list[i].string)
            book.toc = tuple(toc[i][1])
            book.spine = ['nav'] + book_add[i]
            for item in book_add[i]:
                book.add_item(item)
            for img_list in total_image_list[i]:
                book.add_item(img_list)
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            epub.write_epub(book_name + "/" + book_name + " " + chapter_list[i].string + ".epub", book)
    else:
        spine = reduce(add_list, book_add)
        book = book_init(book_name, author)
        book.toc = tuple(toc)
        book.spine = ['nav'] + spine
        for item in spine:
            book.add_item(item)
        for img_list in total_image_list:
            if img_list is not None:
                for item in img_list:
                    book.add_item(item)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub.write_epub(book_name + ".epub", book)

    time2 = time.time() - time1
    print('Done.\nUsing time: %0.1f min' % (time2 / 60))


if __name__ == "__main__":
    get_ebooks("1999", book_number=2)
