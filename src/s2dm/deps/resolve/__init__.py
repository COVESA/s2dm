from importlib import import_module

# Extractors bootstrapping
import_module("s2dm.deps.resolve.extractors.tar_extractor")
import_module("s2dm.deps.resolve.extractors.zip_extractor")

# Resolvers bootstrapping
import_module("s2dm.deps.resolve.resolvers.local_resolver")
import_module("s2dm.deps.resolve.resolvers.remote_resolver")
