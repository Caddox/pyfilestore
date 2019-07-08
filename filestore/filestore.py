"""
This module holds the following classes:
Filestore: A class for storing a dictionary-like structure on the file.

This module holds no non-class functions.
"""
from base64 import b64encode, b64decode     # for base 64 encoding and decoding
from pickle import dumps, loads             # Writing a serializer is hard :(
import os                                   # File path manipulation
from shutil import rmtree                   # Recursive file removal
from ctypes import c_uint32                 # For c-like overflowing while hashing
from ast import literal_eval                # For numerical insert loading. (Otherwise the hash is wrong.)
from struct import pack                     # For consistent hashing values regardless of variable type.
from copy import deepcopy

class Filestore():
    """ This class implements the filestore class and logic.
    Through this, a dictionary like structure will be created
    that will save all the information to the file system,
    similar to a website cache.
    """
    def __init__(self, encoding='utf-8', overwrite=False):
        # define some variables
        self.STORE = './.store/'
        self.ENCODING = encoding
        self.FILE_INDEX = './.store/index'
        self.unsafe = False
        self.sym_index = []
        self.collisions = []
        self.top_dir = os.getcwd()
        self.working_dir = os.path.join(self.top_dir, self.STORE)
        self.overwrite = overwrite
        self.serializer = dumps         # From pickle
        self.deserializer = loads       # From pickle
        self.hasher_func = self.cFNV32  # Default hash

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
            self.gen_file()

    def __getitem__(self, index):
        # First check if the key is in the sym_index
        if not self.unsafe:
            try:
                self.sym_index.index(index)
            except ValueError: # if not found
                raise KeyError("Given key not found")

        # now check if the hash exists
        name = self.hasher(index)

        # if it does not exist
        if not os.path.isfile(os.path.join(self.working_dir, str(name))):
            raise KeyError("Given key not found")
        else:
            return self.get(index)

    def __setitem__(self, key, value):
        # First, see if the item exists already.
        if not self.unsafe:
            try:
                i = self.sym_index.index(key)
            except ValueError: # Not found
                i = -1

        # Get the hash of the item
        name = self.hasher(key)
        # Get the filepath for the file that may or may not exist
        # also get the serialized data.
        file_path = os.path.join(self.working_dir, str(name))
        serial = self.serialize(value)
        try:
            encoded = b64encode(serial.encode(self.ENCODING))
        except AttributeError:
            encoded = b64encode(serial)

        if i is not -1: # If the item does exist, replace the content of the file.
            os.remove(file_path)
            f = open(file_path, 'wb')
            f.write(encoded)
            f.close() # Nothing else needs to be done here
        else:
            # Entry does not exist, so append it in.
            self.append((key, value))

    def __delitem__(self, key):
        # First, check if the key exists
        try:
            self.__getitem__(key)
        except KeyError as e:
            print(e)
            return

        # Hash the key to find the name it is listed under.
        name = self.hasher(key)
        # We need to remove it from three places:
        # 1) The index file
        # 2) The self.sym_index
        # 3) The self.STORE file.
        # 2 and 3 are easy, 1 is not.

        # 2:
        index = self.sym_index.index(key)
        del self.sym_index[index]

        # 3:
        filepath = os.path.join(self.working_dir, str(name))
        os.remove(filepath)

        # 1: The name is saved pre-hashing in the index file
        with open(self.FILE_INDEX, 'r+') as f:
            lines = f.readlines()
            f.seek(0)
            search_key = str(key) + '\n'

            for elm in lines:
                if elm == search_key: # The line we want to remove
                    continue
                else:
                    f.write(elm)

            f.truncate()

    def __repr__(self):
        return str(self)

    def __str__(self):
        builder = '{'
        for elm in self.sym_index:
            if isinstance(elm, str):
                builder += "'" + elm + "': "
            else:
                builder += str(elm) + ': '

            item = self.get(elm)
            if isinstance(item, str):
                if item.find("'", 0) != -1:
                    builder += '"' + str(item) + '", '
                else:
                    builder += "'" + str(item) + "', "
            else:
                builder += str(item) + ", "

        if len(self.sym_index) == 0:
            builder += '}'

        builder = builder.rsplit(',', 1) # get rid of the final comma
        out = '}'.join(builder)

        return out

    def get(self, index):
        """
        Returns decoded information when given an index
        Gets the data out of the key.
        __getitem__ performs the existence checks.
        """
        name = self.hasher(index)

        contents = None
        with open(os.path.join(self.working_dir, str(name)), 'rb') as f:
            contents = f.read()

        dec = b64decode(contents)
        try:
            return self.deserialize(dec.decode(self.ENCODING))
        except (AttributeError, UnicodeDecodeError):
            return self.deserialize(dec)

    def load_index(self):
        '''
        Loads the index file into the member variable sym_index
        Will throw a FileNotFound exception if the file does not exist.
        '''
        with open(os.path.join(self.top_dir, self.FILE_INDEX), 'r') as f:
            tmp = f.read().split('\n')[:-1]
            #print(tmp)
            for t in tmp:
                t = self.untype_string(t)
                self.sym_index.append(t)

    def update_index(self, name):
        '''
        Adds a new item to the index file.
        This will occur each time a new key is entered into the Filestore.
        '''
        # Check if the name is already in the list
        try:
            self.sym_index.index(name)
        # not in the list case
        except ValueError:
            self.sym_index.append(name)
            f = open(os.path.join(self.top_dir, self.FILE_INDEX), 'a')
            insert_val = self.type_string(name)
            f.write(insert_val + str('\n'))
            f.close()
            #print(self.sym_index)

    def type_string(self, var):
        '''
        Alters anything not nativity a string to contain a marker
        showing that the following variable needs to be evaluated
        into a default data type. Undone with self.untype_string.
        '''
        builder = ''
        # if the variable is in the collided list
        if len(self.collisions) > 0:
            collided_vars, counts = zip(*self.collisions)
            if var in collided_vars:
                builder += '<' + str(counts[collided_vars.index(var)]) + '>'

        if not isinstance(var, str):
            builder += '::' + str(var)
        else:
            builder += var

        return builder


    def untype_string(self, var):
        '''
        Checks if the string from the file has a '::' at the beginning,
        if it does it evaluates it into a data type that is not a string.
        Without this functionality, loading keys can mistake integers for
        strings, leading to a hash error.
        '''
        if var.find('<', 0, 5) != -1:
            start = var.find('<')
            end = var.find('>')
            col = literal_eval(var[start + 1:end])
            self.collisions.append((var[3:], col))
            return var[3:]
        if var.find('::', 0, 5) == -1: # '::' is found in the first five spots
            return var
        else:
            collisions, value = var.split('::') # returns a list like ['<collisions>', 'value']
            evaled = literal_eval(value)

            if collisions != '':
                # Note the item in the collisions list
                start = collisions.find('<')
                end = collisions.find('>')
                col = literal_eval(collisions[start + 1:end])
                self.collisions.append((evaled, col))

            return evaled

    def gen_file(self):
        '''
        This function generates the ./.store directory and hides it.
        On windows, this leads to a ctypes.windll call, otherwise the file is
        created as-is.
        '''
        os.mkdir(self.STORE)

        if os.name == 'nt': # For windows, we have to call a windows function to hide the file
            from ctypes import windll
            windll.kernel32.SetFileAttributesW(self.STORE, 2) # Make the file hidden

        # Open the index file on all systems and write nothing to it.
        open(self.FILE_INDEX, 'a').close()

    def store_data(self, data):
        '''
        data is a list (or tuple) of pairs (of tuples/lists)
        This will result in the addition of items to the Filestore
        data. Generally for larger amounts of data.
        '''
        # go into the storage directory
        os.chdir(self.STORE)
        self._walk(data)
        os.chdir(self.top_dir)

    def append(self, data):
        '''
        Takes an input of a tuple of two items. Data can only include one
        tuple. Use store_data for a list of multiple tuples.
        This function will result in an updating of the data in the Filestore.
        '''
        try:
            os.chdir(self.STORE)
        except FileNotFoundError:
            self.gen_file()
            os.chdir(self.STORE)
        ins = (data),
        self._walk(ins)
        os.chdir(self.top_dir)

    def _walk(self, data):
        '''
        Takes in a list of pairs, and inserts them into the Filestore.
        On each insert, a file may be created. The key (pair[0]) gets hashed
        and a file is created with the hashed name. The data (pair[1]) gets
        serialized, encoded into base64, and written to the file. Unless
        self.overwrite is True, the files are not overwritten given a new
        pair with an old key.
        '''
        # Iterate over each pair of items in data (eg, a key-data relationship)
        # hash the key to use as the filename
        # if the file already exists, refer to the overwrite variable (and/or pass)
        # encode the data as base64 and write the file

        #print(data)
        for pair in data:
            name = self.hasher(pair[0])
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
        ''' Sets the serializer function for use. '''
        self.serializer = new_ser

    def set_deserializer(self, new_des):
        ''' Sets the deserializer function for use. '''
        self.deserializer = new_des

    def set_hasher_func(self, new_hash):
        '''
        Sets the hasher_func for use. The hash function is required
        to handle all simple data types (i.e., int, float, str, bytes).

        NOTE: For Windows, the length of the number returned may not
        exceed the maximum file name length of 254 characters. Please
        ensure the assigned hash does not generate a hash longer than
        254 characters in length.
        '''
        self.hasher_func = new_hash

    def serialize(self, data):
        ''' Serializes the data using the set serializer. '''
        return self.serializer(data)

    def deserialize(self, data):
        ''' Deserializes the data using the set deserializer. '''
        return self.deserializer(data)

    def clean_up(self): # Return to the top dir and remove the .store directory.
        '''
        Removes all Filestore files off of the system.
        Calling this will clear out the entire ./.store directory and remove it.
        Non-reversible. BE SURE YOU WANT THIS WHEN YOU USE IT.

        NOTE: Currently places the class object in a weird state. If you want to
        continue using this object, you must call gen_file() to reset the state
        of the Filestore.
        '''
        os.chdir(self.top_dir)
        rmtree(self.working_dir)
        del self.sym_index
        del self.collisions
        self.sym_index = []
        self.collisions = []

    def clear(self):
        '''
        Cleans up the existing file system and resets it for more use.
        Clears out the .store and recreates it essentially.
        '''
        self.clean_up()
        self.gen_file()

    def hasher(self, data):

        count = 0
        item = deepcopy(data)

        # Now get the hash so we can check for collisions
        origin_hash = self.hasher_func(data)

        # Check for new collisions by checking for file existence
        while os.path.isfile(os.path.join(self.STORE, str(origin_hash))) and \
            item not in self.sym_index:
            # Existance proves collision
            count += 1
            origin_hash = self.hasher_func(origin_hash)

        # Handle old collisions 
        if len(self.collisions) > 0:
            colls, number = zip(*self.collisions)
            if data in colls:
                for _ in range(number[colls.index(data)]):
                    origin_hash = self.hasher_func(origin_hash)

        # Log the name with the collisions
        if count is not 0:
            self.collisions.append((item, count))

        # Return the final hash
        return origin_hash


    def cFNV32(self, data):
        '''
        A 32-bit hash function. Takes in any simple data type
        and converts it to an iterate-able form.
        Returns a 32-bit integer.
        '''
        # First convert the data into a bytes format
        if not isinstance(data, bytes):
            in_type = type(data)
            if in_type == int:
                data = pack('i', data)
            elif in_type == float:
                data = pack('f', data)
            elif in_type == str:
                data = data.encode(self.ENCODING)

        h = c_uint32(0x811c9dc5)
        for n in data:
            h = (h.value ^ n) * 16777619
            h = c_uint32(h)         # Fun fact: ctypes does not support the bitwise OR operator.
                                    # So, we convert it twice.
        return h.value

