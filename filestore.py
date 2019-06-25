from base64 import b64encode, b64decode     # for base 64 encoding and decoding
from pickle import dumps, loads             # Writing a serializer is hard :(
import os                                   # File path manipulation
from shutil import rmtree                   # Recursive file removal
from zlib import adler32                    # For consistent hash names

class filestore():
    def __init__(self, encoding='utf-8', overwrite=False):
        # define some variables
        self.STORE = './.store/'
        self.ENCODING = encoding
        self.FILE_INDEX = './.store/index'
        self.unsafe = False
        self.sym_index = []
        self.top_dir = os.getcwd()
        self.working_dir = os.path.join(self.top_dir, self.STORE)
        self.overwrite = overwrite
        self.serializer = dumps
        self.deserializer = loads

        # Start by looking for the './.store/' directory
        if os.path.exists(self.STORE):
            # Try to load the index into memory
            try:
                self.load_index()
            except FileNotFoundError:
                # Index is not there, but the files are. We cannot do anything
                # about this. We're gonna turn unsafe mode on
                self.unsafe = True
                print('==> WARNING: Unsafe mode has been enabled. This generally occurs when your index file has been removed but the .store directory stuck around for some reason. You should either call self.clean_up() or remove the .store file itself and repopulate it, as it is possible that hash collisions will occur now.')
        else:
            # Create it if it does not exist
            os.mkdir(self.STORE)
            open(self.FILE_INDEX, 'a').close()

    def __getitem__(self, index):
        # First check if the key is in the sym_index
        if not self.unsafe:
            try:
                self.sym_index.index(index)
            except ValueError: # if not found
                raise KeyError("Given key not found")

        # now check if the hash exists
        name = adler32(index.encode(self.ENCODING))
        # if it does not exist
        if not os.path.isfile(os.path.join(self.working_dir, str(name))):
            raise KeyError("Given key not found")
            return None
        else:
            return self.get(index)

    def __repr__(self):
        return str(self)

    def __str__(self):
        builder = '{'
        for elm in self.sym_index:
            builder += "'" + elm + "': '"
            builder += str(self.get(elm)) + "', "

        builder = builder.rsplit(',', 1)
        out = '}'.join(builder)

        return out

    def get(self, index):
        name = adler32(bytes(index.encode(self.ENCODING)))
        contents = None
        with open(os.path.join(self.working_dir, str(name)), 'rb') as f:
            contents = f.read()

        dec = b64decode(contents)
        try:
            return self.deserialize(dec.decode(self.ENCODING))
        except (AttributeError, UnicodeDecodeError) as e:
            return self.deserialize(dec)

    def load_index(self):
        with open(os.path.join(self.top_dir, self.FILE_INDEX), 'r') as f:
            tmp = f.read().split('\n')[:-1]
            #print(tmp)
            self.sym_index = tmp

    def update_index(self, name):
        # Check if the name is already in the list
        try:
            self.sym_index.index(name)
        # not in the list case
        except ValueError:
            self.sym_index.append(name)
            f = open(os.path.join(self.top_dir, self.FILE_INDEX), 'a')
            f.write(name + str('\n'))
            f.close()
            #print(self.sym_index)


    def store_data(self, data):
        # go into the storage directory
        os.chdir(self.STORE)
        self._walk(data)
        os.chdir(self.top_dir)

    def append(self, data):
        os.chdir(self.STORE)
        ins = (data),
        self._walk(ins)
        os.chdir(self.top_dir)

    def _walk(self, data):
        # Iterate over each pair of items in data (eg, a key-data relationship)
        # hash the key to use as the filename
        # if the file already exists, refer to the overwrite variable (and/or pass)
        # encode the data as base64 and write the file

        #print(data)
        for pair in data:
            #print(pair)
            #print(str(pair[0]) + ":" +  str(pair[1]))
            try:
                name = adler32(bytes(pair[0].encode(self.ENCODING)))
            except AttributeError:
                name = adler32(bytes(pair[0]))
                #print("Unhashable key: " + str(pair[0]) + ':' + str(pair[1]))
                #continue
            #print(str(pair[0]) + " hashed to: " + str(name))
            current_file_path = os.path.join(self.working_dir, str(name))
            self.update_index(pair[0])

            # if the file does not exist
            if not os.path.isfile(current_file_path):
                with open(current_file_path, 'wb') as f:
                    serialized = self.serialize(pair[1])
                    try:
                        encoded = b64encode(serialized.encode(self.ENCODING))
                    except AttributeError:
                        encoded = b64encode(serialized)
                    f.write(encoded)
            # File exists, but overwrite is true
            if self.overwrite is True and os.path.isfile(current_file_path):
                os.remove(current_file_path)
                with open(current_file_path, 'wb') as f:
                    serialized = self.serialize(pair[1])
                    try:
                        encoded = b64encode(serialized.encode(self.ENCODING))
                    except AttributeError:
                        encoded = b64encode(serialized)
                    f.write(encoded)
            # file does exist, nothing needs to be done
            else:
                continue

    def set_serializer(self, new_ser):
        self.serializer = new_ser

    def set_deserializer(self, new_des):
        self.deserializer = new_des

    def serialize(self, data):
        return self.serializer(data)

    def deserialize(self, data):
        return self.deserializer(data)

    def clean_up(self):
        os.chdir(self.top_dir)
        rmtree(self.working_dir)


