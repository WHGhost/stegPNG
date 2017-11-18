from struct import pack, unpack
from .pngexceptions import InvalidChunkStructureException, UnsupportedCompressionMethodException
import zlib

class ChunkImplementation:

    def __init__(self, chtype, empty_data=b'', length=None, maxlength=1<<31-1, minlength=0):
        """Arguments:
            chtype: The chunk type (IHDR, IDAT, IEND etc...
            empty_data: the data an empty chunk of this type should have, to makeit valid
            length: The fixed length of the chunk. Overrides minlength and maxlength if set.
            minlength: The minimum length of the chunk.
            maxlength: The minimum length of the chunk."""
        self.type = chtype
        self.empty_data = empty_data
        if length != None:
            if isinstance(length, tuple):
                for i in length:
                    if not type(i) is int:
                        raise TypeError("Possible lenghts should be integers.")
                self.lengths = length
            elif type(length) is int:
                self.maxlength = length
                self.minlength = length
            else:
                raise TypeError("lenght should be an integer or a tuple of integers")
        else:
            self.maxlength = maxlength
            self.minlength = minlength

    def _is_length_valid(self, chunk):
        """Returns True if the chunk's length is valid for that chunk.
        This not to be overriden in most case, the length, maxlength and minlength arguments
        of __init__ should be used."""
        try:
            return chunk.type == self.type and len(chunk) <= self.maxlength and len(chunk) >= self.minlength
        except AttributeError:
            return len(chunk) in self.lengths

    def is_valid(self, chunk):
        """Returns True if the chunk is valid.
        It ignores the crc signature, use PngChunk#check_crc() for that.
        This method should normaly not be overriden as it checks the chunk's header
        and calls _is_payload_valid() to check the payload. This is what is to be overiden."""
        return self._is_length_valid(chunk) and self._is_payload_valid(chunk)

    def _is_payload_valid(self, chunk):
        """This is to be overriden for most chunks."""
        return chunk.data == b''

    def get_all(self, chunk):
        """This is to be overriden for most chunks."""
        return {}

    def get(self, chunk, field):
        """This is to be overriden for most chunks."""
        raise KeyError()

    def set(self, chunk, field, value):
        """This is to be overriden for most chunks."""
        raise KeyError()

