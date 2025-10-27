ASCII_MAP = {
    "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a",
    "ă": "a", "ằ": "a", "ắ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
    "â": "a", "ầ": "a", "ấ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
    "À": "A", "Á": "A", "Ả": "A", "Ã": "A", "Ạ": "A",
    "Ă": "A", "Ằ": "A", "Ắ": "A", "Ẳ": "A", "Ẵ": "A", "Ặ": "A",
    "Â": "A", "Ầ": "A", "Ấ": "A", "Ẩ": "A", "Ẫ": "A", "Ậ": "A",

    "đ": "d",
    "Đ": "D",

    "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
    "ê": "e", "ề": "e", "ế": "e", "ể": "e", "ễ": "e", "ệ": "e",
    "È": "E", "É": "E", "Ẻ": "E", "Ẽ": "E", "Ẹ": "E",
    "Ê": "E", "Ề": "E", "Ế": "E", "Ể": "E", "Ễ": "E", "Ệ": "E",

    "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
    "Ì": "I", "Í": "I", "Ỉ": "I", "Ĩ": "I", "Ị": "I",

    "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o",
    "ô": "o", "ồ": "o", "ố": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
    "ơ": "o", "ờ": "o", "ớ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
    "Ò": "O", "Ó": "O", "Ỏ": "O", "Õ": "O", "Ọ": "O",
    "Ô": "O", "Ồ": "O", "Ố": "O", "Ổ": "O", "Ỗ": "O", "Ộ": "O",
    "Ơ": "O", "Ờ": "O", "Ớ": "O", "Ở": "O", "Ỡ": "O", "Ợ": "O",

    "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u",
    "ư": "u", "ừ": "u", "ứ": "u", "ử": "u", "ữ": "u", "ự": "u",
    "Ù": "U", "Ú": "U", "Ủ": "U", "Ũ": "U", "Ụ": "U",
    "Ư": "U", "Ừ": "U", "Ứ": "U", "Ử": "U", "Ữ": "U", "Ự": "U",

    "ỳ": "y", "ý": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    # --- 'Y' based ---
    "Ỳ": "Y", "Ý": "Y", "Ỷ": "Y", "Ỹ": "Y", "Ỵ": "Y",
}

