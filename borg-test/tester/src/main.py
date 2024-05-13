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
    print(f"Main function from: {sys.argv}")
    if(not os.path.exists(sys.argv[4]+f"{sys.argv[5]}{extension1}")):
        jw(True, 0,sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], f"{sys.argv[5]}{extension1}")
    jsonC1 =  jtr.JsonToJsonConverter(sys.argv[4],f"{sys.argv[5]}{extension1}")
    time.sleep(1)
    if not os.path.exists(sys.argv[4]+f"{sys.argv[5]}{extension2}"):
        jw(False, jsonC1,sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], f"{sys.argv[5]}{extension2}")
    jsonC2 = jtr.JsonToJsonConverter(sys.argv[4],f"{sys.argv[5]}{extension2}")

    
    for i in jsonC1._tests:
        print(f"{i[0]}({i[1]},{i[2]},{i[3]})")
    print("________________________________________________________________")
    print("________________________________________________________________")
    for i in jsonC2._tests:
        print(f"{i[0]}({i[1]},{i[2]},{i[3]})")
    
main()