class ChunkIHDR(ChunkImplementation):

    def __init__(self):
        super(ChunkIHDR, self).__init__(
            'IHDR',
            length=13,
            empty_data=b'\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x00',
        )
        self.__color_types = (
        ("Greyscale", (1,2, 4, 8, 16)),
        ("Wrong!!", None),
        ("Truecolour", (8, 16)),
        ("Indexed-colour", (1, 2, 4, 8)),
        ("Greyscale with alpha", (8, 16)),
        ("Wrong!!", None),
        ("Truecolour with alpha", (8, 16))
        )

    def get_all(self, chunk):
        return {
            'size': self.get(chunk, 'size'),
            'colortype_name': self.get(chunk, 'colortype_name'),
            'colortype_code': self.get(chunk, 'colortype_code'),
            'colortype_depth': self.get(chunk, 'colortype_depth'),
            'bit_depth': self.get(chunk, 'bit_depth'),
            'compression': self.get(chunk, 'compression'),
            'filter_method': self.get(chunk, 'filter_method'),
            'interlace': self.get(chunk, 'interlace')
        }

    def get(self, chunk, field):
        if field == 'size':
            width = unpack('>I', chunk.data[0:4])[0]
            height = unpack('>I', chunk.data[4:8])[0]
            return (width, height)
        elif field == 'width':
            return unpack('>I', chunk.data[0:4])[0]
        elif field == 'height':
            return unpack('>I', chunk.data[4:8])[0]
        elif field == 'colortype_name':
            code = self.get(chunk, 'colortype_code')
            return self.__color_types[code][0]
        elif field == 'colortype_code':
            return unpack('B', chunk.data[9:10])[0]
        elif field == 'colortype_depth':
            code = self.get(chunk, 'colortype_code')
            return self.__color_types[code][1]
        elif field == 'bit_depth':
            return unpack('B', chunk.data[8:9])[0]
        elif field == 'compression':
            return unpack('B', chunk.data[10:11])[0]
        elif field == 'filter_method':
            return unpack('B', chunk.data[11:12])[0]
        elif field == 'interlace':
            return unpack('B', chunk.data[12:13])[0]
        else:
            raise KeyError()

    def set(self, chunk, field, value):
        if field == 'size':
            self.set(chunk, 'width', value[0])
            self.set(chunk, 'height', value[1])
        elif field == 'width':
            width = pack('>I', value)
            chunk.data = width + chunk.data[4:]
        elif field == 'height':
            height = pack('>I', value)
            chunk.data = chunk.data[:4] + height + chunk.data[8:]
        elif field == 'colortype_code':
            code = pack('B', value)
            chunk.data = chunk.data[:9] + code + chunk.data[10:]
        elif field == 'bit_depth':
            code = pack('B', value)
            chunk.data = chunk.data[:8] + code + chunk.data[9:]
        elif field == 'compression':
            code = pack('B', value)
            chunk.data = chunk.data[:10] + code + chunk.data[11:]
        elif field == 'filter_method':
            code = pack('B', value)
            chunk.data = chunk.data[:11] + code + chunk.data[12:]
        elif field == 'interlace':
            code = pack('B', value)
            chunk.data = chunk.data[:12] + code + chunk.data[13:]
        else:
            raise KeyError()

    def _is_payload_valid(self, chunk):
        return self.get(chunk, 'bit_depth') in self.get(chunk, 'colortype_depth')

class ChunkIDAT(ChunkImplementation):

    """Not ready at all""" #TODO
    def __init__(self):
        super(ChunkIDAT, self).__init__('IDAT')

    def get_all(self, chunk):
        return {'data': 'lots of data'}

    def get(self, chunk, field):
        pass

class ChunktEXt(ChunkImplementation):

    def __init__(self):
        super(ChunktEXt, self).__init__('tEXt',
            empty_data=b'A\x00',
            minlength=2,
        )

    def get_all(self, chunk):
        return {'text': self.get(chunk, 'text'),
                'keyword': self.get(chunk, 'keyword')}

    def get(self, chunk, field):
        if field not in ('text', 'keyword', 'content'):
            raise KeyError()
        if chunk.data.count(0x00) != 1 or chunk.data.find(0x00) > 78:
            raise InvalidChunkStructureException("invalid number of null byte separator in tEXt chunk")
        sep = chunk.data.find(0x00)
        keyword = unpack('{}s'.format(sep), chunk.data[0: sep])[0].decode('latin1')
        text = unpack('{}s'.format(len(chunk.data) - sep - 1), chunk.data[sep + 1: len(chunk.data)])[0].decode('latin1')
        if field == 'text':
            return text
        elif field == 'keyword':
            return keyword
        elif field == 'content':
            return keyword, text

    def set(self, chunk, field, value):
        if field not in ('text', 'keyword'):
            raise KeyError()
        if chunk.data.count(0x00) != 1:
            raise InvalidChunkStructureException("invalid number of null byte separator in tEXt chunk")
        sep = chunk.data.find(0x00)
        value = value.encode('latin1')
        if field == 'text':
            chunk.data = chunk.data[:sep + 1] + value
        elif field == 'keyword':
            chunk.data = value + chunk.data[sep:]

    def _is_payload_valid(self, chunk):
        return chunk.data.count(0x00) == 1 and chunk.data.find(0x00) <= 78