ACCENT_SYMBOL_MAP = {
    "à": ("grave",),
    "á": ("acute",),
    "ả": ("hook",),
    "ã": ("tilde",),
    "ạ": ("dot",),
    "ă": ("breve",),
    "ằ": ("breve", "grave"),
    "ắ": ("breve", "acute"),
    "ẳ": ("breve", "hook"),
    "ẵ": ("breve", "tilde"),
    "ặ": ("breve", "dot"),
    "â": ("circumflex",),
    "ầ": ("circumflex", "grave"),
    "ấ": ("circumflex", "acute"),
    "ẩ": ("circumflex", "hook"),
    "ẫ": ("circumflex", "tilde"),
    "ậ": ("circumflex", "dot"),

    "À": ("grave",),
    "Á": ("acute",),
    "Ả": ("hook",),
    "Ã": ("tilde",),
    "Ạ": ("dot",),
    "Ă": ("breve",),
    "Ằ": ("breve", "grave"),
    "Ắ": ("breve", "acute"),
    "Ẳ": ("breve", "hook"),
    "Ẵ": ("breve", "tilde"),
    "Ặ": ("breve", "dot"),
    "Â": ("circumflex",),
    "Ầ": ("circumflex", "grave"),
    "Ấ": ("circumflex", "acute"),
    "Ẩ": ("circumflex", "hook"),
    "Ẫ": ("circumflex", "tilde"),
    "Ậ": ("circumflex", "dot"),

    "đ": ("crossbar",),
    "Đ": ("crossbar",),

    "è": ("grave",),
    "é": ("acute",),
    "ẻ": ("hook",),
    "ẽ": ("tilde",),
    "ẹ": ("dot",),
    "ê": ("circumflex",),
    "ề": ("circumflex", "grave"),
    "ế": ("circumflex", "acute"),
    "ể": ("circumflex", "hook"),
    "ễ": ("circumflex", "tilde"),
    "ệ": ("circumflex", "dot"),

    "È": ("grave",),
    "É": ("acute",),
    "Ẻ": ("hook",),
    "Ẽ": ("tilde",),
    "Ẹ": ("dot",),
    "Ê": ("circumflex",),
    "Ề": ("circumflex", "grave"),
    "Ế": ("circumflex", "acute"),
    "Ể": ("circumflex", "hook"),
    "Ễ": ("circumflex", "tilde"),
    "Ệ": ("circumflex", "dot"),

    "ì": ("grave",),
    "í": ("acute",),
    "ỉ": ("hook",),
    "ĩ": ("tilde",),
    "ị": ("dot",),
    "Ì": ("grave",),
    "Í": ("acute",),
    "Ỉ": ("hook",),
    "Ĩ": ("tilde",),
    "Ị": ("dot",),

    "ò": ("grave",),
    "ó": ("acute",),
    "ỏ": ("hook",),
    "õ": ("tilde",),
    "ọ": ("dot",),
    "ô": ("circumflex",),
    "ồ": ("circumflex", "grave"),
    "ố": ("circumflex", "acute"),
    "ổ": ("circumflex", "hook"),
    "ỗ": ("circumflex", "tilde"),
    "ộ": ("circumflex", "dot"),
    "ơ": ("horn",),
    "ờ": ("horn", "grave"),
    "ớ": ("horn", "acute"),
    "ở": ("horn", "hook"),
    "ỡ": ("horn", "tilde"),
    "ợ": ("horn", "dot"),

    "Ò": ("grave",),
    "Ó": ("acute",),
    "Ỏ": ("hook",),
    "Õ": ("tilde",),
    "Ọ": ("dot",),
    "Ô": ("circumflex",),
    "Ồ": ("circumflex", "grave"),
    "Ố": ("circumflex", "acute"),
    "Ổ": ("circumflex", "hook"),
    "Ỗ": ("circumflex", "tilde"),
    "Ộ": ("circumflex", "dot"),
    "Ơ": ("horn",),
    "Ờ": ("horn", "grave"),
    "Ớ": ("horn", "acute"),
    "Ở": ("horn", "hook"),
    "Ỡ": ("horn", "tilde"),
    "Ợ": ("horn", "dot"),

    "ù": ("grave",),
    "ú": ("acute",),
    "ủ": ("hook",),
    "ũ": ("tilde",),
    "ụ": ("dot",),
    "ư": ("horn",),
    "ừ": ("horn", "grave"),
    "ứ": ("horn", "acute"),
    "ử": ("horn", "hook"),
    "ữ": ("horn", "tilde"),
    "ự": ("horn", "dot"),

    "Ù": ("grave",),
    "Ú": ("acute",),
    "Ủ": ("hook",),
    "Ũ": ("tilde",),
    "Ụ": ("dot",),
    "Ư": ("horn",),
    "Ừ": ("horn", "grave"),
    "Ứ": ("horn", "acute"),
    "Ử": ("horn", "hook"),
    "Ữ": ("horn", "tilde"),
    "Ự": ("horn", "dot"),

    "ỳ": ("grave",),
    "ý": ("acute",),
    "ỷ": ("hook",),
    "ỹ": ("tilde",),
    "ỵ": ("dot",),
    
    "Ỳ": ("grave",),
    "Ý": ("acute",),
    "Ỷ": ("hook",),
    "Ỹ": ("tilde",),
    "Ỵ": ("dot",),
}

ACCENT_BITMAP_MAP = {
    "grave": (
        0b01000,
        0b00100,
    ),
    "acute": (
        0b00100,
        0b01000,
    ),
    "hook": (
        0b00100,
        0b00010,
        0b00100,
    ),
    "tilde": (
        0b01000,
        0b10101,
        0b00010,
    ),

    "dot": (
        0b00100,
    ),

    "breve": (
        0b01010,
        0b00100,
    ),
    "circumflex": (
        0b00100,
        0b01010,
    ),
    "horn": (
        0b00001,
    ),

    "crossbar": (
        0b01110,
    ),
}

ACCENT_POSITION_MAP = {
    # accents drawn ABOVE the character
    "grave": 1,
    "acute": 1,
    "hook": 1,
    "tilde": 1,
    "breve": 1,
    "circumflex": 1,
    "horn": 1,

    # accents drawn BELOW the character
    "dot": -1,

    # accents drawn THROUGH the character
    "crossbar": 0,
}


def to_ascii(s):
    return ''.join(ASCII_MAP.get(c, c) for c in s)
