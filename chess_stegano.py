import chess
import chess.svg
import random
from cairosvg import svg2png
import os, json
import shutil

def writeImage(fen, filename):
    board = chess.Board(fen)
    svg = chess.svg.board(board=board, coordinates=False, size=400)
    svg2png(bytestring=svg, write_to=f"{filename}")

def validate(FEN):
    board = chess.Board(FEN)

    # rule 1: both king must be on the board
    king = [False, False]
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None and piece.symbol() == 'k':
            king[0] = True
        if piece is not None and piece.symbol() == 'K':
            king[1] = True

    if king[0] == False or king[1] == False:
        return False
    
    # only 2 king available
    king_count = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None and piece.symbol() == 'k':
            king_count+=1
        if piece is not None and piece.symbol() == 'K':
            king_count+=1

    # return True

    # king not placed adjacently
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None and piece.symbol() == 'k':
            for i in range(-1, 2):
                for j in range(-1, 2):
                    if i == 0 and j == 0: continue
                    if chess.square_rank(square)+i < 0 or chess.square_rank(square)+i > 7: continue
                    if chess.square_file(square)+j < 0 or chess.square_file(square)+j > 7: continue

                    adj_square = chess.square(chess.square_file(square)+j, chess.square_rank(square)+i)
                    adj_piece = board.piece_at(adj_square)
                    if adj_piece is not None and adj_piece.symbol() == 'K':
                        return False

        if piece is not None and piece.symbol() == 'K':
            for i in range(-1, 2):
                for j in range(-1, 2):
                    if i == 0 and j == 0: continue
                    if chess.square_rank(square)+i < 0 or chess.square_rank(square)+i > 7: continue
                    if chess.square_file(square)+j < 0 or chess.square_file(square)+j > 7: continue

                    adj_square = chess.square(chess.square_file(square)+j, chess.square_rank(square)+i)
                    adj_piece = board.piece_at(adj_square)
                    if adj_piece is not None and adj_piece.symbol() == 'k':
                        return False

    # both king not in check
    if board.is_check():
        return False

    if king_count != 2:
        return False

    return True

POS_MAPPING = {
    1: "000",
    2: "001",
    3: "010",
    4: "011",
    5: "100",
    6: "101",
    7: "110",
    8: "111",
}

ORIGINAL_MAPPING = {
    1: 'R',
    2: 'N',
    3: 'B',
    4: 'Q',
    5: 'K',
    6: 'B',
    7: 'N',
    8: 'R',
}

PIECE_MAX = {
    'r': 1,
    'n': 2,
    'b': {
        'light': 1,
        'dark': 1,
    },
    'q': 1,
    'p': 8,
    'R': 1,
    'N': 2,
    'B': {
        'light': 1,
        'dark': 1,
    },
    'Q': 1,
}

ORIGINAL_BOARD = [
    ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
    ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
    ['0', '0', '0', '0', '0', '0', '0', '0'],
    ['0', '0', '0', '0', '0', '0', '0', '0'],
    ['0', '0', '0', '0', '0', '0', '0', '0'],
    ['0', '0', '0', '0', '0', '0', '0', '0'],
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],
]

piece_color_row_idx = ['white', 'white', 'white', 'white', 'black', 'black', 'black', 'black']

def convertBoardToFEN(board):
    FEN = ""
    for i in range(len(board)):
        emptyCounter = 0
        for j in range(len(board[i])):
            square = board[i][j]
            if square == '0':
                emptyCounter += 1
            else:
                if emptyCounter != 0:
                    FEN += str(emptyCounter)
                    emptyCounter = 0
                FEN += board[i][j]
        if emptyCounter != 0:
            FEN += str(emptyCounter)

        if i != len(board) - 1:
            FEN += '/'
    return FEN

def randomize_board(board):
    for _ in range(random.randint(10, 200)):
        legal_moves = list(board.legal_moves)
        random_move = random.choice(legal_moves)
        board.push(random_move)

def xor(a, b):
    result = ""
    for i in range(len(a)):
        if a[i] == b[i]:
            result += "0"
        else:
            result += "1"
    return result

def scanCol(board, index):
    total_pieces = 0
    pieces = []
    for row in range(8):
        piece = board.piece_at(chess.square(index, row))
        if piece is not None:
            total_pieces += 1
            pieces.append({
                'symbol': piece.symbol(),
                'index': row,
            })
    
    return total_pieces, pieces