class ChunksRGB(ChunkImplementation):

    def __init__(self):
        super(ChunksRGB, self).__init__('sRGB',
            empty_data=b'\x00',
            length=1,
        )
        self.rederingtypes = (
            "Perceptual",
            "Relative colorimetric",
            "Saturation",
            "Absolute colorimetric"
        )

    def get_all(self, chunk):
        return {
                'rendering_code': self.get(chunk, 'rendering_code'),
                'rendering_name': self.get(chunk, 'rendering_name'),
            }

    def get(self, chunk, field):
        if field == 'rendering_code':
            return chunk.data[0]
        elif field == 'rendering_name':
            try:
                return self.rederingtypes[self.get(chunk, 'rendering_code')]
            except KeyError:
                raise InvalidChunkStructureException('invalid sRGB value')
        else:
            raise KeyError()

    def set(self, chunk, field, value):
        if field == 'rendering_code':
            chunk.data = pack('B', value)
        else:
            raise KeyError()

    def _is_payload_valid(self, chunk):
        return self.get(chunk, 'rendering_code') in range(4)

class ChunktIME(ChunkImplementation):

    def __init__(self):
        super(ChunktIME, self).__init__(
            'tIME',
            length=7,
            empty_data=b'\x00\x00\x01\x01\x00\x00\x00',
        )

    def get_all(self, chunk):
        return {
            'year': self.get(chunk, 'year'),
            'month': self.get(chunk, 'month'),
            'day': self.get(chunk, 'day'),
            'hour': self.get(chunk, 'hour'),
            'minute': self.get(chunk, 'minute'),
            'second': self.get(chunk, 'second'),
        }

    def get(self, chunk, field):
        if field == 'year':
            return unpack('>h', chunk.data[0:2])[0]
        elif field == 'month':
            return chunk.data[2]
        elif field == 'day':
            return chunk.data[3]
        elif field == 'hour':
            return chunk.data[4]
        elif field == 'minute':
            return chunk.data[5]
        elif field == 'second':
            return chunk.data[6]
        else:
            raise KeyError()

    def set(self, chunk, field, value):
        if field == 'year':
            chunk.data = pack('>h', value) + chunk.data[2:]
        elif field == 'month':
            chunk.data = chunk.data[:2] + pack('B', value) + chunk.data[3:]
        elif field == 'day':
            chunk.data = chunk.data[:3] + pack('B', value) + chunk.data[4:]
        elif field == 'hour':
            chunk.data = chunk.data[:4] + pack('B', value) + chunk.data[5:]
        elif field == 'minute':
            chunk.data = chunk.data[:5] + pack('B', value) + chunk.data[6:]
        elif field == 'second':
            chunk.data = chunk.data[:6] + pack('B', value)
        else:
            raise KeyError()

    def _is_payload_valid(self, chunk):
        year = self.get(chunk, 'year')
        month = self.get(chunk, 'month')
        day = self.get(chunk, 'day')
        hour = self.get(chunk, 'hour')
        minute = self.get(chunk, 'minute')
        second = self.get(chunk, 'second')
        month_ok = month >= 1 and month <= 12
        if month in (1, 3, 5, 7, 8, 10, 12):
            max_day = 31
        elif month == 2:
            if year % 4 == 0 and (year % 400 == 0 or year % 100 != 0):
                max_day = 29
            else:
                max_day = 28
        else:
            max_day = 30
        day_ok = day >= 1 and day <= max_day
        hour_ok = hour >= 0 and hour <= 23
        minute_ok = minute >= 0 and minute <= 59
        second_ok = second >= 0 and second <= 60
        return day_ok and month_ok and hour_ok and minute_ok and second_ok


class ChunkgAMA(ChunkImplementation):

    def __init__(self):
        super(ChunkgAMA, self).__init__('gAMA',
            empty_data=b'\x00\x00\x00\x00',
            length=4,
        )

    def get_all(self, chunk):
        return {
                'gama': self.get(chunk, 'gama'),
            }

    def get(self, chunk, field):
        if field == 'gama':
            return unpack('>I', chunk.data[0:4])[0] / 100000
        else:
            raise KeyError()

    def set(self, chunk, field, value):
        if field == 'gama':
            chunk.data = pack('>I', int(value * 100000))
        else:
            raise KeyError()

    def _is_payload_valid(self, chunk):
        return True


