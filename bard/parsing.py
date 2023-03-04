from bs4 import BeautifulSoup as Soup 

def soupify(text: str) -> Soup: 
    return Soup(text, 'html.parser')