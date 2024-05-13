import json

class Tests:
    
    _tests = []
    
    def __init__(self, tests):
        self._tests = tests
        

    def ToString(self):
        str = ""
        for test in self._tests:
            str = str + f"{test[0]}("
            for i in range(1,len(test)):
                str = str + f"{test[i]},"
            str = str[:-1] + ")\n"
        return str
    
    def ToJson(self):
        return json.dumps(JsonConverter(self._tests), indent=4, cls=JsonConverterEncoder)
        
            
class JsonConverter():
    
    _allTests = []
    
    def __init__(self, tests):
        allTests = []
        lastVolumes = ""
        jsonTest = Test("", ["","",""])
        for test in tests:
            
            if(test[1] != "_" and test[2] != "_" and test[3] != "_"):
                if(jsonTest.depot_directory + jsonTest.directory_save_file != "" and test[0] != lastVolumes):
                    allTests.append(jsonTest)
                if(test[0] != lastVolumes):
                    jsonTest = Test(test[0], [test[1],test[2],test[3]])
                    
                
            if(test[2] == "_" and test[3] != "_"):
                jsonTest.actions1[-1].actions2[-1].AddAction(test[3])
            
            if(test[1] == "_" and test[2] != "_"):
                jsonTest.actions1[-1].AddAction(test[2],test[3])
                
            if(test[0] == lastVolumes and test[1] != "_"):
                jsonTest.AddAction([test[1], test[2], test[3]])
            
            lastVolumes = test[0]
                
        allTests.append(jsonTest)
        self._allTests = allTests
        
        
        
        
    
class Test():
    def __init__(self, available_volume, actions):
        
        if len(available_volume) > 0:
            self.depot_directory = available_volume[0]

            if len(available_volume) > 1:
                self.directory_save_file = available_volume[1]
            else:
                self.directory_save_file = ""
        else:
            self.depot_directory = ""
            self.directory_save_file = ""
        

        self.actions1 = [Action1(actions[0],actions[1],actions[2])]
    
    def AddAction(self, actions):
        self.actions1.append(Action1(actions[0],actions[1],actions[2]))
        
class Action1():
    def __init__(self, action1, action2, action3):
        self.action1 = action1
        self.actions2 = [Action2(action2,action3)]
    
    def AddAction(self, action2, action3):
        self.actions2.append(Action2(action2, action3))
        
class Action2():
    def __init__(self, action2, action3):
        self.action2 = action2
        self.actions3 = [Action3(action3)]
    
    def AddAction(self, action3):
        self.actions3.append(Action3(action3))
        
class Action3():
    def __init__(self, action3):
        self.action3 = action3
        
class JsonConverterEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__
        