class ChunkzTXt(ChunkImplementation):

    def __init__(self):
        super(ChunkzTXt, self).__init__('zTXt',
            empty_data=b'A\x00x\x9c\x03\x00\x00\x00\x00\x01',
            minlength=3,
        )

    def get_all(self, chunk):
        return {'text': self.get(chunk, 'text'),
                'keyword': self.get(chunk, 'keyword'),
                'compression': self.get(chunk, 'compression')}

    def get(self, chunk, field):
        if field not in ('text', 'keyword', 'content', 'compression'):
            raise KeyError()
        if chunk.data.count(0x00) < 1:
            raise InvalidChunkStructureException("invalid number of null byte separator in zTXt chunk")
        sep = chunk.data.find(0x00)
        keyword = unpack('{}s'.format(sep), chunk.data[0: sep])[0].decode('latin1')
        compression_code = chunk.data[sep + 1]
        if compression_code == 0:
            text = zlib.decompress(chunk.data[sep + 2:])
            text = unpack('{}s'.format(len(text)), text)[0].decode('latin1')
        else:
            raise UnsupportedCompressionMethodException(code=compression_code)
        if field == 'text':
            return text
        elif field == 'keyword':
            return keyword
        elif field == 'compression':
            return compression_code
        elif field == 'content':
            return keyword, text

    def set(self, chunk, field, value):
        if field not in ('text', 'keyword'):
            raise KeyError()
        if chunk.data.count(0x00) < 1:
            raise InvalidChunkStructureException("invalid number of null byte separator in zTXt chunk")
        sep = chunk.data.find(0x00)
        compression_code = chunk.data[sep + 1]
        if field == 'text':
            if compression_code == 0:
                text = value.encode('latin1')
                text = zlib.compress(text)
                chunk.data = chunk.data[:sep + 2] + text
            else:
                raise UnsupportedCompressionMethodException()
        elif field == 'keyword':
            chunk.data = value.encode('latin1') + chunk.data[sep:]

    def _is_payload_valid(self, chunk):
        return chunk.data.count(0x00) >= 1 and chunk.data.find(0x00) <= 78

class ChunkcHRM(ChunkImplementation):

    def __init__(self):
        super(ChunkcHRM, self).__init__(
            'cHRM',
            length=32,
            empty_data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        )

    def get_all(self, chunk):
        return {
            'white_x': self.get(chunk, 'white_x'),
            'white_y': self.get(chunk, 'white_y'),
            'red_x': self.get(chunk, 'red_x'),
            'red_y': self.get(chunk, 'red_y'),
            'green_x': self.get(chunk, 'green_x'),
            'green_y': self.get(chunk, 'green_y'),
            'blue_x': self.get(chunk, 'blue_x'),
            'blue_y': self.get(chunk, 'blue_y'),
        }

    def get(self, chunk, field):
        if field == 'white_x':
            return unpack('>I', chunk.data[0:4])[0] / 100000
        elif field == 'white_y':
            return unpack('>I', chunk.data[4:8])[0] / 100000
        elif field == 'red_x':
            return unpack('>I', chunk.data[8:12])[0] / 100000
        elif field == 'red_y':
            return unpack('>I', chunk.data[12:16])[0] / 100000
        elif field == 'green_x':
            return unpack('>I', chunk.data[16:20])[0] / 100000
        elif field == 'green_y':
            return unpack('>I', chunk.data[20:24])[0] / 100000
        elif field == 'blue_x':
            return unpack('>I', chunk.data[24:28])[0] / 100000
        elif field == 'blue_y':
            return unpack('>I', chunk.data[28:32])[0] / 100000
        else:
            raise KeyError()

    def set(self, chunk, field, value):
        if field == 'white_x':
            value = pack('>I', round(value * 100000))
            chunk.data = value+ chunk.data[4:]
        elif field == 'white_y':
            value = pack('>I', round(value * 100000))
            chunk.data = chunk.data[:4] + value + chunk.data[8:]
        elif field == 'red_x':
            value = pack('>I', round(value * 100000))
            chunk.data = chunk.data[:8] + value + chunk.data[12:]
        elif field == 'red_y':
            value = pack('>I', round(value * 100000))
            chunk.data = chunk.data[:12] + value + chunk.data[16:]
        elif field == 'green_x':
            value = pack('>I', round(value * 100000))
            chunk.data = chunk.data[:16] + value + chunk.data[20:]
        elif field == 'green_y':
            value = pack('>I', round(value * 100000))
            chunk.data = chunk.data[:20] + value + chunk.data[24:]
        elif field == 'blue_x':
            value = pack('>I', round(value * 100000))
            chunk.data = chunk.data[:24] + value + chunk.data[28:]
        elif field == 'blue_y':
            value = pack('>I', round(value * 100000))
            chunk.data = chunk.data[:28] + value
        else:
            raise KeyError()

    def _is_payload_valid(self, chunk):
        return True

