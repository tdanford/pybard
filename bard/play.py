
import urllib.parse
from typing import List, Union
from rich.tree import Tree 
from rich.console import Console 
import itertools 
from functools import reduce 

import requests
import textwrap
import re

from bard.parsing import soupify 

def add_dicts(d1, d2): 
    keys = set(d1.keys()).union(set(d2.keys()))
    return { k: d1.get(k, 0) + d2.get(k, 0) for k in keys }

class DramaticEvent:
    pass

class Direction(DramaticEvent): 

    direction: str 

    def __init__(self, direction: str): 
        self.direction = direction 
    
    def __repr__(self): 
        return self.direction
    
    def has_match(self, word): 
        return self.direction.lower().find(word) != -1
    
    def is_entering(self): 
        return self.has_match('enter')

    def is_exiting(self): 
        return self.has_match('exit') or self.has_match('exeunt')
    
    def serialize(self): 
        return {
            "type": "direction", 
            "direction": self.direction
        }

def serialize(value): 
    if isinstance(value, str): 
        return {
            "type": "string", 
            "value": value
        }
    else: 
        return value.serialize()

class Speech(DramaticEvent): 

    speaker: str 
    lines: List[Union[str, Direction]]
    act_no: int
    scene_no: int 
    line_no: int

    def __init__(self, speaker: str, lines: List[Union[str, Direction]], act_no: int = 1, scene_no: int = 1, line_no: int = 1):
        self.speaker = speaker 
        self.lines = lines 
        self.act_no = act_no
        self.scene_no = scene_no 
        self.line_no = line_no
    
    def scene_repr(self): 
        formatted_lines = [x if isinstance(x, str) else f"\n{x}\n" for x in self.lines]
        body = textwrap.indent("\n".join(formatted_lines), prefix="   ")
        return f"{self.speaker.upper()}:\n\n{body}"
    
    @property 
    def directions(self): 
        for line in self.lines: 
            if isinstance(line, Direction): 
                yield line

    def serialize(self): 
        return {
            "type": "speech", 
            "speaker": self.speaker, 
            "lines": [
                serialize(v) for v in self.lines
            ], 
            "act_no": self.act_no, 
            "scene_no": self.scene_no, 
            "line_no": self.line_no
        }
    
    def __repr__(self): 
        return f"{self.speaker} speaks"
    
    def __eq__(self, other): 
        if not isinstance(other, Speech): return False 
        return ( 
            self.speaker == other.speaker and 
            self.lines == other.lines and 
            self.act_no == other.act_no and 
            self.scene_no == other.scene_no and 
            self.line_no == other.line_no
        )

    def __hash__(self): 
        return hash((self.speaker, self.lines, self.act_no, self.scene_no, self.line_no))

    def __lt__(self, other: 'Speech'): 
        return ( 
            (self.act_no, self.scene_no, self.line_no, self.speaker) < 
            (other.act_no, other.scene_no, other.line_no, other.speaker)
        )

scene_title_regex = re.compile("SCENE ([IVX]+)\\.(.*)")

class Scene: 

    events: List[DramaticEvent] 
    title: str 
    act_no: int 
    scene_no: int 

    def __init__(self, title: str, act_no: int, scene_no: int): 
        self.events = [] 
        m = scene_title_regex.match(title) 
        if m is not None: 
            (roman_numerals, value) = m.groups() 
            self.title = value 
        else: 
            self.title = title 
        self.act_no = act_no 
        self.scene_no = scene_no 
    
    @property 
    def directions(self): 
        for event in self.events: 
            if isinstance(event, Direction): 
                yield event 
            else: 
                for direc in event.directions: 
                    yield direc 

    def serialize(self): 
        return {
            "type": "scene", 
            "title": self.title, 
            "act_no": self.act_no, 
            "scene_no": self.scene_no, 
            "events": [
                serialize(v) for v in self.events
            ]
        }
    
    def __repr__(self): 
        return f"Scene {self.scene_no}: {self.title}"

    def add_line(self, line, line_no: int = 1): 
        if len(self.events) == 0: raise ValueError("empty events list")
        last_event = self.events[-1] 
        if not isinstance(last_event, Speech): 
            #raise ValueError(f"Cannot add line '{line}' to non-Speech object")
            self.events.append(Speech("Unknown", [line], self.act_no, self.scene_no, line_no))
        else: 
            last_event.lines.append(line) 
    
    def add_direction(self, direction: str): 
        if len(self.events) == 0: 
            self.events.append(Direction(direction))
        elif isinstance(self.events[-1], Direction): 
            self.events.append(Direction(direction))
        else:
            self.events[-1].lines.append(Direction(direction))
    
    def add_speech(self, speaker: str, line_no: int, first_line: str): 
        new_speech = Speech(speaker, [first_line], act_no=self.act_no, scene_no=self.scene_no, line_no=line_no)
        self.events.append(new_speech) 
    
    def speeches(self): 
        for event in self.events: 
            if isinstance(event, Speech): 
                yield event 
    
    def speaker_counts(self): 
        speakers = [event.speaker for event in self.speeches()]
        speakers.sort() 
        counted = { k: len(list(g)) for (k, g) in itertools.groupby(speakers) }
        return counted
    
    def to_tree(self): 
        t = Tree(str(self)) 
        try: 
            first_dir = next(self.directions)
            t.add(f"\"{first_dir.direction}\"")
        except StopIteration: 
            pass 
        scs = self.speaker_counts()
        for (speaker, count) in scs.items(): 
            t.add(f"{speaker} speaks {count} times")
        return t

