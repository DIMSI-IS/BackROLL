import os
from JsonTestsReader import JsonTestsReader as jtr
from shell import shell

class ExecTests:

    def IdentificationVolumeByCharacter(str):
        if str == "C":
            return "container"
        elif str == "H":
            return "host"
        elif str == "D":
            return "docker volume"
        elif str == "N":
            return "NFS"
    
        return ""


    def ExecuteAllTests(path, file):
        fullpath = path + file
        if(not os.path.exists(fullpath)):
            return
        create = shell(f"docker volume create mon_volume")
        rm = shell(f"docker volume rm mon_volume")

        for i in create.output():
            print(f"CREATE | {i}")
    
        for i in rm.output():
            print(f"REMOVE | {i}")

        allTests =  jtr.JsonToJsonConverter(path,file)._tests
        count=0
        for availaible_volumes,action1,action2,action3 in allTests:
            depot_directory = availaible_volumes[0]
            directory_save_file = availaible_volumes[1]
            count+=1
            print(f"TESTS  | {count}")