def scanRow(board, index):
    total_pieces = 0
    pieces = []
    for col in range(8):
        piece = board.piece_at(chess.square(col, index))
        if piece is not None:
            total_pieces += 1
            pieces.append({
                'piece': piece.symbol(),
                'index': col,
            })
    
    return total_pieces, pieces

def readMessage(FEN, key, block_size, pawn_mapping=None):
    global POS_MAPPING
    if pawn_mapping != None:
        POS_MAPPING = {}
        pawn_mapping_order = ["000", "001", "010", "011", "100", "101", "110", "111"]
        for number in pawn_mapping:            
            POS_MAPPING[int(number)] = pawn_mapping_order.pop(0)

    board = chess.Board(FEN)
    secretMsg = ""

    read_0_24_bits = ""
    read_24_32_bits = ""
    read_32_40_bits = ""

    colPos = 0
    while colPos < 8:
        pieceSum = 0
        pawnPos = 1
        haveOriginalG = False
        for row in reversed(range(8)):
            square = board.piece_at(chess.square(colPos, row))

            if square is not None:
                pieceSum += 1

                if square.symbol() == 'p' and row == 6:
                    pawnPos = row+1
                
                if square.symbol() == ORIGINAL_MAPPING[colPos+1]:
                    haveOriginalG = True
                
                if square.symbol() == 'P':
                    pawnPos = row+1
        
        if haveOriginalG and pawnPos == key:
            block = POS_MAPPING[8]
        else:
            block = POS_MAPPING[pawnPos]

        read_0_24_bits += block
        colPos += 1
        read_24_32_bits += '1' if pieceSum % 2 == 1 else '0'

    # read 32-40 bits
    for index_col in range(8):
        pieceSum = 0
        for row in range(8):
            square = board.piece_at(chess.square(row, index_col))
            if square is not None:
                pieceSum += 1
        
        read_32_40_bits += '1' if pieceSum % 2 == 1 else '0'

    secretMsg = read_0_24_bits + read_24_32_bits + read_32_40_bits
    return secretMsg[:block_size]

