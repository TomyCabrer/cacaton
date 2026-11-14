import os
for l in open(".env"):
    k, _, v = l.strip().partition("=")
    if k: os.environ[k] = v
from adaption import Adaption
c = Adaption()
r = c.autoscientist.list_models()
print(r if isinstance(r, (list, dict, str)) else getattr(r, "data", r))
