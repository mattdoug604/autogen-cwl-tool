class Arg:
    def __init__(self, prefix, arg_type=None, doc=None):
        self.__prefix = prefix
        self.__arg_type = arg_type
        self.__doc = doc

    def __str__(self):
        return "prefix:'{}' type:'{}' doc:'{}'".format(
            self.__prefix, self.__arg_type, self.__doc
        )

    @property
    def prefix(self):
        return self.__prefix or ""

    @prefix.setter
    def prefix(self, prefix):
        self.__prefix = prefix.strip()

    @property
    def arg_type(self):
        return self.__arg_type or ""

    @arg_type.setter
    def intype(self, arg_type):
        self.__arg_type = arg_type.strip()

    @property
    def doc(self):
        return self.__doc or ""

    @doc.setter
    def doc(self, doc):
        self.__doc = doc.strip()

    def append_doc(self, doc):
        doc = doc.strip()
        if not self.__doc:
            self.__doc = doc
        else:
            if self.__doc[-1] == "-":
                self.__doc += doc
            else:
                self.__doc += " " + doc

    @property
    def id(self):
        return self.__prefix.strip("-").replace("-", "_")