class ChunkpHYs(ChunkImplementation):

    def __init__(self):
        super(ChunkpHYs, self).__init__(
            'pHYs',
            length=9,
            empty_data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        )

    def get_all(self, chunk):
        return {
            'ppu_x': self.get(chunk, 'ppu_x'),
            'ppu_y': self.get(chunk, 'ppu_y'),
            'unit_code': self.get(chunk, 'unit_code'),
            'unit_name': self.get(chunk, 'unit_name'),
            'dpi': self.get(chunk, 'dpi'),
        }

    def get(self, chunk, field):
        if field == 'ppu_x':
            return unpack('>I', chunk.data[0:4])[0]
        elif field == 'ppu_y':
            return unpack('>I', chunk.data[4:8])[0]
        elif field == 'unit_code':
            return chunk.data[8]
        elif field == 'unit_name':
            code = self.get(chunk, 'unit_code')
            if code == 0:
                return 'unknown'
            elif code == 1:
                return 'meter'
            else:
                raise InvalidChunkStructureException("invalid unit code, only 1 or 0 allowed, found {}".format(code))
        elif field == 'dpi':
            return round(self.get(chunk, 'ppu_x') / 39.3701), round(self.get(chunk, 'ppu_y') / 39.3701)
        else:
            raise KeyError()

    def set(self, chunk, field, value):
        if field == 'ppu_x':
            chunk.data = pack('>I', value) + chunk.data[4:]
        elif field == 'ppu_y':
            chunk.data = chunk.data[:4] + pack('>I', value) + chunk.data[8:]
        elif field == 'unit_code':
            chunk.data = chunk.data[:8] + pack('B', value)
        elif field == 'dpi':
            self.set(chunk, 'ppu_x', round(value[0] * 39.3701))
            self.set(chunk, 'ppu_y', round(value[1] * 39.3701))
        else:
            raise KeyError()

    def _is_payload_valid(self, chunk):
        return self.get(chunk, 'unit_code') in range(2)

