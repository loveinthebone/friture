# from friture.test import fft_points

# if __name__ == "__main__":
#     objName = fft_points()

#     see=  objName.convert()
#     print("finally!")

from friture.test import Name

if __name__ == "__main__":
    objName = Name()
    objName.printaname()
    for i in range(5):
        objName.add()
    print(objName.ls)