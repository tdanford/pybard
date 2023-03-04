
from bard.play import Play, Act, Scene, Speech 

def test_speech_equality(): 
    speech1 = Speech("John", ["Hi, my name is", "John"])
    speech2 = Speech("John", ["Hi, my name is", "John"])
    speech3 = Speech("John", ["Hi, my name is John"])
    speech4 = Speech("John", ["Hi, my name is John", ""])
    speech5 = Speech("Bill", ["Hi, my name is", "John"])

    assert speech1 == speech2 
    assert speech1 != speech3
    assert speech1 != speech4
    assert speech1 != speech5