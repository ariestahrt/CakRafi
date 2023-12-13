import os
import heapq

class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq

def create_freq_dict(message):
    # count the number of times each letter appears in the message
    char_count = [(char, message.count(char)) for char in set(message)]

    # sort the list by count and then alphabetically
    char_count.sort(key=lambda x: (x[1], x[0]))

    print(char_count)
    return char_count

def save_msg_tree(message):
    char_count = create_freq_dict(message)

    # save the results to a file
    NULL = chr(0)
    with open('temp/freq_dict.bin', 'w') as f:
        for char, count in char_count:
            f.write(char + NULL + str(count) + NULL)


def read_msg_tree():
    # read the results from the file
    with open('temp/freq_dict.bin', 'r') as f:
        data = f.read()

    # convert the data back into a list
    NULL = chr(0)
    data = data.split(NULL)
    data = data[:-1]
    data = list(zip(data[0::2], data[1::2]))

    # convert values back to integers
    data = [(char, int(count)) for char, count in data]

    return data

def build_dict_from_text(data):

    NULL = chr(0)
    data = data.split(NULL)
    data = data[:-1]
    data = list(zip(data[0::2], data[1::2]))

    # convert values back to integers
    data = [(char, int(count)) for char, count in data]

    return data

def build_huffman_tree(freq_dict):
    # heap = [HuffmanNode(char, freq) for char, freq in freq_dict.items()]
    heap = [HuffmanNode(char, freq) for char, freq in freq_dict]
    heapq.heapify(heap)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)

        merged = HuffmanNode(None, left.freq + right.freq)
        merged.left = left
        merged.right = right

        heapq.heappush(heap, merged)

    return heap[0]


def build_huffman_codes(node, current_code, codes):
    if node is not None:
        if node.char is not None:
            codes[node.char] = current_code
        build_huffman_codes(node.left, current_code + '0', codes)
        build_huffman_codes(node.right, current_code + '1', codes)

def compress(message):
    freq_dict = create_freq_dict(message)
    root = build_huffman_tree(freq_dict)

    codes = {}
    build_huffman_codes(root, '', codes)

    compressed_message = ''.join(codes[char] for char in message)
    return compressed_message, root

def decompress(compressed_message, root):
    current_node = root
    decoded_message = ''

    for bit in compressed_message:
        if bit == '0':
            current_node = current_node.left
        else:
            current_node = current_node.right

        if current_node.char is not None:
            decoded_message += current_node.char
            current_node = root

    return decoded_message

if __name__ == "__main__":
    message = "meet me under the bridge at 10 pm"
    save_msg_tree(message)

    # get size of results.txt
    size = os.path.getsize('results.txt')
    print("Huffman Tree Size: ", size, "bytes")

    compressed_message, tree = compress(message)

    print(compressed_message)

    data = read_msg_tree()
    print("READ DATA: ")
    print(data)
    tree = build_huffman_tree(data)

    decompressed_message = decompress(compressed_message, tree)

    print(decompressed_message)