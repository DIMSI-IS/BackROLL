def test():
    allContainer = [[1,1,1],[2,1,1],[1,2,1],[1,1,2]]
    volumes = "CHDN"
    nbTest = 0

    for repository_volume in volumes:

        for important_files_volume in volumes:

            available_volume = [repository_volume,important_files_volume]

            for container in allContainer:
                
                
                for i in range(8):

                    binary = int_to_bin(3, i)
                    print(f"bin= {binary} | {repository_volume}{important_files_volume}({container[0]}{available_volume[int(binary[-3])]},{container[1]}{available_volume[int(binary[-2])]},{container[2]}{available_volume[int(binary[-1])]})")
                    nbTest+=1
    print(f"{nbTest} Tests done")


def int_to_bin(length: int, n: int):
    binary = bin(n)
    binary = binary[2:]
    return binary.rjust(length,'0')

        

test()