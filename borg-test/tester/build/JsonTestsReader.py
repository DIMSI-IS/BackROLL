import json

class JsonTestsReader:


    def JsonToString(folder,file):
        path = folder + file
        fileObject = open(path,"r")
        jsonContent = fileObject.read()
        aList = json.loads(jsonContent)
        count = 0
        for indexa in range(len(aList['_allTests'])):
            print("")
            for indexb in range(len(aList['_allTests'][indexa]['actions1'])):
                for indexc in range(len(aList['_allTests'][indexa]['actions1'][indexb]['actions2'])):
                    for indexd in range(len(aList['_allTests'][indexa]['actions1'][indexb]['actions2'][indexc]['actions3'])):
                        a = aList['_allTests'][indexa]['available_volume']
                        b = aList['_allTests'][indexa]['actions1'][indexb]['action1']
                        c = aList['_allTests'][indexa]['actions1'][indexb]['actions2'][indexc]['action2']
                        d = aList['_allTests'][indexa]['actions1'][indexb]['actions2'][indexc]['actions3'][indexd]['action3']
                    
                        #print(f"{indexa}|{indexb}|{indexc}|{indexd}")
                        print(f"{a}({b},{c},{d})")
                        count+=1
        print("")
        print(f"{count} tests")

#JsonTestsReader.JsonToString("TestsFile.json")