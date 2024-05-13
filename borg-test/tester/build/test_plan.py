import itertools as iter
import JsonConverter as jc
import os

class JsonWriter:

    def __init__(self, generate_a_list_of_test, jsonConverter, containers, volumes, nbAction, pathForJsonFile, fileName):
        if generate_a_list_of_test:
            jsonC = self.generate_list_of_test(containers, volumes, nbAction)
        else:
            jsonC = jsonConverter
        self.WriteAFile(pathForJsonFile+fileName, jsonC)

    def generate_list_of_test(self, containers, volumes, nbAction):
        nbTest = 0
        nbUnderscore = 0
        if(isinstance(nbAction,str)):
            nbAction = int(nbAction)


        allTest = []

        for available_volumes in iter.product(volumes, repeat=2):
        
        
            #Initilisation
            first_action = True
            index_of_index = nbAction-1
            consumable_index = nbAction
            consume = False
            list_index = [0]*nbAction
            list_action = [[]]*nbAction
            test = []
            for i in range(len(list_action)):
                if (available_volumes[0] == available_volumes[1]):
                    if (i == 0):
                        list_action[i] = list(iter.product(
                            containers[0], available_volumes[0]))
                    else:
                        list_action[i] = list(iter.product(
                            containers, available_volumes[0]))

                else:
                    if (i == 0):
                        list_action[i] = list(iter.product(
                            containers[0], available_volumes))
                    else:
                        list_action[i] = list(iter.product(
                            containers, available_volumes))
                for j in range(len(list_action[i])):
                    list_action[i][j] = f"{list_action[i][j][0]}{list_action[i][j][1]}"

            tmp_str = "list_index: "
            for i in list_index:
                tmp_str = tmp_str + f"{i},"

            tmp_str = "list_action:\n"
            for i in range(len(list_action)):
                tmp_str = tmp_str + f"{i}: "
                for j in list_action[i]:
                    tmp_str = tmp_str + f"{j},"
                tmp_str = tmp_str + "\n"

            # Hearth of the code
            while (list_index[0] < len(list_action[0])):
            
                if(index_of_index == len(list_index)-1):

                    # Write a test
                    str_test = f"{available_volumes[0]}{available_volumes[1]}("
                    str_index = ""
                    test.append(f"{available_volumes[0]}{available_volumes[1]}")
                
                    for i in range(len(list_index)):
                        str_index = str_index + f"{list_index[i]}"
                        if(i != 0):
                            str_test = str_test + ','
                
                        if((consumable_index > i) and (not first_action)):
                            str_test = str_test + '_'
                            test.append('_')
                            consume = True
                            nbUnderscore+=1
                        else:
                            str_test = str_test + f"{list_action[i][list_index[i]]}"
                            test.append(f"{list_action[i][list_index[i]]}")
                    
                        if(consumable_index == 0):
                            consume = True
                    allTest.append(test)
                    test = []
                    str_test = str_test + ')'
                
                    #print(f"{str_test}")
                    nbTest += 1

            

                # Manage list_of_index
                list_index[index_of_index] += 1
                
                if(list_index[index_of_index] >= len(list_action[index_of_index])):
                    if(index_of_index == 1):
                        for i in range(1,nbAction-1):
                            list_index[i] = -1
                            index_of_index-=1
                    if(index_of_index > 1):  
                        list_index[index_of_index] = 0
                        index_of_index-=1
                
                else:
                    if(index_of_index < nbAction-1):
                        index_of_index+=1
                
                if(consume):
                    consume = False
                    consumable_index = nbAction
                
                if(index_of_index < consumable_index):  
                    consumable_index = index_of_index
                
                str_index = ""
                for index in list_index:
                    str_index = str_index + f"{index}"
            
                first_action = False
    
        #print(f"{nbTest} Tests done | {nbUnderscore} underscores used")
        print(f"{nbTest*3-nbUnderscore} actions to execute")
        return jc.Tests(allTest)



    def WriteAFile(self, path, jsonConverter):
        if(os.path.exists(path)):
            fichier = open(path,"a")
            fichier.truncate(0)
            fichier.write(jsonConverter.ToJson())
            fichier.close()
        else:
            content = jsonConverter.ToJson() 
            with open(path, "w") as file:
                file.write(content)