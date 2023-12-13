import cv2
import numpy as np
import math
import glob

# Sources: https://github.com/RobinDavid/LSB-Steganography

class SteganographyException(Exception):
    pass

class LSBSteg():
    def __init__(self, img_list):
        # combine images horizontally
        # combine images horizontally
        images = []
        for i in range(1, len(img_list)+1):
            images.append(cv2.imread(img_list[0].split("/")[0] +"/board_{}.png".format(i)))

        if len(images) == 1:
            self.image = images[0]
        else:
            # combine images horizontally
            self.image = np.hstack((images[0], images[1]))
            for i in range(2, len(images)):
                self.image = np.hstack((self.image, images[i]))

        self.height, self.width, self.nbchannels = self.image.shape
        self.size = self.width * self.height

        self.cell_width = 50
        self.cell_height = 50

        self.width_part = self.width // self.cell_width
        self.height_part = self.height // self.cell_height

        self.part_height = self.height // self.height_part
        self.part_width = self.width // self.width_part
        
        self.maskONEValues = [1,2,4,8,16,32,64,128]
        #Mask used to put one ex:1->00000001, 2->00000010 .. associated with OR bitwise
        self.maskONE = self.maskONEValues.pop(0) #Will be used to do bitwise operations
        
        self.maskZEROValues = [254,253,251,247,239,223,191,127]
        #Mak used to put zero ex:254->11111110, 253->11111101 .. associated with AND bitwise
        self.maskZERO = self.maskZEROValues.pop(0)
        
        self.curwidth = 0  # Current width position
        self.curheight = 0 # Current height position
        self.curwidth_ = 0  # Current width position
        self.curheight_ = 0 # Current height position
        self.curchan = 0   # Current channel position
        self.cur_width_part = 0
        self.cur_height_part = 0
        self.cycle = 0

    def put_binary_value(self, bits): #Put the bits in the image
        for c in bits:
            val = list(self.image[self.curheight,self.curwidth]) #Get the pixel value as a list
            if int(c) == 1:
                val[self.curchan] = int(val[self.curchan]) | self.maskONE #OR with maskONE
            else:
                val[self.curchan] = int(val[self.curchan]) & self.maskZERO #AND with maskZERO
                
            self.image[self.curheight,self.curwidth] = tuple(val)
            self.next_slot() #Move "cursor" to the next space
    
    def next_slot(self): #Move to the next slot were information can be taken or put
        if self.cur_width_part == self.width_part-1:
            self.cur_width_part = 0
            if self.cur_height_part == self.height_part-1:
                self.cur_height_part = 0
                if self.curchan == self.nbchannels-1:
                    self.curchan = 0
                    if self.curwidth_ == self.part_width-1:
                        self.curwidth_ = 0
                        if self.curheight_ == self.part_height-1:
                            self.curheight_ = 0
                            if self.maskONE == 128:
                                raise SteganographyException("No available slot remaining (image filled)")
                            else:
                                self.maskONE = self.maskONEValues.pop(0)
                                self.maskZERO = self.maskZEROValues.pop(0)
                        else:
                            self.curheight_ +=1
                    else:
                        self.curwidth_ +=1
                else:
                    self.curchan +=1
            else:
                self.cur_height_part += 1
        else:
            self.cur_width_part += 1
        
        self.curwidth = self.cur_width_part * self.part_width + self.curwidth_
        self.curheight = self.cur_height_part * self.part_height + self.curheight_

    def read_bit(self): #Read a single bit int the image
        val = self.image[self.curheight,self.curwidth][self.curchan]
        val = int(val) & self.maskONE
        self.next_slot()
        if val > 0:
            return "1"
        else:
            return "0"
    
    def read_byte(self):
        return self.read_bits(8)
    
    def read_bits(self, nb): #Read the given number of bits
        bits = ""
        for i in range(nb):
            bits += self.read_bit()
        return bits

    def byteValue(self, val):
        return self.binary_value(val, 8)
        
    def binary_value(self, val, bitsize): #Return the binary value of an int as a byte
        binval = bin(val)[2:]
        if len(binval) > bitsize:
            raise SteganographyException("binary value larger than the expected size")
        while len(binval) < bitsize:
            binval = "0"+binval
        return binval

    def encode_text(self, txt):
        l = len(txt)
        binl = self.binary_value(l, 16) #Length coded on 2 bytes so the text size can be up to 65536 bytes long
        self.put_binary_value(binl) #Put text length coded on 4 bytes
        for char in txt: #And put all the chars
            c = ord(char)
            self.put_binary_value(self.byteValue(c))
        return self.image
       
    def decode_text(self):
        ls = self.read_bits(16) #Read the text size in bytes
        l = int(ls,2)
        i = 0
        unhideTxt = ""
        while i < l: #Read all bytes of the text
            tmp = self.read_byte() #So one byte
            i += 1
            unhideTxt += chr(int(tmp,2)) #Every chars concatenated to str
        return unhideTxt

    def encode_binary(self, data):
        l = len(data)
        if self.width*self.height*self.nbchannels < l+64:
            raise SteganographyException("Carrier image not big enough to hold all the datas to steganography")
        self.put_binary_value(self.binary_value(l, 64))
        for byte in data:
            byte = byte if isinstance(byte, int) else ord(byte) # Compat py2/py3
            self.put_binary_value(self.byteValue(byte))
        return self.image

    def decode_binary(self):
        l = int(self.read_bits(64), 2)
        print("Length: ", l)
        output = b""
        for i in range(l):
            output += bytearray([int(self.read_byte(),2)])
        return output