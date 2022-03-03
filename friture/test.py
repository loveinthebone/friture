# from friture.spectrum import Spectrum_Widget
# from numpy import zeros, ones

# class fft_points():

#     def __init__(self):
#         self.buffer_length = 100
#         self.buffer = zeros((2, self.buffer_length))
#         self.buffer1 = zeros((2, self.buffer_length))
#         self.spectrum=Spectrum_Widget


#     def convert(self):

#         sp1=self.spectrum.dispbuffers1
#         sp2=self.spectrum.dispbuffers2

#         # sp1=ones(30)
#         # sp2=ones(30)

#         freq1_idx=10
#         freq2_idx=20

#         amp1=sp1[ freq1_idx]
#         amp2=sp2[freq2_idx]

#         self.buffer1=self.buffer
#         self.buffer[:, self.buffer_length-1]=[amp1, amp2]

#         for i in range(self.buffer_length-1):
#             self.buffer[:,i]=self.buffer1[:, i+1]

#         return self.buffer
            
class Name:
    def __init__(self):
        self.myname = "harry"
        self.num=1
        self.ls=[]

    def printaname(self):
        print("Name", self.myname )  

    def add(self) :
        self.num=self.num+1
        self.ls.append(self.num)




