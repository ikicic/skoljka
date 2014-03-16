from pipeline.compressors import CompressorBase
from cssmin import cssmin

# TODO: fix /*! */ comments, they should be preserved
class CSSCompressor(CompressorBase):
    """
        Wrapper around cssmin compressor. Pipeline has it's own
        wrapper, but it is using pipes for some reason.
    """
    def compress_css(self, css):
        return cssmin(css)
