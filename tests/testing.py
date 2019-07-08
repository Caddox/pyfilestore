from filestore import Filestore
import random
import ctypes

def random_string(length):
    choices = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    return ''.join([random.choice(choices) for x in range(length)])
    '''
    out = ""
    for _ in range(length):
        out += random.choice(choices)

    return out
    '''

def mass_test(ammount, filestore):
    keys = []
    datas = []

    print("Generating. . .")
    for x in range(ammount):
        print("{0:.2f}% done".format((x / ammount) * 100), end='\r')
        key = random_string(10)
        data = random_string(random.randint(500, 1000))

        if key in keys or data in datas:
            pass
            #print("Duplicate key. Dumping . . .")
            #print('Keys:' + str(keys))
            #print('Datas:' + str(datas))
            #raise Warning("Bad shit cuz.")

        keys.append(key)
        datas.append(data)
        pair = (key, data)
        filestore.append(pair)

    # Check the integrity
    print("Checking. . . ")
    for i in range(ammount):
        print("{0:.2f}% done".format((i / ammount) * 100), end='\r')
        test = filestore[keys[i]]
        if test not in datas:
            print("Key clash with key: " + keys[i])

    print("Done!\t\t\t\t")

def cFNV64(data):
    low = data.lower()
    h = ctypes.c_uint64(0xCBF29CE484222325)
    for i in range(len(low)):
        b = ord(low[i])
        h = (h.value ^ b) * 1099511628211
        h = ctypes.c_uint64(h)
        #h = (h ^ ctypes.c_uint64(b)) * 1099511628211

    return h.value

def cFNV32(data):
    h = ctypes.c_uint32(0x811c9dc5)
    for i in range(len(data)):
        b = ord(data[i])
        h = (h.value ^ b) * 16777619
        h = ctypes.c_uint32(h)

    return h.value

def FNV64(data):
    low = data.lower()
    h = 0xCBF29CE484222325
    for i in range(len(low)):
        b = ord(low[i])
        h ^= b
        h *= 1099511628211

    return h

def elfHash(message):
    h = 0
    high = None

    for m in message:
        h = (h << 4) + ord(m)
        high = h & 0xF0000000
        if high != 0:
            h ^= high >> 24
        h &= ~high

    return h


if __name__ == "__main__":
    tmp = Filestore()
    '''
    data = (('ABC', "It's as easy as one, two three!"), ('Take two!', 'Thriller is not my favorate song...'))
    tmp.store_data(data)
    dic_test = {'a':1, 'b':2, 'c':3}
    dic_t = ('dt', dic_test)
    tmp.append(dic_t)


    dat = ((1, 2, 3), (1,))
    packed = (('Numbers', dat), ('Wut?', dat))
    ins = ('ack', (dat))
    tmp.append(ins)
    tmp.store_data(packed)
    print("================== FINAL ==============")
    print(tmp.serialize(data[0][1]))
    print(tmp['ABC'])
    print(tmp['Take two!'])
    print(tmp['ack'])
    print(tmp['Numbers'])
    print(tmp['Wut?'])
    print(tmp['dt'])
    print(tmp)
    '''

    #print(FNV64("costarring"))
    #print(FNV64("liquid"))
    lista = []
    x = 0
    try:
        while 1:
            x += 1
            print("Checked " + str(x) + " items.", end='\r')
            line = random_string(10)
            h = cFNV32(line)
            if h in [x[0] for x in lista]:
                print("COLLISION: " + str(h))
                print("STRING 1: " + str(line))
                i = [x[0] for x in lista].index(h)
                print("STRING 2: " + str(lista[i][1]))
                print("Checked " + str(len(lista)) + " items.")
                #raise Warning("Donzo")
            lista.append((h, line))
    except KeyboardInterrupt:
        print('\n\nInterupted.')
        if len(set(lista)) == len(lista):
            print(" All good, nothing wrong at all.")
    mass_test(5000, tmp)
    #tmp.clean_up()