def embedMsg(msg, key):
    global POS_MAPPING
    board = chess.Board()
    randomize_board(board)
    # remove all white pawns
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None and piece.color == chess.WHITE and piece.piece_type == chess.PAWN:
            board.remove_piece_at(square)

    writeImage(board.fen(), "randomize.png")

    msg_bits = [msg[:24][i:i+3] for i in range(0, len(msg[:24]), 3)]

    # check for OGState
    PPost_OGState_list = [{
        "P_pos": 1,
        "OGState": "dontcare"
    } for _ in range(8)]
    for index, block in enumerate(msg_bits):
        if index > 7:
            break

        P_pos = 1
        OGState = "dontcare"
        if block == POS_MAPPING[8]: P_pos = key ; OGState = "yes"
        else:
            for pos, value in POS_MAPPING.items():
                if value == block:
                    P_pos = pos
                    if P_pos == key:
                        OGState = "no"
                    break
        
        PPost_OGState_list[index]["P_pos"] = P_pos
        PPost_OGState_list[index]["OGState"] = OGState

    for index, block in enumerate(msg_bits):
        if index > 7:
            break

        # print("Index: {}, block: {}".format(index, block))

        P_pos = PPost_OGState_list[index]["P_pos"]
        OGState = PPost_OGState_list[index]["OGState"]

        if P_pos != 1 and P_pos != 7:
            # set pawn at P_pos
            row_pos = P_pos - 1
            dest = chess.square(index, row_pos)
            # print("Trying to set pawn at row {}, col {}".format(row_pos, index))
            # print("Dest: {}".format(dest))

            # check if there is a piece at dest, then move it to a random place
            if board.piece_at(dest) is not None:
                piece_to_move = board.piece_at(dest)
                board.remove_piece_at(dest)
                square_color = chess.square_rank(dest) % 2 == chess.square_file(dest) % 2
                while True:
                    # if piece color is black, then move to row 2-5
                    if piece_to_move.color == chess.BLACK:
                        if piece_to_move.symbol() == 'p':
                            possible_row = random.randint(4, 6)
                        else:
                            possible_row = random.randint(4, 7)
                    else:
                        possible_row = random.randint(0, 5)

                    if piece_to_move.symbol() == 'K':
                        possible_row = random.randint(0,3)

                    possible_col = random.randint(0, 7)
                    possible_dest = chess.square(possible_col, possible_row)
                    # check if there is a piece at dest, then retry
                    
                    board.remove_piece_at(possible_dest)

                    if piece_to_move.symbol() == 'p':
                        # print("Just delete pawn")
                        break

                    if board.piece_at(possible_dest) is None:
                        # check if it is a bishop, then make sure the color is correct
                        if piece_to_move.symbol() == 'b':
                            if square_color == (chess.square_rank(possible_dest) % 2 == chess.square_file(possible_dest) % 2):
                                # print(">> Moving piece {} from col {}, row {} to col {}, row {}".format(piece_to_move.symbol(), index, row_pos, possible_col, possible_row))
                                board.set_piece_at(possible_dest, piece_to_move)
                                break
                        else:
                            # print(">> Moving piece {} from col {}, row {} to col {}, row {}".format(piece_to_move.symbol(), index, row_pos, possible_col, possible_row))
                            board.set_piece_at(possible_dest, piece_to_move)
                            break

            board.set_piece_at(dest, chess.Piece(chess.PAWN, chess.WHITE))

            # check if OSState is yes, then move original piece to its own column
            if OGState == "yes":
                # print("OGSTATE == YESS")
                original_piece = ORIGINAL_MAPPING[index+1]
                # print("Original piece: {}".format(original_piece))

                # detect original piece
                for chess_col in range(index, 8):
                    for chess_row in range(8):
                        square = chess.square(chess_col, chess_row)
                        piece = board.piece_at(square)
                        if piece is not None and piece.symbol() == original_piece:
                            # delete piece
                            board.remove_piece_at(square)
                            # print("Deleting piece {} at col {}, row {}".format(original_piece, chess_col, chess_row))

                # then move original piece to its own column
                while True:
                    possible_row = random.randint(0, 6)
                    possible_dest = chess.square(index, possible_row)
                    # check if there is a piece at dest, then retry
                    if board.piece_at(possible_dest) is None:
                        # print("Set piece {} at col {}, row {}".format(original_piece, index, possible_row))
                        board.set_piece_at(possible_dest, chess.Piece.from_symbol(original_piece))
                        break
            
            if OGState == "no":
                # print("OGSTATE == NOOO")
                original_piece = ORIGINAL_MAPPING[index+1]
                # print("Original piece: {}".format(original_piece))

                # detect original piece
                for chess_col in range(index, 8):
                    for chess_row in range(8):
                        square = chess.square(chess_col, chess_row)
                        piece_to_move = board.piece_at(square)
                        square_color = chess.square_rank(square) % 2 == chess.square_file(square) % 2

                        if piece_to_move is not None and piece_to_move.symbol() == original_piece:
                            # move to possible dest
                            possible_col_list = [i for i in range(8) if PPost_OGState_list[i]["OGState"] == "dontcare"]
                            while True:
                                possible_col = random.choice(possible_col_list)
                                possible_row = random.randint(0, 5)

                                if piece_to_move.symbol() == 'K':
                                    possible_row = random.randint(0,3)
                                
                                possible_dest = chess.square(possible_col, possible_row)

                                # check if it is a bishop, then make sure the color is correct
                                if piece_to_move.symbol() == 'b' and square_color != (chess.square_rank(possible_dest) % 2 == chess.square_file(possible_dest) % 2):
                                    continue

                                # check if there is a piece at dest, then retry
                                if board.piece_at(possible_dest) is None:
                                    # print("Moving piece {} from col {}, row {} to col {}, row {}".format(original_piece, chess_col, chess_row, possible_col, possible_row))
                                    board.remove_piece_at(square)
                                    board.set_piece_at(possible_dest, chess.Piece.from_symbol(original_piece))
                                    break
        
        elif P_pos == 7:
            # set black pawn at P_pos
            row_pos = P_pos - 1
            dest = chess.square(index, row_pos)
            # print("Trying to set pawn at row {}, col {}".format(row_pos, index))
            # print("Dest: {}".format(dest))

            # remove all pawn at current column
            for chess_row in range(8):
                square = chess.square(index, chess_row)
                piece = board.piece_at(square)
                if piece is not None and piece.symbol() == 'p':
                    board.remove_piece_at(square)

            # check if there is a piece at dest, then move it to a random place
            if board.piece_at(dest) is not None:
                piece_to_move = board.piece_at(dest)
                board.remove_piece_at(dest)
                square_color = chess.square_rank(dest) % 2 == chess.square_file(dest) % 2
                while True:
                    # if piece color is black, then move to row 2-5
                    if piece_to_move.color == chess.BLACK:
                        if piece_to_move.symbol() == 'p':
                            possible_row = random.randint(4, 6)
                        else:
                            possible_row = random.randint(4, 7)
                    else:
                        possible_row = random.randint(0, 5)

                    possible_col = random.randint(0, 7)
                    possible_dest = chess.square(possible_col, possible_row)
                    # check if there is a piece at dest, then retry
                    
                    if board.piece_at(possible_dest) is not None and board.piece_at(possible_dest).symbol() == 'P':
                        # remove pawn
                        board.remove_piece_at(possible_dest)

                    if board.piece_at(possible_dest) is None:
                        # check if it is a bishop, then make sure the color is correct
                        if piece_to_move.symbol() == 'b':
                            if square_color == (chess.square_rank(possible_dest) % 2 == chess.square_file(possible_dest) % 2):
                                board.set_piece_at(possible_dest, piece_to_move)
                                break
                        else:
                            # print(">> Moving piece {} from col {}, row {} to col {}, row {}".format(piece_to_move.symbol(), index, row_pos, possible_col, possible_row))
                            board.set_piece_at(possible_dest, piece_to_move)
                            break
            # set black pawn at dest
            board.set_piece_at(dest, chess.Piece(chess.PAWN, chess.BLACK))
        elif P_pos == 1:
            for chess_row in range(8):
                square = chess.square(index, chess_row)
                piece = board.piece_at(square)

                if piece is not None and piece.symbol() == 'p' and chess_row == 6:
                    # print("[][][][][][] ==== Found black pawn at col {}, row {}".format(index, chess_row))
                    possible_row_list = [-1, 5, 4]
                    possible_row = random.choice(possible_row_list)

                    board.remove_piece_at(square)
                    if possible_row != -1:
                        board.set_piece_at(chess.square(index, possible_row), chess.Piece(chess.PAWN, chess.BLACK))
                    
                    break

    writeImage(board.fen(), "24bits.png")

    if len(msg) <= 24:
        return board.fen()

    last_bytes = msg[24:32]
    print("Next bytes: {}".format(last_bytes))
    
    # count the total piece on the board
    total_piece = {
        "black": 0,
        "white": 0
    }
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            if piece.color == chess.BLACK:
                total_piece["black"] += 1
            else:
                total_piece["white"] += 1

    # print("Total piece: {}".format(total_piece))
    missmatch_list = [False for _ in range(8)]
    total_piece_list = [0 for _ in range(8)]
    total_piece_list_color = [
        {
            "black": 0,
            "white": 0
        } for _ in range(8)
    ]
    
    for index, bit in enumerate(last_bytes):
        # print("Index: {}, bit: {}".format(index, bit))
        # total piece at col index is odd
        # loop through all col index
        total_piece = 0
        for chess_row in range(8):
            square = chess.square(index, chess_row)
            piece = board.piece_at(square)
            if piece is not None:
                total_piece += 1
                if piece.color == chess.BLACK:
                    total_piece_list_color[index]["black"] += 1
                else:
                    total_piece_list_color[index]["white"] += 1
        
        total_piece_list[index] = total_piece

        if bit == '1': # total piece at col index is odd
            if total_piece % 2 == 0:
                missmatch_list[index] = True
        else: # total piece at col index is even
            if total_piece % 2 == 1:
                missmatch_list[index] = True

    # print("Total piece list: {}".format(total_piece_list))
    # print("Missmatch list: {}".format(missmatch_list))

    # writeImage(board.fen(), "24bits.png")

    mm_list = []
    for index, mm in enumerate(missmatch_list):
        if mm:
            tot_piece, pieces = scanCol(board, index)
            mm_list.append({
                "index": index,
                "total_piece": tot_piece,
                "pieces": pieces
            })

    # sort by total piece
    mm_list = sorted(mm_list, key=lambda k: k['total_piece'])

    # print("MM_LIST")
    # print(json.dumps(mm_list, indent=4))

    if len(mm_list) % 2 != 0:
        # drop the first one, then delete random piece
        selected_mm = mm_list[0]

        # select piece to delete
        blacklist = ['k', 'K']
        # check ogstate
        if PPost_OGState_list[selected_mm['index']]["OGState"] == "yes":
            blacklist.append(ORIGINAL_MAPPING[selected_mm['index']+1])
        
        piece_available = []
        for piece in selected_mm['pieces']:
            if piece['symbol'] in blacklist: continue

            if piece['symbol'] == 'p' and piece['index'] == PPost_OGState_list[selected_mm['index']]["P_pos"]:
                continue

            if piece['symbol'] == 'P' and piece['index'] == PPost_OGState_list[selected_mm['index']]["P_pos"]:
                continue

            piece_available.append(piece)

        if len(piece_available) == 0:
            raise Exception("Cannot find piece to delete")

        random_piece = random.choice(piece_available)
        board.remove_piece_at(chess.square(selected_mm['index'], random_piece['index']))

        mm_list = mm_list[1:]

    # print("MM_LIST")
    # print(json.dumps(mm_list, indent=4))

    mm_pair = []
    # pair by highest and lowest
    for i in range(len(mm_list)//2):
        mm_pair.append([mm_list[i], mm_list[len(mm_list)-i-1]])

    # print("MM_PAIR")
    # print(json.dumps(mm_pair, indent=4))

    for mmp in mm_pair:
        mmp1 = mmp[0]
        mmp2 = mmp[1]

        # clean available piece to swap
        mmp1_available_piece = []
        mmp2_available_piece = []

        mmp1_blacklist = []
        mmp2_blacklist = []

        # check ogstate
        if PPost_OGState_list[mmp1['index']]["OGState"] == "yes":
            mmp1_blacklist.append(ORIGINAL_MAPPING[mmp1['index']+1])

        if PPost_OGState_list[mmp2['index']]["OGState"] == "yes":
            mmp2_blacklist.append(ORIGINAL_MAPPING[mmp2['index']+1])

        if PPost_OGState_list[mmp1['index']]["OGState"] == "no":
            mmp2_blacklist.append(ORIGINAL_MAPPING[mmp1['index']+1])

        if PPost_OGState_list[mmp2['index']]["OGState"] == "no":
            mmp1_blacklist.append(ORIGINAL_MAPPING[mmp2['index']+1])

        for piece in mmp1['pieces']:
            if piece['symbol'] in mmp1_blacklist: continue

            if piece['symbol'] == 'p' and piece['index'] == PPost_OGState_list[mmp1['index']]["P_pos"]:
                continue

            if piece['symbol'] == 'P' and piece['index'] == PPost_OGState_list[mmp1['index']]["P_pos"]:
                continue

            mmp1_available_piece.append(piece)

        for piece in mmp2['pieces']:
            if piece['symbol'] in mmp2_blacklist: continue

            if piece['symbol'] == 'p' and piece['index'] == PPost_OGState_list[mmp2['index']]["P_pos"]:
                continue

            if piece['symbol'] == 'P' and piece['index'] == PPost_OGState_list[mmp2['index']]["P_pos"]:
                continue

            mmp2_available_piece.append(piece)

        if len(mmp1_available_piece) == 0 or len(mmp2_available_piece) == 0:
            raise Exception("Cannot find piece to swap")

        selected_mmp = mmp1 if len(mmp1_available_piece) > len(mmp2_available_piece) else mmp2
        target_mmp = mmp2 if len(mmp1_available_piece) > len(mmp2_available_piece) else mmp1

        # select random piece to swap
        swap_ok = False
        for piece_to_move in selected_mmp['pieces']:
            piece_symbol = piece_to_move['symbol']
            piece_index = piece_to_move['index']
            piece_color = 'black' if piece_symbol.islower() else 'white'
            square_color = chess.square_rank(chess.square(selected_mmp['index'], piece_index)) % 2 == chess.square_file(chess.square(selected_mmp['index'], piece_index)) % 2
            square_color = 'light' if square_color else 'dark'

            target_index = target_mmp['index']
            target_piece_list = target_mmp['pieces']

            possible_row_list = [i for i in range(8)]
            if piece_symbol == 'p':
                possible_row_list = [i for i in range(4, 8)]

            if piece_symbol == 'P':
                possible_row_list = [i for i in range(4)]

            if piece_symbol == 'b' or piece_symbol == 'B':
                possible_row_list = []
                for i in range(8):
                    square = chess.square(target_index, i)
                    current_square_color = chess.square_rank(square) % 2 == chess.square_file(square) % 2
                    current_square_color = 'light' if current_square_color else 'dark'

                    if current_square_color == square_color:
                        possible_row_list.append(i)

            if piece_symbol == 'k' or piece_symbol == 'K':
                possible_row_list = [i for i in range(8) if piece_color_row_idx[i] == piece_color]

            for tp in target_piece_list:
                if tp['index'] in possible_row_list:
                    possible_row_list.remove(tp['index'])

            if len(possible_row_list) > 0:
                # select random row
                for possi_row in possible_row_list:
                    # print("Trying to move piece {} from col {}, row {} to col {}, row {}".format(piece_symbol, selected_mmp['index'], piece_index, target_index, possi_row))
                    board.remove_piece_at(chess.square(selected_mmp['index'], piece_index))
                    board.set_piece_at(chess.square(target_index, possi_row), chess.Piece.from_symbol(piece_symbol))
                    swap_ok = True
                    break
                if swap_ok == True:
                    break
            
            if swap_ok == True:
                break

        if swap_ok == False:
            raise Exception("Cannot find piece to swap")

    # validate
    read_bits_24_32 = ""
    for index in range(8):
        pieceSum, _ = scanCol(board, index)
        read_bits_24_32 += '1' if pieceSum % 2 == 1 else '0'

    if read_bits_24_32 != msg[24:32]:
        raise Exception("Validation failed")

    writeImage(board.fen(), "32bits.png")

    if len(msg) <= 32:
        return board.fen()

    # insert by rows
    last_bytes = msg[32:]
    print("Next bytes: {}".format(last_bytes))

    # removing double black pawn
    for chess_col in range(8):
        pawn_list = []
        for chess_row in range(8):
            square = chess.square(chess_col, chess_row)
            piece = board.piece_at(square)
            if piece is not None and piece.symbol() == 'p':
                pawn_list.append(square)

        if len(pawn_list) > 1:
            # remove 2 pawn
            board.remove_piece_at(pawn_list[0])
            board.remove_piece_at(pawn_list[1])
    # count the total piece on the board
    total_piece = {
        "black": 0,
        "white": 0
    }

    piece_count_by_symbol = {
        'r': 0,
        'n': 0,
        'b': {
            'light': 0,
            'dark': 0,
        },
        'q': 0,
        'p': 0,
        'R': 0,
        'N': 0,
        'B': {
            'light': 0,
            'dark': 0,
        },
        'Q': 0,
        'P': 0,
        'k': 0,
        'K': 0
    }

    piece_max = {
        'r': 2,
        'n': 2,
        'b': {
            'light': 1,
            'dark': 1,
        },
        'q': 1,
        'p': 8,
        'R': 2,
        'N': 2,
        'B': {
            'light': 1,
            'dark': 1,
        },
        'Q': 1,
        'P': 8,
        'k': 1,
        'K': 1
    }

    piece_availability = {
        'black': {
            'available': 0,
            'piece': {}
        },
        'white': {
            'available': 0,
            'piece': {}
        }
    }

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            if piece.symbol() == 'b' or piece.symbol() == 'B':
                square_color = chess.square_rank(square) % 2 == chess.square_file(square) % 2
                if square_color:
                    piece_count_by_symbol[piece.symbol()]['light'] += 1
                else:
                    piece_count_by_symbol[piece.symbol()]['dark'] += 1
            else:
                piece_count_by_symbol[piece.symbol()] += 1

            if piece.color == chess.BLACK:
                total_piece["black"] += 1
            else:
                total_piece["white"] += 1

    print("PIECE COUNT BY SYMBOL ____")
    print(json.dumps(piece_count_by_symbol, indent=4))

    for piece_symbol, piece_count in piece_count_by_symbol.items():
        if piece_symbol in "kKpP": continue
        piece_color = 'black' if piece_symbol.islower() else 'white'

        if piece_symbol == 'b' or piece_symbol == 'B':
            piece_availability.get(piece_color, {}).get('piece', {}).update({
                piece_symbol: {
                    'light': piece_max.get(piece_symbol, {}).get('light', 0) - piece_count.get('light', 0),
                    'dark': piece_max.get(piece_symbol, {}).get('dark', 0) - piece_count.get('dark', 0)
                }
            })
        else:
            piece_availability.get(piece_color, {}).get('piece', {}).update({
                piece_symbol: piece_max.get(piece_symbol, 0) - piece_count
            })

    # update available count
    for color in ['black', 'white']:
        for piece_symbol in piece_availability[color]['piece'].keys():
            if piece_symbol == 'b' or piece_symbol == 'B':
                piece_availability[color]['available'] += piece_availability[color]['piece'][piece_symbol].get('light', 0)
                piece_availability[color]['available'] += piece_availability[color]['piece'][piece_symbol].get('dark', 0)
            else:
                piece_availability[color]['available'] += piece_availability[color]['piece'][piece_symbol]
    
    print("piece availablity")
    print(json.dumps(piece_availability, indent=4))

    # print("Total piece: {}".format(total_piece))
    missmatch_list = [False for _ in range(8)]
    total_piece_list = [0 for _ in range(8)]
    total_piece_list_color = [
        {
            "black": 0,
            "white": 0
        } for _ in range(8)
    ]
    
    for index, bit in enumerate(last_bytes):
        # print("Index: {}, bit: {}".format(index, bit))
        # total piece at col index is odd
        # loop through all col index
        total_piece = 0
        for chess_col in range(8):
            square = chess.square(chess_col, index)
            piece = board.piece_at(square)
            if piece is not None:
                total_piece += 1
                if piece.color == chess.BLACK:
                    total_piece_list_color[index]["black"] += 1
                else:
                    total_piece_list_color[index]["white"] += 1
        
        total_piece_list[index] = total_piece

        if bit == '1': # total piece at col index is odd
            if total_piece % 2 == 0:
                missmatch_list[index] = True
        else: # total piece at col index is even
            if total_piece % 2 == 1:
                missmatch_list[index] = True

    # try to embed by rows
    print("missmatch_list: {}".format(missmatch_list))
    index = 0
    mm_index = []
    for index, mm in enumerate(missmatch_list):
        if mm:
            mm_index.append(index)

    print("mm_index: {}".format(mm_index))

    if len(mm_index) % 2 != 0:
        raise Exception("Cannot find mm_index pair")

    # split mm_index into 2
    mm_split = [ mm_index[i:i+2] for i in range(0, len(mm_index), 2) ]
    print("mm_split: {}".format(mm_split))


    for mms in mm_split:
        print("mms: {}".format(mms))
        # detect where we can insert the piece

        possible_affected_col = []
        for index_col in range(8):
            square1 = chess.square(index_col, mms[0])
            square2 = chess.square(index_col, mms[1])

            if board.piece_at(square1) is None and board.piece_at(square2) is None:
                # count the total piece at col index_col
                total_piece = 0
                for chess_row in range(8):
                    square = chess.square(index_col, chess_row)
                    piece = board.piece_at(square)
                    if piece is not None:
                        total_piece += 1
                
                possible_affected_col.append({
                    "col": index_col,
                    "total_piece": total_piece
                })

        # sort by total piece
        possible_affected_col = sorted(possible_affected_col, key=lambda k: k['total_piece'])
        print("Possible col list: {}".format(possible_affected_col))
        
        if len(possible_affected_col) == 0:
            raise Exception("Cannot find possible affected col")

        ok = False

        for affected in possible_affected_col:
            affected_col = affected['col']
            ok_to_insert = [False, False]
            for row_affected in [0,1]:
                if piece_availability[piece_color_row_idx[mms[row_affected]]]['available'] > 0:
                    # insert piece
                    print("Inserting piece at col {}, and row {}".format(affected_col, mms[row_affected]))
                    # get available piece
                    current_square_color = chess.square_rank(chess.square(affected_col, mms[row_affected])) % 2 == chess.square_file(chess.square(affected_col, mms[row_affected])) % 2
                    current_square_color = 'light' if current_square_color else 'dark'

                    available_piece = []
                    for piece_symbol, piece_count in piece_availability[piece_color_row_idx[mms[row_affected]]]['piece'].items():
                        # print("Piece symbol: {}".format(piece_symbol))
                        # print("Piece count: {}".format(piece_count))
                        if piece_symbol == 'b' or piece_symbol == 'B':
                            if piece_count.get(piece_symbol, {}).get(current_square_color, 0) > 0:
                                available_piece.append(piece_symbol)
                        else:
                            if piece_count > 0:
                                available_piece.append(piece_symbol)

                    # check the OGState
                    if PPost_OGState_list[affected_col]["OGState"] == "no":
                        if ORIGINAL_MAPPING[affected_col+1] in available_piece:
                            available_piece.remove(ORIGINAL_MAPPING[affected_col+1])

                    print("Available piece to insert: {}".format(available_piece))

                    if len(available_piece) == 0:
                        continue

                    # scrumble the available piece
                    random.shuffle(available_piece)
                    piece_to_insert = available_piece[0]

                    # insert piece
                    board.set_piece_at(chess.square(affected_col, mms[row_affected]), chess.Piece.from_symbol(piece_to_insert))

                    # update piece availability
                    if piece_to_insert == 'b' or piece_to_insert == 'B':
                        piece_availability[piece_color_row_idx[mms[row_affected]]]['piece'].get(piece_to_insert, {})[current_square_color] -= 1
                    else:
                        piece_availability[piece_color_row_idx[mms[row_affected]]]['piece'][piece_to_insert] -= 1

                    piece_availability[piece_color_row_idx[mms[row_affected]]]['available'] -= 1
                    ok_to_insert[row_affected] = True
            if ok_to_insert[0] and ok_to_insert[1]:
                ok = True
                break

        if ok: continue

        # try to delete piece
        possible_affected_col = []
        for index_col in range(8):
            square1 = chess.square(index_col, mms[0])
            square2 = chess.square(index_col, mms[1])

            blacklist = ['k', 'K', 'p', 'P', ]
            # check ogstate
            if PPost_OGState_list[index_col]["OGState"] == "yes":
                blacklist.append(ORIGINAL_MAPPING[index_col+1])

            if board.piece_at(square1) is not None and board.piece_at(square2) is not None:
                if board.piece_at(square1).symbol() in blacklist : continue
                if board.piece_at(square2).symbol() in blacklist : continue

                # count the total piece at col index_col
                total_piece = 0
                for chess_row in range(8):
                    square = chess.square(index_col, chess_row)
                    piece = board.piece_at(square)
                    if piece is not None:
                        total_piece += 1
                
                possible_affected_col.append({
                    "col": index_col,
                    "total_piece": total_piece
                })

        # sort by total piece desc
        possible_affected_col = sorted(possible_affected_col, key=lambda k: k['total_piece'], reverse=True)
        print("Possible col list: {}".format(possible_affected_col))

        if len(possible_affected_col) == 0:
            raise Exception("Cannot find possible affected col")

        ok = False

        for affected in possible_affected_col:
            affected_col = affected['col']
            ok_to_delete = [False, False]
            for row_affected in [0,1]:
                if board.piece_at(chess.square(affected_col, mms[row_affected])) is not None:
                    # delete piece
                    print("Deleting piece at col {}, and row {}".format(affected_col, mms[row_affected]))
                    # get available piece
                    current_square_color = chess.square_rank(chess.square(affected_col, mms[row_affected])) % 2 == chess.square_file(chess.square(affected_col, mms[row_affected])) % 2
                    current_square_color = 'light' if current_square_color else 'dark'

                    piece_to_delete = board.piece_at(chess.square(affected_col, mms[row_affected])).symbol()

                    # delete piece
                    board.remove_piece_at(chess.square(affected_col, mms[row_affected]))

                    # update piece availability
                    if piece_to_delete == 'b' or piece_to_delete == 'B':
                        piece_availability[piece_color_row_idx[mms[row_affected]]]['piece'][piece_to_delete][current_square_color] += 1
                    else:
                        piece_availability[piece_color_row_idx[mms[row_affected]]]['piece'][piece_to_delete] += 1

                    piece_availability[piece_color_row_idx[mms[row_affected]]]['available'] += 1
                    ok_to_delete[row_affected] = True
            if ok_to_delete[0] and ok_to_delete[1]:
                ok = True
                break

        if ok: continue
        else:
            raise Exception("Failed to embed by rows")
    
    writeImage(board.fen(), "40bits.png")
    return board.fen()

def main_embedMessage(msg, key, block_size, batch_folder, pawn_mapping):
    global POS_MAPPING
    POS_MAPPING = {}
    pawn_mapping_order = ["000", "001", "010", "011", "100", "101", "110", "111"]
    for number in pawn_mapping:            
        POS_MAPPING[int(number)] = pawn_mapping_order.pop(0)

    # create batch folder
    if not os.path.exists(batch_folder):
        os.makedirs(batch_folder, exist_ok=True)

    # clean folder
    for f in os.listdir(batch_folder):
        os.remove(os.path.join(batch_folder, f))

    msg_part = [msg[i:i+block_size] for i in range(0, len(msg), block_size)]

    img_path_list = []

    for index, part in enumerate(msg_part):
        print("Part {}: {}".format(index, part))
        # embed part into board
        max_retry = 100
        while True:
            max_retry -= 1
            if max_retry == 0:
                return False, None
            
            try:
                generatedFEN = embedMsg(part, key)
                secretMsg = readMessage(generatedFEN, key, block_size)
                # validate secretMsg matches msg
                print("Secret msg  ", secretMsg)
                print("Original msg", part)

                if validate(generatedFEN) and secretMsg == part:
                    break
                else:
                    print("NOT VALID, Retrying...")
            except Exception as e:
                print("ERROR, Retrying...")
                print("error message", e)
                # break

        shutil.move(f"{block_size}bits.png", f"{batch_folder}/board_{index+1}.png")
        img_path_list.append(f"{batch_folder}/board_{index+1}.png")

    return True, img_path_list