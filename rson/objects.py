from collections import OrderedDict

class_for_tag = OrderedDict()
tag_for_class = OrderedDict()  # classes -> tagger (get name, value)

reserved_tags = set("""
        bool int float complex
        string bytestring base64
        duration datetime
        set list dict object
        unknown
""".split())

class InvalidTag(Exception):
    def __init__(self, name, reason):
        self.name = name
        Exception.__init__(self, reason)

class TaggedObject:
    def __init__(self, name, value):
        self.name = name
        self.value = value


tag_for_class[TaggedObject] = lambda obj: (obj.name, obj.value)

def tag_value_for_object(obj):
    if obj.__class__ in tag_for_class:
        get_tag = tag_for_class[obj.__class__]
        name, value = get_tag(obj)
    else:
        raise InvalidTag('unknown',
            "Can't find tag for object {}: unknown class {}".format(obj, obj.__class__))

    if name == 'object':
        return None, value
    if name not in reserved_tags:
        return name, value
    else:
        raise InvalidTag(
            name, "Can't find tag for object {}, as {} is reserved name".format(obj, name))


def tag_rson_value(name, value):
    if name in reserved_tags:
        raise InvalidTag(
            name, "Can't tag {} with {}, {} is reserved".format(value, name, name))

    if name in class_for_tag:
        tag_cls = class_for_tag[name]
        return tag_cs(name, value)
    else:
        return TaggedObject(name, value)


