import datetime

class FieldDescriptor(object):
    def __init__(self, field):
        self.field = field
    def __get__(self, instance, owner):
        try:
            return self.field.lookup(instance, instance.data[self.field.name])
        except KeyError:
            raise AttributeError

class MultiFieldDescriptor(object):
    def __init__(self, field):
        self.field = field
    def __get__(self, instance, owner):
        values = instance.data[self.field.name]
        return [self.field.lookup(instance, value) for value in values]

class Field(object):
    group_multi = None
    multi = None

    def __init__(self, lists, list_id, xml):
        self.lists, self.list_id = lists, list_id
        self.name = xml.attrib['Name']
	self.display_name = xml.attrib['DisplayName']
        self.description = xml.attrib.get('Description')
        if self.multi is None:
            self.multi = xml.attrib.get('Mult') == 'TRUE'

    def get(self, row):
        value = row.attrib.get('ows_' + self.name)
        if value is None:
            return None

        values, start, pos = [], 0, -1
        while True:
            pos = value.find(';', pos+1)
            if pos == -1:
                values.append(value[start:].replace(';;', ';'))
                break
            elif value[pos:pos+2] == ';;':
                pos += 2
                continue
            elif value[pos:pos+2] == ';#':
                values.append(value[start:pos].replace(';;', ';'))
                start = pos = pos + 2
            else:
                raise ValueError("Unexpected character after ';': {0}".format(value[pos+1]))

        if self.group_multi is not None:
            values = [values[i:i+self.group_multi] for i in xrange(0, len(values), self.group_multi)]

        if self.multi:
            return map(self.parse, values)
        else:
            return self.parse(values[0])

    def parse(self, value):
        raise NotImplementedError

    @property
    def descriptor(self):
        if not hasattr(self, '_descriptor'):
            self._descriptor = (MultiFieldDescriptor if self.multi else self.descriptor_class)(self)
        return self._descriptor
    descriptor_class = FieldDescriptor

    def lookup(self, row, value):
        return value

class TextField(Field):
    def parse(self, value):
        return value

class LookupFieldDescriptor(FieldDescriptor):
    def __get__(self, instance, owner):
        lookup_list, row_id = instance.data[self.name]
        return instance.list.lists[lookup_list].rows_by_id[row_id]

class LookupField(Field):
    group_multi = 2

    def __init__(self, lists, list_id, xml):
        super(LookupField, self).__init__(lists, list_id, xml)
	self.lookup_list = xml.attrib['List']

    def parse(self, value):
        return self.lookup_list, int(value[0])

    def lookup(self, row, value):
        list_id, row_id = value
        return row.list.lists[list_id].rows_by_id[row_id]

class URLField(Field):
    def parse(self, value):
        url, text = value.split(', ', 1)
        return ('U', url, text)

class ChoiceField(Field):
    def parse(self, value):
        return value

class MultiChoiceField(ChoiceField):
    multi = True

    def get(self, xml):
        values = super(MultiChoiceField, self).get(xml)
        if values is not None:
            return [value for value in values if value]

class DateTimeField(Field):
    def parse(self, value):
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')

class UnknownField(Field):
    def parse(self, value):
        return value

class CounterField(Field):
    def parse(self, value):
        return int(value)

class UserField(Field):
    group_multi = 2

    def parse(self, value):
        return ('USER', value)


type_mapping = {'Text': TextField,
                'Lookup': LookupField,
                'LookupMulti': LookupField,
                'URL': URLField,
                'Choice': ChoiceField,
                'MultiChoice': MultiChoiceField,
                'DateTime': DateTimeField,
                'Counter': CounterField,
                'Computed': TextField,
                'Note': TextField,
                'User': UserField}
default_type = UnknownField
