
from typing import Dict, List
import requests 
import urllib.parse 
from rich.console import Console 

from bard.parsing import soupify 
from bard.play import Play 

console = Console() 

def fetch_plays() -> List['Play']:
    url = 'http://shakespeare.mit.edu'

    response = requests.get(url) 
    soup = soupify(response.text) 
    tables = soup.findAll('table')
    
    central_table = tables[1] 
    anchors = central_table.findAll('a')

    return [
        Play(
            a.text.strip(),
            urllib.parse.urljoin(url, a.attrs.get('href'))
        ) for a in anchors if a.attrs.get('href').lower().find('poetry') == -1
    ]