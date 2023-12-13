from window import Ui_MainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
import sys

from huffman import compress, decompress, save_msg_tree, build_dict_from_text, build_huffman_tree
import glob
import cv2
import random

from chess_stegano import main_embedMessage, readMessage
from chess_vision import detect_fen

from rc4 import *
from lsb_multi import LSBSteg
import base64
import numpy as np

def generate_random_pawn_mapping():
    pawn_mapping = list(range(1, 9))
    random.shuffle(pawn_mapping)
    return "".join(map(str, pawn_mapping))

def load(ui):
    ui.comboBoxCapacity.addItem("24 bits")
    ui.comboBoxCapacity.addItem("32 bits")
    ui.comboBoxCapacity.addItem("40 bits")

    ui.comboBoxCapacity.setCurrentIndex(1)

    ui.spinBoxKey.setValue(4)

    ui.textEdit_IOPath.setPlaceholderText("message1")
    ui.textEdit_IOText.setPlaceholderText("input/output text")
    ui.textEdit_RC4Key.setPlaceholderText("key in base64")

    # generate random key
    random_key = generate_random_key(32)
    ui.textEdit_RC4Key.setPlainText(base64.b64encode(random_key).decode('utf-8'))

    ui.textEdit_PawnMapping.setPlainText(generate_random_pawn_mapping())
    ui.textEdit_IOText.setPlainText("meet me under the bridge at 10 pm")
    ui.textEdit_IOPath.setPlainText("boards")

    # Set IOText Texsize
    font = QtGui.QFont()
    font.setPointSize(14)
    ui.textEdit_IOText.setFont(font)

def psnr(img1, img2):
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return 100
    PIXEL_MAX = 255.0
    psnr = 20 * np.log10(PIXEL_MAX / np.sqrt(mse))
    return psnr

def get_avg_psnr(io_ori, io_embedded):
    image_list_ori = glob.glob(io_ori + "/*.png")
    image_list_ori.sort()

    image_list_embedded = glob.glob(io_embedded + "/*.png")
    image_list_embedded.sort()

    avg_psnr = 0
    for i in range(len(image_list_ori)):
        img_ori = cv2.imread(image_list_ori[i])
        img_embedded = cv2.imread(image_list_embedded[i])

        psnr_value = psnr(img_ori, img_embedded)
        print("compare", image_list_ori[i], image_list_embedded[i], psnr_value)

        avg_psnr += psnr(img_ori, img_embedded)

    avg_psnr /= len(image_list_ori)

    return avg_psnr

def cleanup():
    file_to_delete = ["temp/freq_dict.bin", "temp/freq_dict_enc.bin", "temp/temp.bin", "24bits.png", "32bits.png", "40bits.png", "randomize.png"]
    for file in file_to_delete:
        if os.path.exists(file):
            os.remove(file)

