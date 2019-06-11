class Arg:
    def __init__(
        self,
        prefix=None,
        intype=None,
        doc=None,
        default=None,
        require=False,
        separator=None,
        symbols=[],
    ):
        self._prefix = prefix
        self._intype = intype
        self._doc = doc
        self._default = default
        self._require = require
        self._separator = separator
        self._symbols = symbols

    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, value):
        self._prefix = value

    @property
    def intype(self):
        return self._intype

    @intype.setter
    def intype(self, value):
        self._intype = value

    @property
    def doc(self):
        return self._doc

    @doc.setter
    def doc(self, value):
        self._doc = value

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, value):
        self._default = value

    @property
    def require(self):
        return self._require

    @require.setter
    def require(self, value):
        self._require = True if value else False

    @property
    def separator(self):
        return self._separator

    @separator.setter
    def separator(self, value):
        self._separator = value

    @property
    def symbol(self):
        return self._symbols

    @symbol.setter
    def symbol(self, value):
        self._symbol = value if isinstance(value, list) else [value]