class Act: 
    """An Act is a collection of Scenes, numbered (starting with 1)
    """

    act_no: int 
    scenes: List[Scene]

    def __init__(self, act_no: int = 1): 
        self.scenes = list()
        self.act_no = act_no
    
    def serialize(self): 
        return {
            "type": "act", 
            "scenes": [
                serialize(s) for s in self.scenes
            ]
        }
    
    def __repr__(self): 
        return f"Act {self.act_no}"
    
    def add_scene(self, title: str): 
        """Add a new scene to the end of the list of scenes in the play"""
        scene_no = self.scenes[-1].scene_no + 1 if len(self.scenes) > 0 else 1 
        scene = Scene(title, self.act_no, scene_no) 
        self.scenes.append(scene) 
    
    def add_line(self, line, line_no: int = 0): 
        self.scenes[-1].add_line(line, line_no=line_no) 
    
    def add_direction(self, direction: str): 
        self.scenes[-1].add_direction(direction) 

    def add_speech(self, speaker: str, line_no: int, first_line: str): 
        self.scenes[-1].add_speech(speaker, line_no, first_line) 
    
    def speaker_counts(self): 
        return reduce(add_dicts, [s.speaker_counts() for s in self.scenes])

    def to_tree(self): 
        t = Tree(str(self)) 
        for scene in self.scenes: 
            t.add(scene.to_tree())
        return t


class Play: 

    url: str 
    title: str 
    _full_url: str 
    acts: List[Act]

    def __init__(self, title: str, url: str, full_play_url: str = None): 
        self.title = title 
        self.url = url 
        self._full_url = None
        self.acts = [] 

    def to_tree(self): 
        t = Tree(str(self)) 
        for act in self.acts: 
            t.add(act.to_tree())
        return t
    
    def serialize(self): 
        return {
            "type": "play", 
            "title": self.title, 
            "url": self.url, 
            "acts": [serialize(s) for s in self.acts]
        }
    
    def fetch_full_play_text(self): 
        response = requests.get(self.full_play_url) 
        soup = soupify(response.text) 
        return soup.text 

    def speaker_counts(self): 
        return reduce(add_dicts, [s.speaker_counts() for s in self.acts])
    
    def cast(self): 
        sc = self.speaker_counts() 
        counted = sorted([(sc[k], k) for k in sc], reverse=True) 
        return [x[1] for x in counted]
    
    def parse_play(self): 
        response = requests.get(self.full_play_url) 
        events = event_stream(response.text) 
        speech_pattern = re.compile("(\\d+)\\.(\\d+)\\.(\\d+)")
        new_speaker: str = None
        
        for (line, offset, tag) in events: 
            content = tag.text.strip()
            if tag.name == 'h3': 
                if content.startswith('ACT'): 
                    self.add_act() 
                elif content.startswith('SCENE'): 
                    self.add_scene(content) 
                else: 
                    pass
            elif tag.name == 'i': 
                self.add_direction(content)
            elif tag.name == 'a': 
                tag_name = tag.attrs.get('name')
                if tag_name is not None: 
                    m = speech_pattern.match(tag_name) 
                    if m is not None: 
                        [_, _, line_no] = [int(v) for v in m.groups()]
                        if new_speaker is not None: 
                            self.add_speech(new_speaker, line_no, content)
                            new_speaker = None
                        else: 
                            self.add_line(content, line_no)
                    else: 
                        new_speaker = content

    def add_act(self): 
        act_no = (self.acts[-1].act_no + 1) if len(self.acts) > 0 else 1 
        act = Act(act_no)
        self.acts.append(act) 

    def add_direction(self, direction: str): 
        self.acts[-1].add_direction(direction) 

    def add_scene(self, title: str): 
        self.acts[-1].add_scene(title) 
    
    def add_line(self, line, line_no: int = 0): 
        self.acts[-1].add_line(line, line_no=line_no) 
    
    def add_speech(self, speaker: str, line_no: int, first_line: str): 
        self.acts[-1].add_speech(speaker, line_no, first_line) 
    
    @property 
    def full_play_url(self): 
        if self._full_url is None: 
            response = requests.get(self.url) 
            soup = soupify(response.text) 
            anchors = soup.findAll('a') 
            entire_play_links = [x for x in anchors if x.text.find('Entire') != -1] 
            if len(entire_play_links) > 0: 
                relative_href = entire_play_links[0].attrs['href']
                self._full_url = urllib.parse.urljoin(self.url, relative_href)
        return self._full_url
    
    def fetch_raw(self): 
        response = requests.get(self.full_play_url) 
        return soupify(response.text) 
    
    def __repr__(self): 
        return f'"{self.title}"'

def make_event(tag): 
    return (tag.sourceline, tag.sourcepos, tag) 

def event_stream(text): 
    soup = soupify(text) 
    anchors = [make_event(e) for e in soup.findAll('a') ] 
    italics = [make_event(e) for e in soup.findAll('i') ]
    h3s = [make_event(e) for e in soup.findAll('h3')]
    return sorted(anchors + italics + h3s)
    