if __name__ == "__main__":
    if not os.path.exists("temp"):
        os.makedirs("temp")

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)

    load(ui)

    def pushButton_Generate_clicked():
        ui.statusLabel.setText("Status: Idle")
        ui.labelGenerated.setText("Generated Chessboard (0):")

        # clear scroll area
        scroll_area = ui.scrollArea
        scroll_area.setWidgetResizable(True)
        scroll_area_widget_contents = QtWidgets.QWidget()

        text = ui.textEdit_IOText.toPlainText()
        key = ui.spinBoxKey.value()
        capacity = ui.comboBoxCapacity.currentText()
        pawn_mapping = ui.textEdit_PawnMapping.toPlainText()
        io_path = ui.textEdit_IOPath.toPlainText()
 
        if capacity == "24 bits":
            capacity = 24
        elif capacity == "32 bits":
            capacity = 32
        elif capacity == "40 bits":
            capacity = 40

        # compress and save freq_dict
        save_msg_tree(text)
        compressed_message, root = compress(text)

        # add padding
        padding_length = capacity - len(compressed_message) % capacity
        compressed_message += '0' * padding_length

        ui.statusLabel.setText("Status: Generating...")
        status, image_list = main_embedMessage(compressed_message, key, capacity, batch_folder=io_path, pawn_mapping=pawn_mapping)

        # print("image_list", image_list)

        if status == False:
            ui.statusLabel.setText("Status: Failed!")
        else:
            ui.statusLabel.setText("Status: Success!")
            
            scroll_area = ui.scrollArea
            scroll_area.setWidgetResizable(True)
            scroll_area_widget_contents = QtWidgets.QWidget()

            # create grid layout for image
            grid_layout = QtWidgets.QGridLayout()
            grid_layout.setSpacing(10)
            grid_layout.setContentsMargins(10, 10, 10, 10)
            scroll_area_widget_contents.setLayout(grid_layout)

            # read huffman tree (freq_dict), then encrypt using rc4
            with open('temp/freq_dict.bin', 'rb') as f:
                huffman_tree = f.read()

            rc4_key = ui.textEdit_RC4Key.toPlainText()
            rc4_key = base64.b64decode(rc4_key)
            encrypted_huffman_tree = rc4_encrypt(huffman_tree, rc4_key)

            # save encrypted huffman tree
            with open('temp/freq_dict_enc.bin', 'wb') as f:
                f.write(encrypted_huffman_tree)

            # embed encrypted huffman tree to generated image
            lsb_steg = LSBSteg(image_list)

            padding_length_binary = lsb_steg.binary_value(padding_length, 8)
            # convert string to binary

            padding_length_bytes = int(padding_length_binary, 2)

            # print("padding_length_binary", padding_length_bytes)
            # write padding length to temp.bin
            with open("temp/temp.bin", "wb") as f:
                f.write(padding_length_bytes.to_bytes(1, byteorder='big'))

            # then append encrypted huffman tree to temp.bin
            with open("temp/temp.bin", "ab") as f:
                f.write(encrypted_huffman_tree)

            # read temp.bin
            with open("temp/temp.bin", "rb") as f:
                data = f.read()

            # embed data to image
            res = lsb_steg.encode_binary(data)

            # save image
            for i in range(len(image_list)):
                current_img = res[:, i*400:(i+1)*400]
                cv2.imwrite(image_list[i], current_img)

            # add image to grid layout
            for i in range(len(image_list)):
                image_path = image_list[i]
                
                image = QtGui.QImage(image_path)
                # resize image
                image = image.scaled(200, 200, QtCore.Qt.KeepAspectRatio)

                image_label = QtWidgets.QLabel()
                image_label.setPixmap(QtGui.QPixmap.fromImage(image))
                image_label.setAlignment(QtCore.Qt.AlignCenter)

                # add to grid layout horizontally
                grid_layout.addWidget(image_label, 0, i)

            scroll_area.setWidget(scroll_area_widget_contents)

            ui.labelGenerated.setText("Generated chessboard (" + str(len(image_list))+ "):")

            print("=====================================")
            print("message size in bytes: ", len(text.encode('utf-8')))

            print("=====================================")
            huffman_size = open("temp/freq_dict.bin", "rb").read().__sizeof__()
            print("huffman_size", huffman_size)
            print("=====================================")
            print("Total chessboard: ", len(image_list))
            # calculate avg psnr

        cleanup()

    def pushButton_Extract_clicked():
        print("Button extract clicked")
        # ui.statusLabel.setText("Status: Idle")
        # ui.labelGenerated.setText("Generated Chessboard (0):")

        # clear scroll area
        scroll_area = ui.scrollArea
        scroll_area.setWidgetResizable(True)
        scroll_area_widget_contents = QtWidgets.QWidget()

        key = ui.spinBoxKey.value()
        capacity = ui.comboBoxCapacity.currentText()
        pawn_mapping = ui.textEdit_PawnMapping.toPlainText()
        io_path = ui.textEdit_IOPath.toPlainText()

        if capacity == "24 bits":
            capacity = 24
        elif capacity == "32 bits":
            capacity = 32
        elif capacity == "40 bits":
            capacity = 40
        
        # read all images from io_path
        image_list = glob.glob(io_path + "/*.png")
        image_list.sort()

        for i in range(len(image_list)):
            # replace \\ to /
            image_list[i] = image_list[i].replace("\\", "/")

        # display image to scroll area
        scroll_area = ui.scrollArea
        scroll_area.setWidgetResizable(True)
        scroll_area_widget_contents = QtWidgets.QWidget()

        # create grid layout for image
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        scroll_area_widget_contents.setLayout(grid_layout)

        # add image to grid layout
        for i in range(len(image_list)):
            image_path = image_list[i]
            
            image = QtGui.QImage(image_path)
            # resize image
            image = image.scaled(200, 200, QtCore.Qt.KeepAspectRatio)

            image_label = QtWidgets.QLabel()
            image_label.setPixmap(QtGui.QPixmap.fromImage(image))
            image_label.setAlignment(QtCore.Qt.AlignCenter)

            # add to grid layout horizontally
            grid_layout.addWidget(image_label, 0, i)

        # read padding length and encrypted huffman tree
        lsb_steg = LSBSteg(image_list)
        data = lsb_steg.decode_binary()

        padding_length = data[0]
        print("padding_length", padding_length)

        huffman_tree = data[1:]

        # save to temp.bin
        # with open("temp/temp.bin", "wb") as f:
        #     f.write(huffman_tree)

        # # compare with original huffman tree
        # with open("temp/freq_dict_enc.bin", "rb") as f:
        #     original_huffman_tree = f.read()

        # if huffman_tree != original_huffman_tree:
        #     print("Huffman tree is not equal!")
        # else:
        #     print("Huffman tree is equal!")

        # decrypt huffman tree
        rc4_key = ui.textEdit_RC4Key.toPlainText()
        rc4_key = base64.b64decode(rc4_key)
        decrypted_huffman_tree = rc4_decrypt(huffman_tree, rc4_key)

        print("Decrypted huffman tree: ", decrypted_huffman_tree)

        freq_dict = build_dict_from_text(str(decrypted_huffman_tree, 'utf-8'))
        huffman_tree = build_huffman_tree(freq_dict)

        # read message
        message = ""
        for file in glob.glob(f'{io_path}/board_*.png'):
            # read image
            image_list = []
            img = cv2.imread(file)

            # split image to 8x8
            for i in range(8):
                for j in range(8):
                    x = 50 * j
                    y = 50 * i
                    image_list.append(img[y:y+50, x:x+50])

            # detect piece
            detected_FEN = detect_fen(image_list)

            # compare
            print("Detected FEN: ", detected_FEN)

            msg_read = readMessage(detected_FEN, key, capacity, pawn_mapping=pawn_mapping)

            message += msg_read

        message = message[:-padding_length]
        # decompress
        decompressed_message = decompress(message, huffman_tree)
        print("Decompressed message: ", decompressed_message)

        # display message
        ui.textEdit_IOText.setPlainText(decompressed_message)

        cleanup()

    def save_config():
        # open file dialog
        filename = QtWidgets.QFileDialog.getSaveFileName(None, 'Save File', os.getcwd(), "Text files (*.txt)")
        if filename[0] == "": return
        
        text = ""
        text += "PAWN_KEY=" + str(ui.spinBoxKey.value()) + "\n"
        text += "RC4_KEY=" + ui.textEdit_RC4Key.toPlainText() + "\n"
        text += "CAPACITY=" + ui.comboBoxCapacity.currentText() + "\n"
        text += "PAWN_MAPPING=" + ui.textEdit_PawnMapping.toPlainText() + "\n"

        with open(filename[0], "w") as f:
            f.write(text)

    def load_config():
        # open file dialog
        filename = QtWidgets.QFileDialog.getOpenFileName(None, 'Open File', os.getcwd(), "Text files (*.txt)")
        if filename[0] == "": return
        
        with open(filename[0], "r") as f:
            text = f.read()

        text = text.split("\n")
        text = [x for x in text if x != ""]
        
        for line in text:
            if "PAWN_KEY=" in line:
                ui.spinBoxKey.setValue(int(line.replace("PAWN_KEY=", "")))
            elif "RC4_KEY=" in line:
                ui.textEdit_RC4Key.setPlainText(line.replace("RC4_KEY=", ""))
            elif "CAPACITY=" in line:
                capacity = line.replace("CAPACITY=", "")
                if capacity == "24 bits":
                    ui.comboBoxCapacity.setCurrentIndex(0)
                elif capacity == "32 bits":
                    ui.comboBoxCapacity.setCurrentIndex(1)
                elif capacity == "40 bits":
                    ui.comboBoxCapacity.setCurrentIndex(2)
            elif "PAWN_MAPPING=" in line:
                ui.textEdit_PawnMapping.setPlainText(line.replace("PAWN_MAPPING=", ""))

    ui.pushButton_Generate.clicked.connect(pushButton_Generate_clicked)
    ui.pushButton_Extract.clicked.connect(pushButton_Extract_clicked)

    ui.actionLoad_Config.triggered.connect(load_config)
    ui.actionSave_Config.triggered.connect(save_config)

    MainWindow.show()
    sys.exit(app.exec_())

