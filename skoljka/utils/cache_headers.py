def set_immutable_cache(response):
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
