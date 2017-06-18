"""
Test a dict subclass
"""


class Hello(dict):
    def __init__(self, *args):
        dict.__init__(self, args)

    def __getitem__(self, key):
        val = dict.__getitem__(self, key)
        return val

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, dict.__repr__(self))

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).items():
            self[k] = v

if __name__ == "__main__":
    t = Hello()

    x = "hello"
