import sys
import os
sys.path.append(sys.path[0]+"/../build")
from test_plan import JsonWriter as jw
from JsonTestsReader import JsonTestsReader as jtr

def main():
    print(f"Main function from: {sys.argv}")
    if(not os.path.exists(sys.argv[4]+sys.argv[5])):
        jw(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    jtr.JsonToString(sys.argv[4],sys.argv[5])  
    
    
main()