# -*- coding:utf-8 -*-
from bs4 import BeautifulSoup
import requests
import re
import ebooklib
from ebooklib import epub
import time


def get_title_list():
    late = 0
    title_list = []
    for x in range(1,3):
        for i in range(0,1000):
            url = "https://www.wenku8.net/novel/"+str(x)+"/"+str(x*1000+i)+"/index.htm"
            data = BeautifulSoup(requests.get(url).content,"html.parser")
            title_data = data.find(id="title") # get the title
            print(title_data)
            if type(title_data) == type(None):
                late = late + 1 # fail too much and we will break
                if late > 5:
                    break
                continue
            else:
                late = 0
                print(x*1000+i,title_data.string,data.find(id='info').string[3:],sep=" ")
                title_list.append(url+"  "+data.find(id='info').string[3:]+"  "+title_data.string)


    with open("title_list.txt","w") as f:
        f.write("\n".join(title_list))


def get_single_one(No):
    time1 = time.time()
    url = "https://www.wenku8.net/novel/1/"+No+"/index.htm"
    data = BeautifulSoup(requests.get(url).content,"html.parser") # analyze the data
    url_link = data.findAll(class_=['vcss','ccss']) # Get the all url link

    # Create a book
    book = epub.EpubBook()
    book.set_identifier('id123456')
    book.set_title(data.find(id='title').string)
    book.set_language('en')
    book.add_author(data.find(id='info').string[3:])

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
                chapter = epub.EpubHtml(title=ahref.string,file_name=ahref.get('href'),lang='hr')
                innerlink = "https://www.wenku8.net/novel/1/"+No+"/"+ahref.get("href")
                print(ahref.get('href'),item.string)
                text_data = BeautifulSoup(requests.get(innerlink).content,"html.parser")
                text = '<br>'+item.string+'<br><br>'+str(text_data.find(id='content'))
                chapter.set_content(text)
                x[1].append(chapter)
                chapters.append(chapter)
                book.add_item(chapter)
            if i == len(url_link)-1:
                x[1] = tuple(x[1])
                toc.append(tuple(x))

    # Add important configuration data such as toc and spine
    book.toc = tuple(toc)
    book.spine = ['nav']+chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())


    # Write the books
    epub.write_epub(data.find(id='title').string+'.epub',book)

    # Return the time
    print('Done\nUsing time:',time.time()-time1)


if __name__ == "__main__":
    get_title_list()
    # get_single_one('1213')