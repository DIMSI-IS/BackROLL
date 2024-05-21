import sys
sys.path.append(sys.path[0]+"/../build")
print(sys.path)
from test_plan import JsonWriter as jw
import JsonConverter as jc
from exec_tests import ExecTests as exet
from JsonTestsReader import JsonTestsReader as jtr

def main():
    extension1 = ".json"
    print(f"Main function from: {sys.argv}")
    jw(True, 0,sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], f"{sys.argv[5]}{extension1}")
    exet.ExecuteAllTests(sys.argv[4],f"{sys.argv[5]}{extension1}")


    
main()