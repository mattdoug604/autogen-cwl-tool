class Arg:
    def __init__(self, prefix, arg_type=None, doc=None):
        self.__prefix = prefix
        self.__type = arg_type
        self.__doc = doc

    def __str__(self):
        return "prefix:'{}' type:'{}' doc:'{}'".format(
            self.__prefix, self.__type, self.__doc
        )

    def get_prefix(self):
        return self.__prefix or ""

    def get_type(self):
        return self.__type or ""

    def get_doc(self):
        return self.__doc or ""

    def get_id(self):
        return self.__prefix.strip("-").replace("-", "_")

    def set_prefix(self, prefix): 
        self.__prefix = prefix.strip()

    def set_type(self, arg_type):
        self.__type = arg_type.strip()

    def set_doc(self, doc):
        self.__doc = doc.strip()

    def append_doc(self, doc):
        doc = doc.strip()
        if not self.__doc:
            self.set_doc(doc)
        else:
            if self.__doc[-1] == "-":
                self.__doc += doc
            else:
                self.__doc += " " + doc