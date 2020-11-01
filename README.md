### Get e-books from https://www.wenku8.net
This is a small project to get e-books in the form of epub from a novel webesites.
```python
get_title_list(timeout=(8,10),max_retries=5) # To get a title list on wenku8.
get_ebooks(No,booknumber=1,timeout=(8,10),max_retries=5,always=False)
"""
A little function to get ebook(s) from www.wenku8.net.

Args:
number: A string of number representing the book. Example: "1","1999"
book_number: A int to choose to create only one file(1) or multiple files(2).
timeout: A tuple with two values which refer to the waiting time of sending requests and waiting responses
max_retries: A int to set the times of retring requests the url.
always: A Boolean to depend whether keep retring to request or not.
"""
```