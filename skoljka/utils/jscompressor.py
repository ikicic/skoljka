from pipeline.compressors import CompressorBase
from slimit import minify


# TODO: fix /*! */ comments, they should be preserved
class JSCompressor(CompressorBase):
    """
    Wrapper around SlimIt compressor. Pipeline has it's own
    wrapper, but we want to customize the parameters.
    """

    def compress_js(self, js):
        return minify(js, mangle=True)
