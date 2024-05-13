import json
import JsonConverter as jc

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
                        a = aList['_allTests'][indexa]['depot_directory'] + aList['_allTests'][indexa]['directory_save_file']
                        b = aList['_allTests'][indexa]['actions1'][indexb]['action1']
                        c = aList['_allTests'][indexa]['actions1'][indexb]['actions2'][indexc]['action2']
                        d = aList['_allTests'][indexa]['actions1'][indexb]['actions2'][indexc]['actions3'][indexd]['action3']
                    
                        #print(f"{indexa}|{indexb}|{indexc}|{indexd}")
                        print(f"{a}({b},{c},{d})")
                        count+=1
        print("")
        print(f"{count} tests")

    def JsonToJsonConverter(folder,file):
        tests = []
        path = folder + file
        fileObject = open(path,"r")
        jsonContent = fileObject.read()
        aList = json.loads(jsonContent)

        for indexa in range(len(aList['_allTests'])):
            last_b, last_c, last_d = "", "", ""
            for indexb in range(len(aList['_allTests'][indexa]['actions1'])):
                for indexc in range(len(aList['_allTests'][indexa]['actions1'][indexb]['actions2'])):
                    for indexd in range(len(aList['_allTests'][indexa]['actions1'][indexb]['actions2'][indexc]['actions3'])):
                        a = f"{aList['_allTests'][indexa]['depot_directory']}{aList['_allTests'][indexa]['directory_save_file']}"
                        b = aList['_allTests'][indexa]['actions1'][indexb]['action1']
                        c = aList['_allTests'][indexa]['actions1'][indexb]['actions2'][indexc]['action2']
                        d = aList['_allTests'][indexa]['actions1'][indexb]['actions2'][indexc]['actions3'][indexd]['action3']
                        
                        if(b == last_b):
                            b = "_"
                            if(c == last_c):
                                c = "_"
                                if(d == last_d):
                                    d = "_"
                        
                        tests.append([a,b,c,d])
                        
                        if(b != "_"):
                            last_b = b
                        if(c != "_"):
                            last_c = c
                        if(d != "_"):
                            last_d = d
                        

        return jc.Tests(tests)
    