class ChunkiTXt(ChunkImplementation):

    def __init__(self):
        super(ChunkiTXt, self).__init__('iTXt',
            empty_data=b'A\x00\x00\x00\x00A\x00',
            minlength=12,
        )

    def get_all(self, chunk):
        return {'keyword': self.get(chunk, 'keyword'),
                'compressed': self.get(chunk, 'compressed'),
                'compression_code': self.get(chunk, 'compression_code'),
                'language': self.get(chunk, 'language'),
                'translated_keyword': self.get(chunk, 'translated_keyword'),
                'text': self.get(chunk, 'text'),
                }

    def get(self, chunk, field):
        if field not in ('text', 'keyword', 'compression_code',
                         'compressed', 'language', 'translated_keyword',):
            raise KeyError()
        if chunk.data.count(b'\x00') < 3:
            raise InvalidChunkStructureException("invalid number of null byte separator in iTXt chunk")
        sep1 = chunk.data.find(0x00)
        if sep1 > 79:
            raise InvalidChunkStructureException(
                "iTXt keyword is too long, it should be at most 79 bytes and is {}".format(sep1)
            )
        sep2 = chunk.data.find(0x00, sep1+3)
        sep3 = chunk.data.find(0x00, sep2+1)
        if field == 'keyword':
            return chunk.data[:sep1].decode('latin1')
        elif field == 'language':
            return chunk.data[sep1+3:sep2].decode('latin1')
        elif field == 'translated_keyword':
            return chunk.data[sep2+1:sep3].decode('utf-8')
        compression_flag = chunk.data[sep1 + 1]
        if field == 'compressed':
            if compression_flag == 0:
                return False
            elif compression_flag == 1:
                return True
            else:
                raise InvalidChunkStructureException('invalid compression flag, it sould be 0 or 1 and is {}'.format(compression_flag))
        compression_code = chunk.data[sep1+2]
        if field == 'compression_code':
            return compression_code
        if field == 'text':
            data = chunk.data[sep3+1:]
            if compression_flag == 0:
                return data.decode('utf-8')
            elif compression_flag == 1:
                if compression_code == 0:
                    return zlib.decompress(data).decode('utf-8')
                else:
                    raise UnsupportedCompressionMethodException()
            else:
                raise InvalidChunkStructureException('invalid compression flag, it sould be 0 or 1 and is {}'.format(compression_flag))
        else:
            raise KeyError()

    def set(self, chunk, field, value):
        sep1 = chunk.data.find(0x00)
        sep2 = chunk.data.find(0x00, sep1+3)
        sep3 = chunk.data.find(0x00, sep2+1)
        if field == 'keyword':
            chunk.data = value.encode('latin1') + chunk.data[sep1:]
        elif field == 'compressed':
            if value:
                chunk.data = chunk.data[:sep1+1] + b'\x01' + chunk.data[sep1+2:]
            else:
                chunk.data = chunk.data[:sep1+1] + b'\x00' + chunk.data[sep1+2:]
        elif field == 'compression_code':
            chunk.data = chunk.data[:sep1+2] + pack('B', value) + chunk.data[sep1+3:]
        elif field == 'language':
                chunk.data = chunk.data[:sep1+3] + value.encode('latin1') + chunk.data[sep2:]
        elif field == 'translated_keyword':
            chunk.data = chunk.data[:sep2+1] + value.encode('utf-8') + chunk.data[sep3:]
        elif field == 'text':
            value = value.encode('utf-8')
            if self.get(chunk, 'compressed'):
                if self.get(chunk, 'compression_code') == 0:
                    chunk.data = chunk.data[:sep3+1] + compress(value)
                else:
                    raise UnsupportedCompressionMethodException()
            else:
                chunk.data = chunk.data[:sep3+1] + value
        else:
            raise KeyError()

    def _is_payload_valid(self, chunk):
        return chunk.data.count(0x00) >= 3 and chunk.data.find(0x00) <= 78

implementations = {
    'IHDR': ChunkIHDR(),
    'IDAT': ChunkIDAT(),
    'IEND': ChunkImplementation('IEND', length=0),
    'tEXt': ChunktEXt(),
    'sRGB': ChunksRGB(),
    'tIME': ChunktIME(),
    'gAMA': ChunkgAMA(),
    'zTXt': ChunkzTXt(),
    'cHRM': ChunkcHRM(),
    'pHYs': ChunkpHYs(),
    'iTXt': ChunkiTXt(),
    #https://www.hackthis.co.uk/forum/programming-technology/27373-png-idot-chunk
}

#TODO If the data to be compressed contain 16384 bytes or fewer, the PNG encoder may set the window size by rounding up to a power of 2 (256 minimum). This decreases the memory required for both encoding and decoding, without adversely affecting the compression ratio.
