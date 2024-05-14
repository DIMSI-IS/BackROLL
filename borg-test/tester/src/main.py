import sys
import os
import time
sys.path.append(sys.path[0]+"/../build")
from test_plan import JsonWriter as jw
import JsonConverter as jc
from JsonTestsReader import JsonTestsReader as jtr

def main():
    extension1 = "0.json"
    extension2 = "1.json"
    extension3 = "2.json"
    print(f"Main function from: {sys.argv}")
    if(not os.path.exists(sys.argv[4]+f"{sys.argv[5]}{extension1}")):
        jw(True, 0,sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], f"{sys.argv[5]}{extension1}")
    jsonC1 =  jtr.JsonToJsonConverter(sys.argv[4],f"{sys.argv[5]}{extension1}")
    if not os.path.exists(sys.argv[4]+f"{sys.argv[5]}{extension2}"):
        jw(False, jsonC1,sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], f"{sys.argv[5]}{extension2}")
    jsonC2 = jtr.JsonToJsonConverter(sys.argv[4],f"{sys.argv[5]}{extension2}")
    if not os.path.exists(sys.argv[4]+f"{sys.argv[5]}{extension3}"):
        jw(False, jsonC2,sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], f"{sys.argv[5]}{extension3}")
    jsonC3 = jtr.JsonToJsonConverter(sys.argv[4],f"{sys.argv[5]}{extension3}")

    """
    for i in jsonC1._tests:
        print(f"{i[0]}({i[1]},{i[2]},{i[3]})")
    print("________________________________________________________________")
    print("________________________________________________________________")
    for i in jsonC2._tests:
        print(f"{i[0]}({i[1]},{i[2]},{i[3]})")
    """
    file1 = open(sys.argv[4]+f"{sys.argv[5]}{extension1}")
    file2 = open(sys.argv[4]+f"{sys.argv[5]}{extension2}")
    file3 = open(sys.argv[4]+f"{sys.argv[5]}{extension3}")
    #print(f"File1:\n{file1.read()}")
    #print(f"File2:\n{file2.read()}")
    #print(f"File3:\n{file3.read()}")
    bool12 = True
    for line1,line2 in zip(file1,file2):
        bool12 = bool12 and (line1==line2)

    bool13 = True
    for line1,line3 in zip(file1,file3):
        bool13 = bool13 and (line1==line3)

    bool23 = True
    for line2,line3 in zip(file2,file3):
        bool23 = bool23 and (line2==line3)

    print(f"File 1-2 are equal: {bool12}")
    print(f"File 1-3 are equal: {bool13}")
    print(f"File 2-3 are equal: {bool23}")

    #print(f"File 1-2 are equal: {file1.read() == file2.read()}")
    #print(f"File 1-3 are equal: {file1.read() == file3.read()}")
    #print(f"File 2-3 are equal: {file2.read() == file3.read()}")

    
main()