
import hashlib

my_string = "This is a very complicated string"

md5 = hashlib.md5()
md5.update(my_string)
print "My number is", int(md5.hexdigest(), 16)
