# Py Filestore

This is a simple package meant to create a static data structure similar to a dictionary that exists as a group of files.

#### Example usage
```python
from filestore import filestore as fs

# You can pass your prefered encoding in:
# store = fs(encoding='ascii') # It defaults to utf-8
# You can also force overwriting on population with
# store = fs(overwrite=True)
store = fs()

# You can treat this just like a python dictionary!
# You can populate it in two ways:
store['a'] = (1,2,3) 
store.append(('b', "The alphabet is pretty cool"))

print(store)
# >>> {'a': '(1, 2, 3)', 'b': 'The alphabet is pretty cool'}

# You can get items out too!
alpha = store['a']
print(alpha)
# >>> (1, 2, 3)
print(alpha[1])
# >>> 2

# The dictionary is saved to file under the directory ./.store
# which means you can close the session and return for it later
# as long as the working directory is the same when the class is initialized.
# However, this leaves residue on the file system. We can clean that up too!
store.clean_up() # All the saved data is gone now.
```

##### How it works:
Creating an instance of the class will create a directory on the system that will hold all the given information. An index file is created to allow repopulation over different sessions. 

When data is added to the *filestore*, the class hashes the key with a naive, non-cryptographic hashing algorithm called [FNV-1a](https://en.wikipedia.org/wiki/Fowler%E2%80%93Noll%E2%80%93Vo_hash_function#FNV-1a_hash) in 32 bits. This hash becomes the name of the file. **I have no proof that collisions are completely handled yet.**

 The actual data gets serialized with python's [pickle](https://docs.python.org/3/library/pickle.html) and then encoded into base64 before being written to the disk. If your data is not compatible with [pickle](https://docs.python.org/3/library/pickle.html), you can write and assign your own serializer/deserializer using `store.set_serializer(my_serializer_function)` and `store.set_deserializer(my_deserializer_function)` prior to inserting or removing data.

 ##### Tests
 Currently, the testing .py file is not comprehensive.