import numpy as np
from PyQt5 import QtCore
import traceback
import types
from functools import wraps


def convertBytesToStr(input):
    #print("input type:",type(input))
    if isinstance(input, dict):
        return {convertBytesToStr(key): convertBytesToStr(value) for key, value in input.items()}
    elif isinstance(input, list):
        return [convertBytesToStr(element) for element in input]
    elif type(input) == np.ndarray:
        if len(input) > 0: e = input[0]
        else:              e = input
        #print("e:",e)
        #print("type(e)",type(e))
        if isinstance(e,(np.bytes_, bytes)):
            #print("inside cond")
            vfunc = np.vectorize(convertBytesToStr)
            return vfunc(input)
        else:
            return input

    elif isinstance(input, (bytes, np.bytes_)):
        #print("converting",input)
        input = input.decode(encoding = 'utf-8')
        #print("now",input)
        return input

    else:
        return input



class singleton:
    singleton_instances = dict()

    def __init__(self,cls):
        self.cls = cls

    def __call__(self,*args,**kwds):
        #print("===============================singleton called for {}".format(self.cls.__name__))
        if self.cls.__name__ not in self.singleton_instances:
            #print("NO INSTANCE YET of {}".format(self.cls.__name__))
            #print("singleton_instances.keys before:", singleton_instances.keys())
            self.singleton_instances[self.cls.__name__] = self.cls(*args, **kwds)
            #print("singleton_instances.keys after:", singleton_instances.keys())
        else:
            #print("INSTANCE EXISTS FOR {}".format(self.cls.__name__))
            pass
        return self.singleton_instances[self.cls.__name__]


# def singleton(cls):
#
#     def wrapper(*args, **kwargs):
#         if cls.__name__ not in singleton_instances:
#             print("NO INSTANCE YET of {}".format(cls.__name__))
#             print("singleton_instances.keys():", singleton_instances.keys())
#             singleton_instances[cls.__name__] = cls(*args, **kwargs)
#         else:
#             print("INSTANCE EXISTS FOR {}".format(cls.__name__))
#             print("singleton_instances.keys():", singleton_instances.keys())
#
#         return singleton_instances[cls.__name__]
#
#     return wrapper


class singleton_toreactivate:
    def __init__(self,klass):
        self.klass = klass
        self.instance = None
    def __call__(self,*args,**kwds):
        if self.instance == None:
            self.instance = self.klass(*args,**kwds)
        return self.instance
#
# def singleton(class_):
#     class class_w(class_):
#         _instance = None
#         def __new__(class_, *args, **kwargs):
#             if class_w._instance is None:
#                 class_w._instance = super(class_w,
#                                     class_).__new__(class_,
#                                                     *args,
#                                                     **kwargs)
#                 class_w._instance._sealed = False
#             return class_w._instance
#         def __init__(self, *args, **kwargs):
#             if self._sealed:
#                 return
#             super(class_w, self).__init__(*args, **kwargs)
#             self._sealed = True
#     class_w.__name__ = class_.__name__
#     return class_w



# ==========================================================================
#             Pour debuggage des slots pyqtSlot
# http://stackoverflow.com/questions/18740884/preventing-pyqt-to-silence-exceptions-occurring-in-slots
# ==========================================================================
def my_pyqtSlot(*args):
    if len(args) == 0 or isinstance(args[0], types.FunctionType):
        args = []

    @QtCore.pyqtSlot(*args)
    def slotdecorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*args)
            except Exception as e:
                print("Uncaught Exception in slot!!")
                print(e)
                traceback.print_exc()

        return wrapper

    return slotdecorator


def atLeastOneNameMatchInList(name, list_of_names):

    matchs = [(name in list_element) for list_element in list_of_names]

    return any(matchs)
