import itertools as iter
import time


def generate_list_of_test(containers, volumes, nbAction):
    nbTest = 0
    nbUnderscore = 0

    allTest = []

    for available_volumes in iter.product(volumes, repeat=2):
        # Initilisation
        #print("Initialisation")
        first_action = True
        index_of_index = nbAction
        list_index = [0]*nbAction
        list_action = [[]]*nbAction
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

        #print(f"index_of_index: {index_of_index}")
        tmp_str = "list_index: "
        for i in list_index:
            tmp_str = tmp_str + f"{i},"
        #print(tmp_str)

        tmp_str = "list_action:\n"
        for i in range(len(list_action)):
            tmp_str = tmp_str + f"{i}: "
            for j in list_action[i]:
                tmp_str = tmp_str + f"{j},"
            tmp_str = tmp_str + "\n"
        #print(tmp_str)
        #print("")

        # Hearth of the code
        while (list_index[0] < len(list_action[0])):

            # Write a test
            str_test = f"{available_volumes[0]}{available_volumes[1]}("
            str_index = ""
            for i in range(len(list_index)):
                str_index = str_index + f"{list_index[i]}"
                if(i != 0):
                    str_test = str_test + ','
                
                if((index_of_index > i) and (not first_action)):
                    str_test = str_test + '_'
                    nbUnderscore+=1
                else:
                    str_test = str_test + f"{list_action[i][list_index[i]]}"

            str_test = str_test + ')'
            #print(f"index_of_index: {index_of_index}")
            #print(f"Index: {str_index}")
            print(str_test)
            
            nbTest += 1

            

            # Manage list_of_index
            for i in range(-1, -(len(list_index)+1), -1):
                if(i == -(len(list_index))):
                    list_index[i] += 1
                    index_of_index = i%len(list_index)
                    #print(f"list_index[i] >= len(list_action[i])-1\n{list_index[i]} >= {len(list_action[i])-1} | {list_index[i] >= len(list_action[i])-1}")
                    break
                if (list_index[i] >= len(list_action[i])-1):
                    list_index[i] = 0
                    continue
                else:
                    list_index[i] += 1
                    index_of_index = i%len(list_index)
                    break
                
                
            str_index = ""
            for index in list_index:
                str_index = str_index + f"{index}"
            #print(f"IndexEnd: {str_index}")
            #print("")
            
            first_action = False
            
            #time.sleep(0.5)

        #print("")
        #print("_____________________________________")
        #print("")

    print(f"{nbTest} Tests done | {nbUnderscore} underscores used")

generate_list_of_test('12', 'CHDN', 3)
>>>>>>> f7fb894 (Script de generation de Tests, test_plan, dans la sortie standard)
